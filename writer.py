import pdb
import queue
import random
import time
import pandas as pd
from client import FloatModbusClient
from utils import *
import os
import datetime
import colorama

colorama.init()


def open_connection(client, host, port=502):
    res = True
    if not client.is_open:
        try:
            client.host = host
            client.port = port
            res = client.open()

        except Exception as e:
            print(e)
            res = False

    return res


def connect(client, args, time_out=2):
    res = False
    [primary_host, primary_port] = args.hosts[0]
    [secondary_host, secondary_port] = args.hosts[1]

    while not res and time_out > 0:
        res = open_connection(client, primary_host, primary_port)
        if res:
            print(f'{bcolors.OKBLUE}Connected to {primary_host} at {primary_port}{bcolors.ENDC}')
        else:
            res = open_connection(client, secondary_host, secondary_port)
            if res:
                print(f'{bcolors.OKBLUE}Connected to {secondary_host} at {secondary_port}{bcolors.ENDC}')
        time_out -= 1
        time.sleep(1)

    if not res:
        print(f'{bcolors.FAIL}Failed to connect{bcolors.ENDC}')
    return res


def write(client, rand_num):
    args = read_args('./configs/configs.yaml')
    try_connect = connect(client, args)

    if not try_connect:
        return
    try:
        for category, address in args.reg_addr.items():
            client.write_float(address, [rand_num])
            print(f'Successfully wrote {rand_num} to {address}')
        val_to_write = 0

        for sensor, coil_address in args.coil_addr.items():
            client.write_single_coil(coil_address, val_to_write)
            print(f'Successfully wrote {val_to_write} to {coil_address}')
        pdb.set_trace()

    except Exception as e:
        print(f'Failed to write data because of {e}')

    client.close()


if __name__ == "__main__":
    client = FloatModbusClient(timeout=2.0)
    while True:
        rand_num = random.randint(1, 100)
        write(client, rand_num)
        time.sleep(1.0)

