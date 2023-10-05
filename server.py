import argparse
import datetime
import logging
from queue import Queue

"""
ModBus is serial communication protocol. ModBusTCP is TCP/IP communication protocol (Ethernet based). 
"""

from pyModbusTCP.utils import *
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusServerContext, ModbusSlaveContext
from pymodbus.server import StartTcpServer

# Constants
from utils import read_args, convert_unicode

MAX_16_BIT = 32768

# init logging
logging.basicConfig()
# parse args
parser = argparse.ArgumentParser()
parser.add_argument('-H', '--host', type=str, default='localhost', help='Host (default: localhost)')
parser.add_argument('-p', '--port', type=int, default=502, help='TCP port (default: 502)')
parser.add_argument('-d', '--debug', action='store_true', help='set debug mode')
args = parser.parse_args()

if args.debug:
    logging.getLogger('pyModbusTCP.server1').setLevel(logging.DEBUG)


"""
ModbusSequentialDataBlock is a class that can be used to store and access different types of data, such as coils, discrete inputs, holding registers, 
and input registers. The address parameter specifies the starting address of the block, and the values parameter specifies the initial values of the block.
"""
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
        # if address == self.args.bitwise_reg + 1:
        #     print_values = values[0]
        # else:
        #     pass
        print_values = [decode_ieee(f) for f in word_list_to_long(values)]
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


"""
Slave Context refers to a representation of Modbus slave device within a Modbus server.
It encapsulates the data processing and behaviour for specific slave device, allowing server to handle requests and responses.
Addresses,data registers, handler methods and etc. 
"""

store = ModbusSlaveContext(
    di=ModbusSequentialDataBlock(0, [0] * 10000),
    co=CoilDataBlock(0, [0] * 10000),
    hr=CustomDataBlock(0, [MAX_16_BIT - 1] * 10000),
    ir=ModbusSequentialDataBlock(0, [0] * 10000))

context = ModbusServerContext(slaves=store, single=True)

"""
In the pyModbus protocol, the client is typically considered the master, and the server is considered the slave. 
The client (master) initiates requests to read from or write to the server (slave), and the server responds to these requests.
"""
server1 = StartTcpServer(context=context, address=("192.168.0.8", 502))
print('Starting server on ports 502')
