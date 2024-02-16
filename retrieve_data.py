import csv
import datetime
import os
import pdb
import time
from queue import Queue

from pyModbusTCP.utils import get_list_2comp, long_list_to_word, encode_ieee, decode_ieee, word_list_to_long
from pymodbus.client import (
    ModbusSerialClient,
    ModbusTcpClient
)

from pyModbusTCP.client import ModbusClient
from pymodbus.exceptions import ModbusException, ModbusIOException, ParameterException, NotImplementedException

from components.utils import *
from pymodbus.payload import BinaryPayloadDecoder


class CacheQueue():
    def __init__(self, dirty=False):
        self.coil_q = Queue()
        self.reg_q = Queue()
        self.batch_size = 100
        args = read_args('configs/configs.yaml')

        if not dirty:
            self.coil_path = "./saved_data/coil_data"
            self.reg_path = "./saved_data/reg_data"
        else:
            self.coil_path = "./saved_data/coil_data_dirty"
            self.reg_path = "./saved_data/reg_data_dirty"

        self.coil_cols = args.coil_addr.keys()
        self.reg_cols = args.reg_addr.keys()

        self.date_format = "%Y-%m-%d %H:%M:%S"

        """
        COP1    1ZYR5311    0
        COP2    1ZYR5312    1
        AGC1    T1_L83EX    29
        AGC2    T2_L83EX    30
        """

        self.prev_cop = None
        self.prev_agc = None
        self.retrieving = False

        self.last_coil_row = None
        self.last_reg_row = None

    def put_coil_bits(self, row):
        if self.coil_q.qsize() > self.batch_size:
            self.save_digital_to_file()

        # The digital doesn't change as fast as analog, it might lead to inconsistency to the number of rows in digital data and analog data
        # That's why flag is used. It indicates if data is new or not, but stores it anyways.
        flag = True
        if self.last_coil_row is not None:
            if self.last_coil_row == row:
                flag = False

        self.coil_q.put(row)
        self.last_coil_row = row
        return flag

    def save_digital_to_file(self):
        write_header = False

        current_date = datetime.now().strftime("%Y-%m-%d")
        path_name = f"{self.coil_path}_{current_date}.csv"

        if not os.path.isfile(path_name):
            write_header = True

        with open(path_name, 'a') as file:
            writer = csv.writer(file)

            if write_header:
                columns = [col_name for col_name in self.coil_cols]
                writer.writerow(columns)

            while not self.coil_q.empty():
                row = self.coil_q.get()
                writer.writerow(row)

    def put_reg_data(self, row):
        if self.reg_q.qsize() > self.batch_size:
            self.save_analog_to_file()

        # Look at description in put_coil_bits() method
        flag = True
        if self.last_reg_row is not None:
            if self.last_reg_row == row:
                flag = False
        self.reg_q.put(row)
        self.last_reg_row = row
        return flag

    def save_analog_to_file(self):
        write_header = False

        current_date = datetime.now().strftime("%Y-%m-%d")
        path_name = f"{self.reg_path}_{current_date}.csv"

        if not os.path.isfile(path_name):
            write_header = True

        with open(path_name, 'a') as file:
            writer = csv.writer(file)

            if write_header:
                columns = [col_name for col_name in self.reg_cols]
                writer.writerow(columns)

            while not self.reg_q.empty():
                row = self.reg_q.get()
                writer.writerow(row)


def start_retrieve(prev_cops, prev_agcs, current_cops, current_agcs):
    if not prev_cops or not prev_agcs:
        total = zip(current_cops, current_agcs)
    else:
        total = zip(prev_cops, prev_agcs, current_cops, current_agcs)

    for zipped_vals in total:
        if len(zipped_vals) > 2:
            prev_cop, prev_agc, current_cop, current_agc = zipped_vals
            if (not prev_cop and not prev_agc) and (current_cop and not current_agc):
                return True
            else:
                return False
        else:
            current_cop, current_agc = zipped_vals
            if current_cop and not current_agc:
                return True
            else:
                return False


def stop_retrieve(current_agc):
    for agc_val in current_agc:
        if agc_val:
            return True
    return False


@log_method
def read_digital(client, cache, start_address=0, number_coils=96, max_retry=2, test_algo=True):
    """ Read coils twice. In case of receiving empty package, retry again"""
    retrial = 0
    successfully_received = False

    while not successfully_received or retrial >= max_retry:
        try:
            res_bits = client.read_coils(start_address, number_coils, slave=1)
            if not res_bits.isError():
                response = res_bits.bits
                if not response:
                    retrial += 1
                    print("!!! Empty Package, retry")
                    continue
                successfully_received = True
                response = response[:number_coils]

                print(f'Reading coils, isDirty: {not test_algo} , try number {retrial} >>>>>', response)
                # Detect if we should retrieve
                cop = (response[0], response[1])
                agc = (response[29], response[30])

                if test_algo:
                    if not cache.retrieving:
                        cache.retrieving = start_retrieve(cache.prev_cop, cache.prev_agc, cop, agc)
                    else:
                        cache.retrieving = not stop_retrieve(agc)

                    cache.prev_agc = agc
                    cache.prev_cop = cop

                    print("****** Cache retrieving status ", cache.retrieving)
                    if cache.retrieving:
                        cache.put_coil_bits(response)

                else:
                    cache.put_coil_bits(response)

                return response

        except (ModbusException, ModbusIOException, ParameterException, NotImplementedException) as MODBUS_EXCEPTIONS:
            print(MODBUS_EXCEPTIONS)

        except Exception as GENERAL_EXCEPTIONS:
            print(GENERAL_EXCEPTIONS)


@log_method
def read_analog_1(client, cache, start_address=0, registers_number=112, max_retry=2, test_algo=True):
    cycle_run = 0
    retrial = 0
    successfully_received = False

    # Conversion to analog addresses
    if registers_number > 64:
        registers_number = registers_number * 2

    if test_algo and not cache.retrieving:
        return None

    while not successfully_received:
        # 1st Pack Of Registers
        regs_pack1_num = 124
        regs_pack1 = None
        while retrial < max_retry:
            cycle_run += 1
            try:
                regs_1 = client.read_holding_registers(start_address, regs_pack1_num, slave=1)
                if not regs_1.isError():
                    if not regs_1.registers:
                        retrial += 1
                        print("!!! Empty Package, retry")
                        continue
                    regs_pack1 = [decode_ieee(f) for f in word_list_to_long(regs_1.registers)]
                    print(f"Reading registers 1, isDirty: {not test_algo}, try number {retrial} >>>>> ", regs_pack1)
                    break

            except (
                    ModbusException, ModbusIOException, ParameterException,
                    NotImplementedException) as MODBUS_EXCEPTIONS:
                print(MODBUS_EXCEPTIONS)

            except Exception as GENERAL_EXCEPTIONS:
                print(GENERAL_EXCEPTIONS)  # Probably need to store.

            if cycle_run > 10:
                print(f"\033[91m Couldn't receive data. Restart network card. \033[0m")

        # Second pack of registers
        regs_pack2_num = registers_number - regs_pack1_num
        regs_pack2 = None
        cycle_run = 0
        retrial = 0
        while retrial < max_retry:
            cycle_run += 1
            try:
                regs_2 = client.read_holding_registers(regs_pack1_num, regs_pack2_num, slave=1)
                if not regs_2.isError():
                    if not regs_2.registers:
                        retrial += 1
                        print("!!! Empty Package, retry")
                        continue
                    regs_pack2 = [decode_ieee(f) for f in word_list_to_long(regs_2.registers)]
                    print(f"Reading registers 2, isDirty: {not test_algo}, try number {retrial} >>>>> ", regs_pack2)
                    break

            except (
                    ModbusException, ModbusIOException, ParameterException,
                    NotImplementedException) as MODBUS_EXCEPTIONS:
                print(MODBUS_EXCEPTIONS)

            except Exception as GENERAL_EXCEPTIONS:
                print(GENERAL_EXCEPTIONS)  # Probably need to store.

            if cycle_run > 10:
                print(f"\033[91m Couldn't receive data. Restart network card. \033[0m")

        if regs_pack1 is not None and regs_pack2 is not None:
            successfully_received = True
            total_regs = regs_pack1 + regs_pack2

            if cache.put_reg_data(total_regs):
                return total_regs


def connect():
    # client = ModbusSerialClient(
    #     port='COM3',
    #     timeout=1,
    #     baudrate=19200
    # )
    client = ModbusTcpClient(host="192.168.8.100", port=501, auto_open=True, auto_close=True)
    client.connect()
    return client


@log_method
def main():
    now = datetime.now()
    print(f"\033[94m! Start Retrieving Data, Time: {now} \033[0m")
    client = connect()
    cache = CacheQueue()
    logger = logging.getLogger("General Logger")
    cache_dirty = CacheQueue(dirty=True)

    cycle_run = 0
    while True:
        start_time = datetime.now()
        digital_data = read_digital(client, cache)
        analog_data = read_analog_1(client, cache)

        digital_data_all = read_digital(client, cache_dirty, test_algo=False)
        analog_data_all = read_analog_1(client, cache_dirty, test_algo=False)

        end_time = datetime.now()
        print(f"\033[92mTime TAKEN: {end_time - start_time} \033[0m", "\n")
        general_log(logger, f"Time TAKEN: {end_time - start_time}")

        if digital_data and analog_data:
            cycle_run = 0
            # send over websockets
            pass

        if not digital_data and not analog_data and cache.retrieving:
            cycle_run += 1

        if cycle_run > 10:
            print(f"\033[91m Couldn't receive data. Restart network card. \033[0m")

        time.sleep(1)


def main1():
    client = ModbusClient(host="192.168.8.100", port=501, auto_open=True, debug=False)
    test = client.read_coils(1, 55)
    test1 = client.read_holding_registers(1, 90)


if __name__ == "__main__":
    while True:
        # Restart Loop, in case of failure
        try:
            main()
            # main1()
        except Exception as excep:
            time.sleep(1)
            print("************ Automatic Restart ****************")

#
# @log_method
# def read_analog(client, cache, start_address=0, registers_number=111, trials=2, max_retry=2):
#     curr = 0
#     retrial = 0
#     successfully_received = False
#     while curr < trials or not successfully_received:
#         try:
#             regs_1 = client.read_holding_registers(start_address, registers_number, slave=1)
#             if not regs_1.isError():
#                 if not regs_1.registers:
#                     curr -= 1
#                     retrial += 1
#                     if retrial >= max_retry:
#                         break
#                     print("!!! Empty Package, retry")
#                     continue
#                 successfully_received = True
#                 print(f"Reading registers, try number {curr} >>>>> ",
#                       [decode_ieee(f) for f in word_list_to_long(regs_1.registers)])
#
#                 # if cache.retrieving:
#                 #     actual_values = [f for f in get_list_2comp(regs_1.registers, 16)]
#                 #     cache.put_reg_data(actual_values)
#
#                 actual_values = [decode_ieee(f) for f in word_list_to_long(regs_1.registers)]
#
#                 # actual_values = long_list_to_word(temp)
#                 if cache.put_reg_data(actual_values):
#                     return actual_values
#
#         except (ModbusException, ModbusIOException, ParameterException, NotImplementedException) as MODBUS_EXCEPTIONS:
#             print(MODBUS_EXCEPTIONS)
#
#         except Exception as GENERAL_EXCEPTIONS:
#             print(GENERAL_EXCEPTIONS)  # Probably need to store.
#
#         finally:
#             curr += 1
