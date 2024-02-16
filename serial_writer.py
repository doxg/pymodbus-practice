import pdb
import queue
import random
import time
import pandas as pd
from client import FloatModbusClient
from pymodbus.client import ModbusSerialClient
from components.utils import *



def write_digital(args, client):
    coil_addr = args.coil_addr
    first_addr = list(coil_addr.values())[0]
    num = len(coil_addr)
    rand_num = random.uniform(0,1)
    client.write_coils(first_addr, [rand_num for _ in range(num)])

def write_analog(args,client):
    reg_add = args.reg_addr
    first_addr = list(reg_add.values())[0]
    num = len(reg_add)
    rand_num = random.randint(1, 100)
    client.write_registers(first_addr, [rand_num for _ in range(num)])




if __name__ == "__main__":
    client = ModbusSerialClient(port='COM3',
                                timeout=1,
                                baudrate=19200)
    client.connect()
    args = read_args('configs/configs.yaml')

    while True:
        write_digital(args,client)
        write_analog(args,client)
        time.sleep(1.0)
