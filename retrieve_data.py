import csv
import datetime
import os
import time
from queue import Queue

from pyModbusTCP.utils import get_list_2comp
from pymodbus.client import (
    ModbusSerialClient,
)
from pymodbus.exceptions import ModbusException, ModbusIOException, ParameterException, NotImplementedException

from components.utils import *


class CacheQueue():
    def __init__(self):
        self.coil_q = Queue()
        self.reg_q = Queue()
        self.batch_size = 100
        args = read_args('./configs/configs.yaml')

        self.coil_path = "./saved_data/coil_data.csv"
        self.coil_cols = args.coil_addr.keys()
        self.reg_path = "./saved_data/coil_data.csv"
        self.reg_cols = args.reg_addr.keys()

        self.date_format = "%Y-%m-%d %H:%M:%S"

        """
        COP1    1ZYR5311    100
        COP2    1ZYR5312    101
        AGC1    T1_L83EX    129
        AGC2    T2_L83EX    130
        """

        self.prev_cop = None
        self.prev_agc = None
        self.retrieving = False

    def put_coil_bits(self, row):
        if self.coil_q.qsize() > self.batch_size:
            self.save_digital_to_file()
        now = datetime.datetime.now()
        row.append(datetime.datetime.strftime(now, self.date_format))
        self.coil_q.put(row)

    def save_digital_to_file(self):
        write_header = False

        if not os.path.isfile(self.coil_path):
            write_header = True

        with open(self.coil_path, 'a') as file:
            writer = csv.writer(file)

            if write_header:
                writer.writerow(self.coil_cols)

            while not self.coil_q.empty():
                row = self.coil_q.get()
                writer.writerow(row)

    def put_reg_data(self, row):
        if self.reg_q.qsize() > self.batch_size:
            self.save_analog_to_file()
        now = datetime.datetime.now()
        row.append(datetime.datetime.strftime(now, self.date_format))
        self.reg_q.put(row)

    def save_analog_to_file(self):
        write_header = False

        if not os.path.isfile(self.reg_path):
            write_header = True

        with open(self.reg_path, 'a') as file:
            writer = csv.writer(file)

            if write_header:
                writer.writerow(self.reg_cols)

            while not self.reg_q.empty():
                row = self.reg_q.get()
                writer.writerow(row)


@log_method
def read_digital(client, cache, start_address=100, number_coils=83, trials=2, max_retry=1):
    """ Read coils twice. In case of receiving empty package, retry again"""
    curr = 0
    retrial = 0
    successfully_received = False
    while curr < trials or successfully_received:
        try:
            res_bits = client.read_coils(start_address, number_coils, slave=1)
            if not res_bits.isError():
                response = res_bits.bits
                if not response and retrial < max_retry:
                    curr -= 1
                    retrial += 1
                    continue
                successfully_received = True
                # Detect if we should retrieve
                cop = (response[0], response[1])
                agc = (response[29], response[30])

                if not cache.retrieving:
                    cache.retrieving = start_retrieve(cache.prev_cop, cache.prev_agc, cop, agc)
                else:
                    cache.retrieving = not stop_retrieve(agc)

                if cache.retrieving:
                    cache.put_coil_bits(response)

                cache.prev_agc = agc
                cache.prev_cop = cop

        except (ModbusException, ModbusIOException, ParameterException, NotImplementedException) as MODBUS_EXCEPTIONS:
            print(MODBUS_EXCEPTIONS)

        except Exception as GENERAL_EXCEPTIONS:
            print(GENERAL_EXCEPTIONS)

        finally:
            curr += 1


@log_method
def read_analog(client, cache, start_address=301, registers_number=83, trials=2, max_retry=1):
    curr = 0
    retrial = 0
    successfully_received = False
    while curr < trials or successfully_received:
        try:
            regs_1 = client.read_holding_registers(start_address, registers_number, slave=1)
            if not regs_1.isError():
                if not regs_1.registers and retrial < max_retry:
                    curr -= 1
                    retrial += 1
                    continue
                successfully_received = True
                if cache.retrieving:
                    actual_values = [f for f in get_list_2comp(regs_1.registers, 16)]
                    cache.put_reg_data(actual_values)

        except (ModbusException, ModbusIOException, ParameterException, NotImplementedException) as MODBUS_EXCEPTIONS:
            print(MODBUS_EXCEPTIONS)

        except Exception as GENERAL_EXCEPTIONS:
            print(GENERAL_EXCEPTIONS)  # Probably need to store.

        finally:
            curr += 1


def start_retrieve(prev_cops, prev_agcs, current_cops, current_agcs):
    for prev_cop, prev_agc, current_cop, current_agc in zip(prev_cops, prev_agcs, current_cops, current_agcs):
        if (not prev_cop and not prev_agc) and (current_cop and not current_agc):
            return True
        else:
            return False


def stop_retrieve(current_agc):
    for agc_val in current_agc:
        if agc_val:
            return True
    return False


def connect():
    client = ModbusSerialClient(
        port='COM3',
        timeout=1,
        baudrate=19200
    )
    client.connect()
    return client


@log_method
def main():
    client = connect()
    cache = CacheQueue()
    while True:
        read_digital(client, cache)
        read_analog(client, cache)


if __name__ == "__main__":
    while True:
        # Restart Loop, in case of failure
        try:
            main()
        except Exception as excep:
            time.sleep(1)
