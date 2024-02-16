import yaml
import logging
import asyncio
from functools import wraps
from datetime import datetime
from pathlib import Path
import traceback
import os

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def get_project_root() -> Path:
    return Path(__file__).parent.parent


def log_method(func):
    """
    Decorator around functions to produce logs.
    * Update: Exception is not raised.
    What should method return if there is error?
    """

    @wraps(func)
    def method_check(*args, **kwargs):
        try:
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


def convert_unicode(text: str) -> list:
    unicoded_res = []
    for ch in text:
        unicoded_res.append(ord(ch))
    return unicoded_res


def convert_ascii(unicoded_list: list) -> str:
    res = ""
    for word in unicoded_list:
        res += chr(word)
    return res


def check_timestamp_format(timestamp: str):
    try:
        datetime.datetime.strptime(timestamp, '%Y-%m-%d | %H:%M:%S')
        return True
    except ValueError:
        return False



def general_log(logger, print_text):
    now = datetime.now()
    root = get_project_root()
    current_month_logs = "general_log/{}/".format(now.strftime("%Y-%m"))
    log_folder_path = os.path.join(root, current_month_logs)
    if not os.path.exists(log_folder_path):
        os.makedirs(log_folder_path, exist_ok=True)

    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(
        log_folder_path
        + "{}-{} log.log".format(now.month, str(now.day))
    )
    formatter = logging.Formatter(
        "Time {} , Log: %(name)s - Msg : {text}"
        "\n\n".format(
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-5]), text=print_text)
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.info(print_text)
    handler.close()
    logger.handlers.clear()  # so that handlers don't accumulative add-up