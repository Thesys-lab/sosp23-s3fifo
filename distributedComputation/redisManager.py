import os
import sys

import json
from pprint import pprint
from collections import defaultdict, Counter
from functools import partial
import redis
from const import *
from utils import *


CONFIG = RunnerConfig(CONFIG_PATH, auto_reload=False)


def init_redis(redis_inst):
    redis_inst.flushall()
    logging.info("redis initialized")

def verify_task_format(task_str):
    """ task format
    task_type:priority:DRAM_requirement_in_GB:cpu_core_requirement:task
    see task.example for example

    """
    return Task.is_task_str_valid(task_str)

def load_task_from_file(task_filepath):
    """
    load task from file

    """

    tasks = set()
    with open(task_filepath) as ifile:
        for line in ifile:
            if line[0] == "#" or len(line.strip()) <= 2:
                continue
            task_str = line.strip("\n")
            if not verify_task_format(task_str):
                print("task format error: {}".format(task_str))
                continue
            if task_str not in tasks:
                tasks.add(task_str)
    return tasks


def add_task_to_redis(redis_inst, task_filepath):
    """
    load tasks from file and add to redis

    """

    tasks = load_task_from_file(task_filepath)
    finished = redis_inst.hgetall(REDIS_KEY_FINISHED_TASKS)
    in_progress = redis_inst.hgetall(REDIS_KEY_IN_PROGRESS_TASKS)

    p = redis_inst.pipeline()
    for task in tasks:
        if task not in finished and task not in in_progress:
            p.hsetnx(REDIS_KEY_TODO_TASKS, task, "")
    r = p.execute()
    logging.info("load {} tasks, add {} task".format(len(tasks), sum(r)))


def filter_func(data, include_str, exclude_str):
    """ 
    return True if pass 

    """
    # print("{} in {} {}".format(include_str, data, include_str in data))
    if len(include_str) > 0:
        if include_str in data:
            return True
        else:
            return False
    if len(exclude_str) > 0:
        if exclude_str in data:
            return False
        else:
            return True
    return True


def print_task_status(redis_inst,
                      todo=False,
                      in_progress=False,
                      finished=False,
                      failed=False,
                      failed_reason=True,
                      print_result=False,
                      include_str="",
                      exclude_str=""):
    """
    print the status of tasks 

    @param todo: print todo tasks
    @param in_progress: print in_progress tasks
    @param finished: print finished tasks
    @param failed: print failed tasks
    @param failed_reason: print failed reason
    @param print_result: print result
    @param include_str: only print task that include this string
    @param exclude_str: only print task that exclude this string

    """
    todo_tasks = []
    in_progress_tasks = {}
    finished_tasks = {}
    failed_tasks = {}
    task_fail_reason = {}
    my_filter = partial(filter_func,
                        include_str=include_str,
                        exclude_str=exclude_str)

    try:
        for task_str, _ in redis_inst.hgetall(REDIS_KEY_TODO_TASKS).items():
            task = Task(task_str)
            todo_tasks.append(task)

        for task_str, worker in redis_inst.hgetall(
                REDIS_KEY_IN_PROGRESS_TASKS).items():
            task = Task(task_str)
            in_progress_tasks[task] = worker

        for task_str, output in redis_inst.hgetall(REDIS_KEY_FINISHED_TASKS).items():
            task = Task(task_str)
            finished_tasks[task] = output

        for task_str, workers in redis_inst.hgetall(REDIS_KEY_FAILED_TASKS).items():
            task = Task(task_str)
            failed_tasks[task] = workers

        for task_str, reason in redis_inst.hgetall(REDIS_KEY_TASK_FAIL_REASON).items():
            task = Task(task_str)
            task_fail_reason[task] = reason
    except Exception as e:
        logging.error(str(e))

    print(
        "{} todo tasks, {} in_progress tasks, {} finished tasks, {} failed tasks\n"
        .format(len(todo_tasks), len(in_progress_tasks), len(finished_tasks),
                len(failed_tasks)))

    if todo:
        print("##" * 24 + "  todo task  " + "##" * 24)
        for task in todo_tasks:
            if my_filter(task):
                print(task)
    if in_progress:
        print("##" * 24 + "  in_progress task  " + "##" * 24)
        for task, output in in_progress_tasks.items():
            if my_filter(task):
                print("{}:         {}".format(task, output))
    if finished:
        print("##" * 24 + "  finished task  " + "##" * 24)
        for task, result in finished_tasks.items():
            if my_filter(task):
                if print_result:
                    print("{}:         {}".format(task, result))
                else:
                    print(task)
    if failed:
        print("##" * 24 + "  failed task  " + "##" * 24)
        for task, worker in failed_tasks.items():
            if my_filter(task):
                print("{}:         {}".format(task, worker))

    if failed_reason and len(task_fail_reason) > 0:
        print("##" * 24 + "  task fail reason " + "##" * 24)
        for task, reason in task_fail_reason.items():
            if my_filter(task):
                print("{}:         {}".format(task, reason))


def print_worker_status(redis_inst,
                        include_str="",
                        exclude_str="",
                        inactive_less_than=-1):
    my_filter = partial(filter_func,
                        include_str=include_str,
                        exclude_str=exclude_str)
    n_finished_tasks = Counter()  # worker -> the num finished tasks
    n_in_progress_tasks = Counter()

    for worker in redis_inst.hvals(REDIS_KEY_IN_PROGRESS_TASKS):
        n_in_progress_tasks[worker] += 1

    for worker_result in redis_inst.hvals(REDIS_KEY_FINISHED_TASKS):
        worker = worker_result.split(":")[0]
        if worker == "m" and worker_result[:2] == "m:":
            worker = ":".join(worker_result.split(":")[:2])
        n_finished_tasks[worker] += 1

    print("{}  {}  {:12} {:>12} {:>12} {:>12} {:>12} {:>12} {:>12} {}".format(
        STATUS_COLOR, "worker", "last_update_from_now", "cores_used",
        "cores_total", "mem_used (GB)", "mem_total (GB)", "n_current_task",
        "n_finished_tasks", NORMAL_COLOR))

    d = redis_inst.hgetall("worker_status")
    for worker, status in sorted(d.items()):
        last_report_ts, used_core, total_core, used_mem_gb, total_mem_gb = status.split(
            ":")
        if inactive_less_than > 0 and time.time() - int(
                last_report_ts) > inactive_less_than:
            continue
        if my_filter(worker):
            print("{:12} {:>12.0f} {:>12} {:>12} {:>12} {:>12} {:>12} {:>12}".
                  format(worker,
                         int(time.time() - int(last_report_ts)), used_core,
                         total_core, used_mem_gb, total_mem_gb,
                         n_in_progress_tasks[worker],
                         n_finished_tasks[worker]))


def cleanup_task(redis_inst,
                 worker_dead_threshold):
    """
    remove dead workers and move their in_progress tasks to todo

    """

    dead_workers = set()
    for worker, status in redis_inst.hscan_iter("worker_status"):
        last_report_ts, used_core, total_core, used_mem_gb, total_mem_gb = status.split(
            ":")
        if time.time() - int(last_report_ts) > worker_dead_threshold:
            # worker is dead, move its in_progress task to todo
            dead_workers.add(worker)
    for worker in dead_workers:
        redis_inst.hdel("worker_status", worker)

    to_return_tasks = []
    for task, worker in redis_inst.hscan_iter(REDIS_KEY_IN_PROGRESS_TASKS):
        if worker in dead_workers:
            to_return_tasks.append(task)
    for task in to_return_tasks:
        redis_inst.hdel(REDIS_KEY_IN_PROGRESS_TASKS, task)
        redis_inst.hset(REDIS_KEY_TODO_TASKS, task, "")

def remove_finished_tasks():
    """
    remove finished tasks
    
    """

    to_remove = []
    for task in redis_inst.hkeys(REDIS_KEY_FINISHED_TASKS):
        to_remove.append(task)

    for task in to_remove:
        redis_inst.hdel(REDIS_KEY_FINISHED_TASKS, task)

def move_in_progress_task_to_todo():
    """
    move in_progress task to todo
    
    """

    for task in redis_inst.hkeys(REDIS_KEY_IN_PROGRESS_TASKS):
        # worker = redis_inst.hget(REDIS_KEY_IN_PROGRESS_TASKS, task)
        redis_inst.hdel(REDIS_KEY_IN_PROGRESS_TASKS, task)
        redis_inst.hset(REDIS_KEY_TODO_TASKS, task, "")

def move_failed_task_to_todo_task():
    """
    move failed task to todo task
    
    """

    for task in redis_inst.hkeys(REDIS_KEY_FAILED_TASKS):
        redis_inst.hdel(REDIS_KEY_FAILED_TASKS, task)
        redis_inst.hset(REDIS_KEY_TODO_TASKS, task, "")

    for task in redis_inst.hkeys(REDIS_KEY_TASK_FAIL_REASON):
        redis_inst.hdel(REDIS_KEY_TASK_FAIL_REASON, task)

if __name__ == "__main__":

    from argparse import ArgumentParser
    from distutils.util import strtobool

    parser = ArgumentParser(description="manage task and worker")

    parser.add_argument("--redis_host",
                        type=str,
                        default=CONFIG.redis_host,
                        help="Redis host")
    parser.add_argument("--redis_port",
                        type=int,
                        default=CONFIG.redis_port,
                        help="Redis port")
    parser.add_argument("--redis_pass",
                        type=str,
                        default=CONFIG.redis_pass,
                        help="Redis auth")
    parser.add_argument("--redis_db",
                        type=str,
                        default=CONFIG.redis_db,
                        help="Redis DB")
    parser.add_argument("--task",
                        type=str,
                        required=True,
                        help="task to execute, initRedis/loadTask/checkWorker/checkTask/checkLog/"+
                                "cleanup/removeFinishedTask/moveInProgressTaskToTodo/moveFailedTaskToTodo"
                        )
    parser.add_argument("--include",
                        type=str,
                        default="",
                        help="filter to show some task/worker")
    parser.add_argument("--exclude",
                        type=str,
                        default="",
                        help="filter to show some task/worker")
    parser.add_argument("--taskfile",
                        type=str,
                        default="task",
                        help="task filepath")

    parser.add_argument("--todo",
                        type=lambda x: bool(strtobool(x)),
                        default=True,
                        help="show todo tasks",
                        )
    parser.add_argument("--finished",
                        type=lambda x: bool(strtobool(x)),
                        default=True,
                        help="show finished tasks",
                        )
    parser.add_argument("--in_progress",
                        type=lambda x: bool(strtobool(x)),
                        default=True,
                        help="show in_progress tasks",
                        )
    parser.add_argument("--failed",
                        type=lambda x: bool(strtobool(x)),
                        default=True,
                        help="show failed tasks",
                        )
    parser.add_argument("--failed_reason",
                        type=lambda x: bool(strtobool(x)),
                        default=True,
                        help="show task failed reason",
                        )
    parser.add_argument("--print_result",
                        type=lambda x: bool(strtobool(x)),
                        default=True,
                        help="print task run stdout",
                        )

    ap = parser.parse_args()
    redis_inst = redis.Redis(
        host=ap.redis_host,
        port=ap.redis_port,
        db=ap.redis_db,
        password=ap.redis_pass,
        decode_responses=True)  # ssl=True, ssl_cert_reqs=None

    tasks = []
    if '&' in ap.task:
        tasks = ap.task.split('&')
    else:
        tasks = [
            ap.task,
        ]

    for task in tasks:
        if task == "initRedis":
            init_redis(redis_inst)
        elif task == "loadTask":
            add_task_to_redis(redis_inst, ap.taskfile)
        elif task == "checkWorker":
            print_worker_status(redis_inst,
                                include_str=ap.include,
                                exclude_str=ap.exclude)
        elif task == "checkTask":
            print_task_status(redis_inst,
                              todo=ap.todo,
                              in_progress=ap.in_progress,
                              finished=ap.finished,
                              failed=ap.failed,
                              failed_reason=ap.failed_reason,
                              print_result=ap.print_result,
                              include_str=ap.include,
                              exclude_str=ap.exclude)
        elif task == "cleanup":
            cleanup_task(redis_inst, CONFIG.health_report_interval * 20)
        elif task == "removeFinishedTask":
            remove_finished_tasks()
        elif task == "moveInProgressTaskToTodo":
            move_in_progress_task_to_todo()
        elif task == "moveFailedTaskToTodo":
            move_failed_task_to_todo_task()
        else:
            raise RuntimeError("unknown task " + task)
