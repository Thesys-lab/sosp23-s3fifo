#################################### setting ####################################
NORMAL_COLOR = "\033[0;37;40m"
TASK_COLOR = "\033[1;32;40m"
WORKER_COLOR = "\033[1;33;40m"
ALERT_COLOR = "\033[5;36;40m"
STATUS_COLOR = "\033[1;34;47m"

STATUS_COLOR = ""
NORMAL_COLOR = ""

KiB = 1024
MiB = 1024 * KiB
GiB = 1024 * MiB
TiB = 1024 * GiB

#################################### task #####################################
WORKER_STOP_COMMAND = "WORKER_COMMAND_CLOSE"
TASK_FORMAT_SEPARATOR = ":"


#################################### redis #####################################
REDIS_KEY_TODO_TASKS = "todo_tasks"
REDIS_KEY_IN_PROGRESS_TASKS = "in_progress_tasks"
REDIS_KEY_FAILED_TASKS = "failed_tasks"
REDIS_KEY_FINISHED_TASKS = "finished_tasks"
REDIS_KEY_TASK_FAIL_REASON = "task_fail_reason"


#################################### other #####################################


CONFIG_PATH = "conf.json"

