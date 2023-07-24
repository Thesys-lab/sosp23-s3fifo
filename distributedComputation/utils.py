
import json
import time
from threading import Thread, Lock

import os
import sys
import logging
from abc import ABC, abstractmethod
from const import TASK_FORMAT_SEPARATOR, WORKER_STOP_COMMAND

#################################### logging related #####################################
logging.basicConfig(format='%(asctime)s: %(levelname)s [%(filename)s:%(lineno)s]: \t%(message)s',
                    level=logging.INFO, datefmt='%H:%M:%S')


"""
a auto reload config class
it assumes that each config field is independent and updating one field of the config is atomic

"""


class RunnerConfig:
    def __init__(self, conf_path, auto_reload):
        """

        :param conf_path: path to the config file
        :param auto_reload: if True, the config will be reloaded every 20 seconds

        """

        # all config fields
        self.min_dram_gb_trigger_return = None
        self.min_dram_gb_accept_new_task = None
        self.max_task_per_worker = None
        self.max_retry_per_task = None
        self.result_dir = None
        self.health_report_interval = None
        self.sleep_sec_between_accepting_task = None
        self.redis_host = None
        self.redis_port = None
        self.redis_pass = None
        self.redis_db = None

        self.conf_path = conf_path
        self.auto_reload = auto_reload
        self.stop_flag = False
        self.lock = Lock()
        self.load_config()

        if auto_reload:
            self.thread = Thread(target=self.main_loop, args=())
            self.thread.start()


    def load_config(self):
        self.lock.acquire()
        with open(self.conf_path) as f:
            conf_data = json.load(f)

            # task related
            self.min_dram_gb_trigger_return = int(
                conf_data["min_dram_gb_trigger_return"])
            self.min_dram_gb_accept_new_task = int(
                conf_data["min_dram_gb_accept_new_task"])
            self.max_task_per_worker = int(conf_data["max_task_per_worker"])
            self.max_retry_per_task = int(conf_data["max_retry_per_task"])
            self.result_dir = conf_data["result_dir"]

            # worker related
            self.health_report_interval = int(
                conf_data["health_report_interval"])
            self.sleep_sec_between_accepting_task = int(
                conf_data["sleep_sec_between_accepting_task"])

            # redis related
            self.redis_host = conf_data["redis_host"]
            self.redis_port = int(conf_data["redis_port"])
            self.redis_pass = conf_data["redis_pass"]
            self.redis_db = int(conf_data["redis_db"])
        self.lock.release()

    def stop(self):
        self.stop_flag = True
        self.thread.join()

    def main_loop(self):
        while not self.stop_flag:
            self.load_config()
            time.sleep(20)

    def __del__(self):
        if self.auto_reload:
            self.stop()
            self.thread.join()


class Task:
    """
    represents a bash task

    """

    def __init__(self, task_str):
        self.task_str = task_str
        self.task_type = None
        self.task_params = None
        self.min_dram_gb = None
        self.require_cpu_core = None
        self.priority = None
        try:
            self.parse_task_str(task_str)
        except Exception as e:
            logging.error(f"parse task str error: {e}, task str: {task_str}")
            logging.error(
                f"task str format task_type:priority:min_dram:min_cpu:task_params, e.g. shell:5:8:0:echo hello")

    def parse_task_str(self, task_str):
        task_type, priority, dram, cpu, task_params = task_str.split(
            TASK_FORMAT_SEPARATOR)
        self.task_type = task_type
        self.priority = int(priority)
        self.min_dram_gb = int(dram)
        self.require_cpu_core = int(cpu)
        self.task_params = task_params
        
    def is_task_str_valid(task_str):
        """
        task str format task_type:priority:min_dram:min_cpu:task_params, e.g. shell:5:8:0:echo hello

        """

        try:
            task_type, priority, dram, cpu, task_params = task_str.split(
                TASK_FORMAT_SEPARATOR)
            if task_type not in ["shell", "python"]:
                return False
            if not priority.isdigit() or int(priority) <0:
                return False
            if not dram.isdigit() or int(dram) < 0:
                return False
            if not cpu.isdigit() or int(cpu) < 0:
                return False
            if task_params == "":
                return False

            return True
        except Exception as e:
            return False

    def __str__(self):
        return f"task_type: {self.task_type}, priority: {self.priority}, " + \
            f"min_dram_gb: {self.min_dram_gb}, require_cpu_core: {self.require_cpu_core}, " + \
            f"task_params: {self.task_params}"

    def __repr__(self):
        return self.__str__()

    def __hash__(self) -> int:
        return hash(self.task_str)

    def __eq__(self, __o: object) -> bool:
        return self.task_str == __o.task_str

    def __ne__(self, __o: object) -> bool:
        return self.task_str != __o.task_str

    def __lt__(self, __o: object) -> bool:
        return self.priority < __o.priority

    def __le__(self, __o: object) -> bool:
        return self.priority <= __o.priority

    def __gt__(self, __o: object) -> bool:
        return self.priority > __o.priority

    def __ge__(self, __o: object) -> bool:
        return self.priority >= __o.priority


class EmptyTask(Task):
    def __init__(self):
        super(EmptyTask, self).__init__(f"0:0:0:0:0")

    def __str__(self):
        return "Empty Task"

class EndofTask(Task):
    def __init__(self):
        super(EndofTask, self).__init__(f"{WORKER_STOP_COMMAND}:0:0:0:{WORKER_STOP_COMMAND}")

    def __str__(self):
        return "End of Task"

EMPTY_TASK = EmptyTask()
END_OF_TASK = EndofTask()


class Tasks:
    def __init__(self, task_dict):
        self.task_dict = task_dict

    def parse_task_dict(self):
        pass


def test_runner_config():
    conf = RunnerConfig("conf.json")
    time.sleep(2)
    for i in range(20):
        print(conf.min_dram_gb_trigger_return)
        time.sleep(8)
    conf.stop()


def test_task():
    task_str = "shell:5:8:0:echo hello"
    task = Task(task_str)
    print(task)


if __name__ == "__main__":
    # test_runner_config()
    # test_task()
    print(EmptyTask.task_str, EndofTask)
    