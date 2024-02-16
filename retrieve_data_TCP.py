import asyncio
import csv
import datetime
import json
import pdb
import time
from queue import Queue
import threading

import websockets
from pyModbusTCP.utils import decode_ieee, word_list_to_long
from pymodbus.client import (
    ModbusTcpClient
)
from pymodbus.exceptions import ModbusException, ModbusIOException, ParameterException, NotImplementedException

from components.utils import *


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
        self.tagnames = [regtag for regtag in self.reg_cols if
                         regtag not in ["1CCGPS-SEC", "1CCGPS-MIN", "1CCGPS-HOUR", "1CCGPS-DAYM", "1CCGPS-MNTH",
                                        "1CCGPS-YEAR"]] + [coiltag for coiltag in self.coil_cols]

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
        self.last_received_datetime = None

    def put_coil_bits(self, row):
        if self.coil_q.qsize() > self.batch_size:
            self.save_digital_to_file()

        self.coil_q.put(row)
        self.last_coil_row = row

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

        self.reg_q.put(row)
        self.last_reg_row = row

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

    def get_last_saved_data(self):
        # 13~18 SEC, MIN, HOUR, DAY, MONTH, YEAR
        data = self.last_reg_row[:13] + self.last_reg_row[19:] + self.last_coil_row
        res = {tag: val for tag, val in zip(self.tagnames, data)}
        res['date'] = self.last_received_datetime.strftime("%Y-%m-%d %H:%M:%S")
        return res


def convert_to_timestamp(register_vals):
    datetime_indexes = [x for x in range(18, 12, -1)]  # Use constants later
    date_format = "%Y-%m-%d %H:%M:%S"
    year, month, day, hour, minute, sec = [int(register_vals[ind]) for ind in datetime_indexes]
    datetime_str = f'{year + 2000}-{month}-{day} {hour}:{minute}:{sec}'
    try:
        res = datetime.strptime(datetime_str, date_format)
    except Exception as e:
        res = None

    return res


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
    response = None

    while not successfully_received and retrial <= max_retry:
        retrial += 1
        try:
            res_bits = client.read_coils(start_address, number_coils, slave=1)
            if not res_bits.isError():
                response = res_bits.bits
                if not response:
                    print("!!! Empty Package, retry")
                    continue
                successfully_received = True
                response = response[:number_coils]

                # print(f'Reading coils, isDirty: {not test_algo} , try number {retrial} >>>>>', response)
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
                    print("Digital data saved at ", cache.last_received_datetime)


        except (ModbusException, ModbusIOException, ParameterException, NotImplementedException) as MODBUS_EXCEPTIONS:
            print(MODBUS_EXCEPTIONS)

        except Exception as GENERAL_EXCEPTIONS:
            print(GENERAL_EXCEPTIONS)

    return response


def read_registers_pack(client, start_address, registers_num, max_retry=2):
    retrial = 0
    regs_pack = None
    while retrial < max_retry:
        retrial += 1
        try:
            regs = client.read_holding_registers(start_address, registers_num, slave=1)
            if not regs.isError():
                if not regs.registers:
                    print("!!! Empty Package, retry")
                    continue
                regs_pack = [decode_ieee(f) for f in word_list_to_long(regs.registers)]
                # print(
                #     f"Reading registers from {start_address} to {start_address + registers_num}, try number {retrial} >>>>> ",
                #     regs_pack)
                break
        except (
                ModbusException, ModbusIOException, ParameterException,
                NotImplementedException) as MODBUS_EXCEPTIONS:
            print(MODBUS_EXCEPTIONS)

        except Exception as GENERAL_EXCEPTIONS:
            print(GENERAL_EXCEPTIONS)  # Probably need to store.

    return regs_pack


@log_method
def read_analog(client, cache, start_address=0, registers_number=112, max_retry=2, test_algo=True):
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
        regs_pack1 = read_registers_pack(client, start_address, regs_pack1_num)

        # Second pack of registers
        regs_pack2_num = registers_number - regs_pack1_num
        if regs_pack2_num > 0:
            regs_pack2 = read_registers_pack(client, regs_pack1_num, regs_pack2_num)
        else:
            regs_pack2 = None
        # Remake logic
        if regs_pack1 is not None and regs_pack2 is not None:
            successfully_received = True
            total_regs = regs_pack1 + regs_pack2
            timestamp = convert_to_timestamp(total_regs)
            if not timestamp:
                return None
            if cache.last_received_datetime is not None:
                if timestamp.second % 9 == 0:
                    return None

                diff = timestamp - cache.last_received_datetime
                if diff.total_seconds() < 1:
                    return None
            cache.last_received_datetime = timestamp
            cache.put_reg_data(total_regs)
            return total_regs
        else:
            return None


def connect():
    args = read_args('configs/configs.yaml')
    client = ModbusTcpClient(host=args.host, port=args.port, auto_open=True, auto_close=True)
    client.connect()
    return client


@log_method
def main():
    now = datetime.now()
    print(f"\033[94m! Start Retrieving Data, Time: {now} \033[0m")
    client = connect()
    cache = CacheQueue()
    cache_dirty = CacheQueue(dirty=True)

    worker_thread1 = threading.Thread(target=run_in_thread, args=[cache_dirty])
    worker_thread1.start()

    # worker_thread2 = threading.Thread(target=run_in_thread, args=[cache_dirty, AIENGINE_URL])
    # worker_thread2.start()

    cycle_run = 0
    while True:
        start_time = datetime.now()
        # digital_data = read_digital(client, cache)
        # analog_data = read_analog(client, cache)

        analog_data_all = read_analog(client, cache_dirty, test_algo=False)
        if analog_data_all:
            digital_data_all = read_digital(client, cache_dirty, test_algo=False)


        end_time = datetime.now()
        # print(f"\033[92mTime TAKEN: {end_time - start_time} \033[0m", "\n")

        time.sleep(0.2)


async def send_to_server(cache, url):
    prev_last_sent = None
    print("Started method send_to_server for ", url)
    while True:
        try:
            async with websockets.connect(url) as websocket:
                while True:
                    if prev_last_sent != cache.last_received_datetime:
                        last_data = cache.get_last_saved_data()
                        last_data["1CCTIME"] = 640
                        now = datetime.now()
                        current_time = now.strftime("%H:%M:%S")
                        message = json.dumps({"Datetime Key": current_time, "Payload": last_data})
                        await websocket.send(message)
                        print("!!!!! Sent Data to ", url, cache.last_received_datetime)
                        prev_last_sent = cache.last_received_datetime

                    await asyncio.sleep(0.5)

        except Exception as e:
            print(str(e), "Reconnect after 5 sec ")
            await asyncio.sleep(5)
        # pdb.set_trace()


def run_in_thread(cache):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    BACKEND_URL = "ws://192.168.8.101:8000/ws/10_dcs"
    AIENGINE_URL = "ws://192.168.8.101:8080/"

    tasks = [loop.create_task(send_to_server(cache,BACKEND_URL)),
             loop.create_task(send_to_server(cache,AIENGINE_URL))]

    loop.run_until_complete(asyncio.gather(*tasks))


if __name__ == "__main__":
    while True:
        # Restart Loop, in case of failure
        try:
            main()
        except Exception as excep:
            time.sleep(1)
            print("************ Automatic Restart ****************")
