import redis
from const import *

redis_inst = redis.Redis(
    host="localhost",
    port="6400",
    db=0,
    password="cloudlab",
    decode_responses=True)  # ssl=True, ssl_cert_reqs=None

def update_task():
    for task in redis_inst.hkeys(REDIS_KEY_FINISHED_TASKS):
        task = task.replace("./cachesim", "./cachesim2")
        redis_inst.hset(REDIS_KEY_TODO_TASKS, task, "")

    for task in redis_inst.hkeys(REDIS_KEY_IN_PROGRESS_TASKS):
        task = task.replace("./cachesim", "./cachesim2")
        redis_inst.hset(REDIS_KEY_TODO_TASKS, task, "")

    for task in redis_inst.hkeys(REDIS_KEY_TODO_TASKS):
        redis_inst.hdel(REDIS_KEY_FINISHED_TASKS, task)
        task = task.replace("./cachesim", "./cachesim2")
        redis_inst.hset(REDIS_KEY_TODO_TASKS, task, "")

if __name__ == "__main__":
    update_task()

