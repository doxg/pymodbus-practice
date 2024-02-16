import logging
import datetime
from pymodbus.server import StartSerialServer
from pyModbusTCP.utils import *
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusServerContext, ModbusSlaveContext
from components.utils import *
from queue import Queue
import pymodbus

MAX_16_BIT = 32768
pymodbus.pymodbus_apply_logging_config(level=logging.INFO)

class CustomDataBlock(ModbusSequentialDataBlock):
    def __init__(self, address, values):
        super().__init__(address, values)
        self.data_q = Queue()
        self.args = read_args('./configs/configs.yaml')

    def setValues(self, address, values):
        if address == self.args.first_incoming + 1:
            self.set_timestamp()
        self.print_decoded_vals(address, values)
        super().setValues(address, values)

    def set_timestamp(self):
        timestamp_now = datetime.datetime.now().strftime('%Y-%m-%d | %H:%M:%S')
        unicoded_list = convert_unicode(timestamp_now)
        set_addr = self.args.timestamp_addr + 1
        super().setValues(set_addr, unicoded_list)
        print(f'TimeStamp {timestamp_now} was written to {set_addr}')

    def print_decoded_vals(self, address, values):
        """Decoding done for reading float values"""
        print_values = [f for f in get_list_2comp(values, 16)]
        print(f'In address {address} {print_values} were written')


class CoilDataBlock(ModbusSequentialDataBlock):
    def __init__(self, address, values):
        super().__init__(address, values)
        self.data_q = Queue()
        self.args = read_args('./configs/configs.yaml')

    def setValues(self, address, values):
        print(values)
        super().setValues(address, values)

    def set_timestamp(self):
        timestamp_now = datetime.datetime.now().strftime('%Y-%m-%d | %H:%M:%S')
        unicoded_list = convert_unicode(timestamp_now)
        set_addr = self.args.timestamp_addr + 1
        super().setValues(set_addr, unicoded_list)
        print(f'TimeStamp {timestamp_now} was written to {set_addr}')

store = ModbusSlaveContext(
    di=ModbusSequentialDataBlock(0, [0] * 10000),
    co=CoilDataBlock(0, [0] * 10000),
    hr=CustomDataBlock(0, [MAX_16_BIT - 1] * 10000),
    ir=ModbusSequentialDataBlock(0, [0] * 10000))

context = ModbusServerContext(slaves=store, single=True)
server = StartSerialServer(port="COM3", baudrate=19200, stop_bits=1, bytesize=8, context=context)
