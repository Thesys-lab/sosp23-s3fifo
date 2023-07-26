
# DistComp: a distributed computation platform
DistComp is a simple tool that uses data parallelism to speed up computation. It is designed to be easy to use. 
I have been using it on Cloudlab to use up to 100 nodes to speed up my experiments.

![DistComp diagram](/diagram/diagram.svg)

## Architecture
DistComp uses a master-worker architecture. The master node is storing the tasks using a redis instance. The worker nodes perform the computation. 
Current design decouples task submission and task execution. A manager submits tasks to the Redis queue. The worker nodes will poll the queue and execute the tasks.

## Features
* **DistCom maximizes resource usage**: it runs as many jobs as possible on each node. When some tasks' memory usage grow over time and the worker is going to run out of memory, the most recent task will be returned to the to do taks queue.
* **On-demand task submission**: new tasks can be submitted at any time.
* **Fault tolerance**: Restarted workers can fetch its previous tasks to continue, and if some workers fail, the failed tasks can be moved to the todo queue.
* **Different types of tasks**: DistComp supports both bash jobs and Python jobs.


## How to use
### 0. Prepare worker nodes
You need to prepare the worker nodes to run the tasks, if your task requires data, the data must be accessible on the worker nodes.
You can consider using a cluster file system, e.g., MooseFS, to aggregate disk capacity from all workers and provide high-bandwidth access to data. 
In addition, the worker and manager nodes need to install `redis` and `psutil` packages. 
```bash
pip install redis psutil
```

### 1. Setup Redis on the master node
```bash

bash ./redis.sh
```

### 2. Create the tasks to be ran
Create a file contains all the tasks. Each line in the file consists of a task in the following format:

```bash
# task type:priority:min_dram:min_cpu:task_params
# echo 'shell:4:2:2:./cachesim PARAM1 PARAM2' >> task

# submit the taks to the Redis
python3 redisManager.py --task 'initRedis&loadTask' --taskfile task

```


### 3. Start the worker nodes
We use the `parallel-ssh` tool to start the worker nodes, and list of workers are stored in the `host` file.

```bash

parallel-ssh -h host -i -t 0 '''
    cd /PATH/TO/DistComp;
    screen -S worker -L -Logfile workerScreen/$(hostname) -dm python3 redisWorker.py
'''
```

### 4. Monitor the progress
```bash
# check the task status
python3 redisManager.py --task checkTask --finished false --todo false --in_progress false --failed false

# check the worker status
python3 redisManager.py --task checkWorker

# monitor the task progress
watch "python3 redisManager.py --task 'checkTask&checkWorker' --finished false --print_result false --in_progress false"

```
