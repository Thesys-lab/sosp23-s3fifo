import os
import sys

import time
import signal
import socket
import logging
import json
from collections import defaultdict
import psutil
import subprocess
from multiprocessing import Process
from threading import Thread, Lock
import redis
from utils import *
from const import *


CONFIG = RunnerConfig(CONFIG_PATH, auto_reload=True)


def run_demo_task(task_params):
    p = subprocess.run("echo demo {}".format(task_params),
                       shell=True,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    o_stdout = p.stdout.decode("ascii").strip()
    o_stderr = p.stderr.decode("ascii").strip()
    return p.returncode, o_stdout, o_stderr


def run_shell_task(task_params):
    """
    export TCMALLOC_LARGE_ALLOC_REPORT_THRESHOLD=1048576000000;

    """

    p = subprocess.run(task_params,
                       shell=True,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    o_stdout = p.stdout.decode("ascii").strip()
    o_stderr = p.stderr.decode("ascii").strip()
    return p.returncode, o_stdout, o_stderr


TASK_TYPE_TO_FUNC = {
    "demo": run_demo_task,
    "shell": run_shell_task,
}

def report_task_finish(worker_name, redis_inst, task, result):
    """
    report a task is finished to redis

    """

    worker = redis_inst.hget(
        REDIS_KEY_IN_PROGRESS_TASKS, task.task_str)
    if worker != worker_name:
        logging.error(
            f"finished task is not assigned to worker {worker} != {worker_name}")

    redis_inst.hset(REDIS_KEY_FINISHED_TASKS, task.task_str,
                            "{}: {}".format(worker_name, result))

    redis_inst.hdel(REDIS_KEY_IN_PROGRESS_TASKS, task.task_str)
    redis_inst.hdel(REDIS_KEY_FAILED_TASKS, task.task_str)

def report_task_failed(worker_name, redis_inst, task, errmsg, max_retry_per_task):
    """ 
    report the task failed

    """

    worker = redis_inst.hget(
        REDIS_KEY_IN_PROGRESS_TASKS, task.task_str)
    if worker != worker_name:
        logging.error(
            f"finished task is not assigned to worker {worker} != {worker_name}")

    failed_workers = redis_inst.hget(
        REDIS_KEY_FAILED_TASKS, task.task_str)
    if failed_workers is None:
        failed_workers = ""
    failed_workers += worker_name + ","
    redis_inst.hset(REDIS_KEY_FAILED_TASKS,
                            task.task_str, failed_workers)
    redis_inst.hset(REDIS_KEY_TASK_FAIL_REASON, task.task_str, errmsg)
    redis_inst.hdel(REDIS_KEY_IN_PROGRESS_TASKS, task.task_str)

    if failed_workers.count(",") < max_retry_per_task:
        redis_inst.hset(REDIS_KEY_TODO_TASKS, task.task_str, "")



class Worker:
    def __init__(self, conf_path="conf.json"):
        self.name = "" + socket.gethostname().split(".")[0]
        self.config = RunnerConfig(conf_path, True)
        self.redis_inst = redis.Redis(
            host=self.config.redis_host,
            port=self.config.redis_port,
            db=self.config.redis_db,
            password=self.config.redis_pass,
            decode_responses=True)  # ssl=True, ssl_cert_reqs=None

        self.in_prog_need_dram_gb = 0
        self.in_progress_tasks = {}  # task -> (start_time, process)
        self.stop_flag = False
        self.last_task_finish_check_time = -1
        self.get_health_info()
        self.lock = Lock()

        self.health_report_thread = Thread(
            target=self.redis_health_report_thread_func, args=())
        self.health_report_thread.start()

        self.health_monitor_thread = Thread(
            target=self.health_monitor_thread_func, args=())
        self.health_monitor_thread.start()

        # fetch whatever this worker was running before (if it is restarted)
        self.reset_task()
        self.logging_worker_info("worker started")

    ########### health #############
    def get_health_info(self):
        cpu_percent = psutil.cpu_percent(interval=2)
        total_core = psutil.cpu_count()
        mem = psutil.virtual_memory()
        total_mem_gb, avail_mem_gb = mem.total / GiB, mem.available / GiB
        self.total_core, self.used_core = total_core, cpu_percent / 100 * total_core
        self.total_mem_gb, self.used_mem_gb = total_mem_gb, total_mem_gb - avail_mem_gb
        return self.total_core, self.used_core, self.total_mem_gb, self.used_mem_gb

    def redis_health_report_thread_func(self):
        logging.info("heartbeat starts")
        while not self.stop_flag:
            self.get_health_info()
            health_str = "{:.0f}:{:.2f}:{:.2f}:{:.2f}:{:.2f}".format(
                time.time(), self.used_core, self.total_core, self.used_mem_gb,
                self.total_mem_gb)
            self.redis_inst.hset("worker_status", self.name, health_str)
            time.sleep(self.config.health_report_interval)

    def logging_worker_info(self, msg):
        logging.info(
            "{}: in progress {} tasks, max {}, curr tasks need DRAM {} GB, used dram {:.2f}/{:.2f} GB, "
            "min dram to accept task {:.2f} GB, cpu core {:.2f}/{}"
            .format(msg,
                    len(self.in_progress_tasks), self.config.max_task_per_worker,
                    self.in_prog_need_dram_gb, self.used_mem_gb, self.total_mem_gb,
                    self.config.min_dram_gb_accept_new_task,
                    self.used_core, self.total_core,
                    ))

    def health_monitor_thread_func(self):
        """
            monitor DRAM usage and return most recent task if it is too low
        
        """
        
        logging.info("monitoring starts")
        while not self.stop_flag:
            self.get_health_info()
            if self.total_mem_gb - self.used_mem_gb < self.config.min_dram_gb_trigger_return:
                self.return_most_recent_task()
            time.sleep(2)

    ########### new task #############

    def can_take_new_task(self):
        can_accept = True
        # check DRAM
        min_dram = self.config.min_dram_gb_accept_new_task
        if self.total_mem_gb - self.used_mem_gb < min_dram:
            can_accept = False
        if self.total_mem_gb - self.in_prog_need_dram_gb < min_dram:
            can_accept = False

        # check CPU
        if len(self.in_progress_tasks) >= self.config.max_task_per_worker:
            can_accept = False
        if self.total_core - self.used_core < 2:
            can_accept = False

        if not can_accept:
            self.logging_worker_info("cannot take new task")

        return can_accept

    def add_in_progress_task(self, task, proc):
        self.lock.acquire()
        self.in_progress_tasks[task] = (time.time(), proc)
        self.in_prog_need_dram_gb += task.min_dram_gb
        self.lock.release()

    ########### task and redis #############
    def return_task(self, task_str):
        """
        return task to todo queue

        """

        worker = self.redis_inst.hget(REDIS_KEY_IN_PROGRESS_TASKS, task_str)
        assert worker == self.name, "report task finish, but task is not assigned to worker"
        self.redis_inst.hdel(REDIS_KEY_IN_PROGRESS_TASKS, task_str)
        self.redis_inst.hset(REDIS_KEY_TODO_TASKS, task_str, "")
        self.logging_worker_info("return task")

    def reset_task(self):
        """
        reset any previous task

        """

        to_return_task = []
        for task, worker in self.redis_inst.hscan_iter(REDIS_KEY_IN_PROGRESS_TASKS):
            if self.name == worker:
                to_return_task.append(task)
        for task in to_return_task:
            self.return_task(task)


    def get_task_from_redis(self):
        """
        fetch a new task from redis

        """

        n_todo = self.redis_inst.hlen(REDIS_KEY_TODO_TASKS)
        if n_todo > 1000:
            kv_list = self.redis_inst.hrandfield(REDIS_KEY_TODO_TASKS, 20, withvalues=True)
            todo = {}
            for i in range(len(kv_list) // 2):
                todo[kv_list[i*2]] = kv_list[i*2+1]
        else:
            todo = self.redis_inst.hgetall(REDIS_KEY_TODO_TASKS)

        if WORKER_STOP_COMMAND in todo:
            return END_OF_TASK

        # failed_tasks = {}
        failed_tasks = self.redis_inst.hgetall(REDIS_KEY_FAILED_TASKS)

        task_can_work_on = []
        for task_str, _ in todo.items():
            if self.name in failed_tasks.get(task_str, ""):
                # do not retry failed tasks
                continue
            task = Task(task_str)
            if task.min_dram_gb > self.total_mem_gb - self.used_mem_gb:
                continue
            if task.min_dram_gb > self.total_mem_gb - self.in_prog_need_dram_gb:
                continue

            task_can_work_on.append(task)

        logging.debug(
            "current task dram {}, task can work on {}, in_progress_tasks {}".
            format(self.in_prog_need_dram_gb, task_can_work_on,
                   self.in_progress_tasks))

        # pick high priority task first
        task_can_work_on.sort(key=lambda x: x.priority, reverse=True)

        for task in task_can_work_on:
            r = self.redis_inst.hdel(REDIS_KEY_TODO_TASKS, task.task_str)
            if r != 1:
                continue
            r = self.redis_inst.hset(
                REDIS_KEY_IN_PROGRESS_TASKS, task.task_str, self.name)
            assert r == 1, "task set in_progress error, task {}".format(task.task_str)
            return task

        return EMPTY_TASK

    ########### util #############
    def return_most_recent_task(self):
        """
        if the node is going to OOM, then kill the most recent process and return it to mamager
        """
        try:
            self.lock.acquire()
            if len(self.in_progress_tasks) == 0:
                raise RuntimeError(
                    "dram usage {:.2f}/{:.2f} no task to return".format(
                        self.used_mem_gb, self.total_mem_gb))

            # the most recent task
            task, (start_time, proc) = sorted(self.in_progress_tasks.items(),
                                              key=lambda x: -x[1][0])[0]

            if proc.is_alive():
                parent = psutil.Process(proc.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()

                # os.killpg(proc.pid, signal.SIGTERM)
                # proc.terminate()
                # proc.close()

                self.in_prog_need_dram_gb -= task.min_dram_gb

                if len(self.in_progress_tasks) == 1:
                    logging.warning("one task to return")
                    report_task_failed(self.name, self.redis_inst,
                        task, f"require too much dram (worker {self.name})", 
                        self.config.max_retry_per_task)
                else:
                    self.return_task(task.task_str)
                logging.info("return task \"{}\" run time {:.2f}".format(
                    task,
                    time.time() - start_time))
                del self.in_progress_tasks[task]

            else:
                self.logging_worker_info(
                    "return most recent task but process is not alive")
        except Exception as e:
            logging.error("return most recent task error {}".format(e))
            self.logging_worker_info("return most recent task failed")
        finally:
            self.lock.release()

    def find_finished_task(self):
        """
        find and clean up finished tasks

        """

        finished_tasks = {}
        self.lock.acquire()
        try:
            for task, (start_time, proc) in self.in_progress_tasks.items():
                if proc.is_alive():
                    continue

                proc.join()
                finished_tasks[task] = proc.exitcode
                self.in_prog_need_dram_gb -= task.min_dram_gb

            for task in finished_tasks.keys():
                del self.in_progress_tasks[task]

        except Exception as e:
            logging.error("check finished task error {}".format(e))
        finally:
            self.lock.release()

        # if self.last_task_finish_check_time + 60 < time.time():
            # self.last_task_finish_check_time = time.time()
        self.logging_worker_info(
            "find {} finished tasks".format(len(finished_tasks)))

        return finished_tasks

    def wait_for_task_completion(self, timeout=-1):
        """
        wait for some tasks to finish with timeout

        """

        finished_tasks = {}  # task => exitcode
        if timeout == -1:
            timeout = 86400 * 30

        while len(finished_tasks) == 0:
            if len(self.in_progress_tasks) == 0 or timeout <= 0:
                return finished_tasks

            finished_tasks = self.find_finished_task()
            time.sleep(2)
            timeout -= 2

        return finished_tasks


#################################### main  #####################################

    def start(self):
        task = EMPTY_TASK
        while task != END_OF_TASK:
            task = self.get_task_from_redis()
            self.logging_worker_info(f"get task {task}")

            if task != EMPTY_TASK:
                p = TaskRunner(self.name, self.redis_inst, task,
                               self.config.max_retry_per_task)
                p.start()
                # if task in self.in_progress_tasks:
                #     # clean up
                #     self.wait_for_task_completion(timeout=2)
                self.add_in_progress_task(task, p)

            while not self.can_take_new_task():
                time.sleep(8)
                self.find_finished_task()

            time.sleep(self.config.sleep_sec_between_accepting_task)
            self.find_finished_task()

        # redis has no task, wait for all tasks to finish
        while len(self.in_progress_tasks) > 0:
            self.wait_for_task_completion()

        self.logging_worker_info("all tasks are finished")
        self.stop_flag = True
        self.health_report_thread.join()
        self.health_monitor_thread.join()


#################################### Task runner #####################################
class TaskRunner(Process):
    def __init__(self, worker_name, redis_inst, task, max_retry_per_task):
        super(TaskRunner, self).__init__()
        self.worker_name = worker_name
        self.redis_inst = redis_inst
        self.task = task
        self.max_retry_per_task = max_retry_per_task

    def run(self):
        o_stdout, o_stderr, exitcode = "", "", -1
        try:
            func = TASK_TYPE_TO_FUNC[self.task.task_type]
            exitcode, o_stdout, o_stderr = func(self.task.task_params)
        except Exception as e:
            logging.warning("error {} task {}".format(e, self.task))
            o_stderr = "failed task \n" + str(e) + "\n" + o_stderr
            if exitcode == 0:
                logging.error("exitcode 0 but error {} {}".format(e, o_stderr))
                exitcode = -1

        if exitcode != 0:
            msg = json.dumps(o_stderr)
            if len(msg) > 1024:
                msg = "stderr is too large. " + msg[:1024]
            report_task_failed(self.worker_name, self.redis_inst, self.task, msg, self.max_retry_per_task)
            logging.warning(
                "cannot finish task {}\n{}".format(self.task, o_stderr))
            sys.exit(exitcode)

        else:
            msg = "stdout is too large"
            if len(o_stdout) < 1024 * 1024:
                msg = json.dumps(o_stdout)
            report_task_finish(self.worker_name, self.redis_inst, self.task, msg)
            logging.info("finish task {}".format(self.task))
            sys.exit(0)


#################################### util function #####################################
def check_task_is_running(task):
    for proc in psutil.process_iter(['pid', 'name', 'username']):
        # print(proc.info)
        p = psutil.Process(proc.info["pid"])
        if " ".join(p.cmdline()) in task:
            # if p.as_dict()["status"] != "sleeping":
            print(p.as_dict())
            return True
    return False


if __name__ == "__main__":

    from argparse import ArgumentParser
    parser = ArgumentParser(description="manage task and worker")

    parser.add_argument("--task",
                        type=str,
                        default="worker",
                        help="worker")
    ap = parser.parse_args()

    if ap.task == "worker":
        worker = Worker()
        worker.start()
    else:
        raise RuntimeError("unknown task {}".format(ap.task))
