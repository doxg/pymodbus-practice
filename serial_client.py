import asyncio
import logging
import random

import pymodbus
from pyModbusTCP.utils import encode_ieee, decode_ieee, \
    long_list_to_word, word_list_to_long
from pymodbus.client import AsyncModbusSerialClient
from pymodbus.exceptions import ModbusException
from pymodbus.transaction import (
    ModbusRtuFramer
)

from utils import read_args

pymodbus.pymodbus_apply_logging_config(level=logging.INFO)


class FloatModbusClient:
    """A ModbusClient class with float support."""

    def __init__(self, **kwargs):
        self.args = read_args('./configs/configs.yaml')
        self.client = AsyncModbusSerialClient(**kwargs)
        # print([method for method in dir(self.client) if callable(getattr(self.client,method))])

    async def read_float(self, address, number=1):
        """Read float(s) with read holding registers."""
        try:
            reg_l = await self.client.read_holding_registers(address, number * 2, slave=1)
            if reg_l.registers:
                return [decode_ieee(f) for f in word_list_to_long(reg_l.registers)]
            else:
                return None

        except ModbusException as modbus_exception:
            print("Modbus Exception:", modbus_exception)
        except Exception as excep:
            print("Generic Exception:", excep)

    async def read_coil(self,address,number):
        try:
            response = await self.client.read_coils(address, number, slave=1)
            if response:
                return response.bits
            else:
                return None

        except ModbusException as modbus_exception:
            print("Modbus Exception:", modbus_exception)
        except Exception as excep:
            print("Generic Exception:", excep)

    async def read_all_registers(self):
        for category, address in self.args.reg_addr.items():
            val = await self.read_float(address, 1)
            print("Printing values: ", val)

    async def read_all_coils(self):
        for category, address in self.args.coil.items():
            val = await self.read_coil(address, 1)
            print("Printing values: ", val)

    async def write_float(self, address, floats_list):
        """Write float(s) with write multiple registers."""
        b32_l = [encode_ieee(f) for f in floats_list]
        b16_l = long_list_to_word(b32_l)
        await self.client.write_registers(address, b16_l, slave=1)


    async def write_pack(self):
        rand_num = random.randint(1, 100)
        for category, address in self.args.reg_addr.items():
            await self.write_float(address, [rand_num])
            print(f'Successfully wrote {rand_num} to {address}')

        rand_bit = random.randint(0,1)
        for sensor, coil_address in self.args.coil_addr.items():
            await self.client.write_coils(coil_address, [bool(rand_bit)], 1)
            print(f'Successfully wrote {rand_bit} to {coil_address}')


async def run_helper():
    clientWrapper = FloatModbusClient(port="COM3", baudrate=9600, stopbits=1, parity="N", framer=ModbusRtuFramer)
    await clientWrapper.client.connect()
    if clientWrapper.client.connected:
        print("Client is connected")
    try:
        while True:
            await clientWrapper.write_pack()
            await asyncio.sleep(1)

            await clientWrapper.read_all_registers()
            await clientWrapper.read_all_coils()

            await asyncio.sleep(1)
    except Exception as e:
        print(e)
    finally:
        clientWrapper.client.close()


if __name__ == "__main__":
    asyncio.run(run_helper())
