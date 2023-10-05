import datetime
import yaml

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

def read_args(path):
    with open(path, 'r', encoding="utf-8") as f:
        args = yaml.load(f, Loader=yaml.Loader)
        f.close()

    return args


def write_args(args, path):
    with open(path, 'w') as f:
        yaml.dump(args, f, default_flow_style=False, sort_keys=False)
    f.close()


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
