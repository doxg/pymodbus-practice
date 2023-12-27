import yaml
import logging
import asyncio
from functools import wraps
from datetime import datetime
from pathlib import Path
import traceback
import os


def get_project_root() -> Path:
    return Path(__file__).parent.parent


def log_method(func):
    """
    Decorator around functions to produce logs.
    * Update: Exception is not raised.
    What should method return if there is error?
    """

    @wraps(func)
    async def method_check(*args, **kwargs):
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            return result
        except Exception as e:
            log_generate(func.__name__, e, "method")
            print(e)
            # raise Exception(e)
        # return result

    return method_check


def log_generate(func_name: str, e: Exception, err_type: str = "method"):
    """
    Writes down logs of exception/errors to specific file.
    """
    now = datetime.now()
    root = get_project_root()
    current_month_logs = "log/{}/".format(now.strftime("%Y-%m"))
    log_folder_path = os.path.join(root, current_month_logs)
    if not os.path.exists(log_folder_path):
        os.makedirs(log_folder_path, exist_ok=True)

    logger = logging.getLogger(func_name)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(
        log_folder_path
        + "{}-{}_{} err log.log".format(now.month, str(now.day), err_type)
    )
    formatter = logging.Formatter(
        "{func_name} method - {} - Logger: %(name)s - ErrorMsg: {}"
        "\n\n %(message)s"
        "\n\n".format(
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-5]),
            e,
            func_name=func_name,
        )
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.error(traceback.format_exc())
    handler.close()
    logger.handlers.clear()  # so that handlers don't accumulative add-up



def write_args(args, path):
    with open(path, 'w') as f:
        yaml.dump(args, f, default_flow_style=False, sort_keys=False)
    f.close()


def read_args(path):
    with open(path, "r", encoding="utf-8") as f:
        args = yaml.load(f, Loader=yaml.Loader)
        f.close()

    return args