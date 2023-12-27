import asyncio
import datetime
import logging
import random

import pymodbus
from pyModbusTCP.utils import encode_ieee, decode_ieee, \
    long_list_to_word, word_list_to_long
from pymodbus.client import AsyncModbusSerialClient
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse
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

    async def read_float(self, address, number=1):
        """Read float(s) with read holding registers."""
        try:
            response = await self.client.read_holding_registers(address, number * 2, slave=1)
            if isinstance(response, ExceptionResponse):
                print("Failed to retrieve data, exception code : ", response.exception_code)
            if response.registers:
                return [decode_ieee(f) for f in word_list_to_long(response.registers)]
        except ModbusException as modbus_exception:
            print("Modbus Exception:", modbus_exception)
        except Exception as excep:
            print("Generic Exception:", excep)

    async def read_holding_coils(self, address, number):
        print("Reading coild")
        # Ask about exception code. Exception code 4?
        try:
            response = await self.client.read_coils(address, number, slave=1)
            if response:
                print(len(response.bits))
                return response.bits
        except ModbusException as modbus_exception:
            print("Modbus Exception:", modbus_exception)
        except Exception as excep:
            print("Generic Exception:", excep)

    async def read_all_registers(self, num_regs=0):
        print("Reading Analog")
        # Maximum number of register that can be read at once is 125.
        if not num_regs:
            for category, address in self.args.reg_addr.items():
                val = await self.read_float(address, 1)
                print("Printing values: ", val)
        else:
            _, start_addr = next(iter(self.args.reg_addr.items()))
            if num_regs > 62:
                values = []
                while num_regs:
                    part_values = await self.read_float(start_addr, num_regs)
                    values += part_values
                    start_addr += (62 * 2)
                    num_regs -= 62
            else:
                values = await self.read_float(start_addr, num_regs)
            print(values)

    async def read_all_coils(self, num_coils=0):
        if not num_coils:
            for category, address in self.args.coil_addr.items():
                val = await self.read_holding_coils(address, 1)
                print("Printing values: ", val)
        else:
            _, start_addr = next(iter(self.args.coil_addr.items()))
            # num_coils = len(self.args.coil_addr)
            values = await self.read_holding_coils(start_addr, num_coils)
            print(values)

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

        rand_bit = random.randint(0, 1)
        for sensor, coil_address in self.args.coil_addr.items():
            await self.client.write_coils(coil_address, [bool(rand_bit)], 1)
            print(f'Successfully wrote {rand_bit} to {coil_address}')


async def run_helper():
    clientWrapper = FloatModbusClient(port="COM3", baudrate=19200, stopbits=1, parity="N", framer=ModbusRtuFramer)
    await clientWrapper.client.connect()
    if clientWrapper.client.connected:
        print("Client is connected")
    try:
        while True:
            start_time = datetime.datetime.now()
            # await clientWrapper.write_pack()
            task1 = clientWrapper.read_all_registers(num_regs=48)
            task2 = clientWrapper.read_all_coils(num_coils=48)
            # task1 = asyncio.create_task(clientWrapper.read_all_registers(num_regs=48))
            # task2 = asyncio.create_task(clientWrapper.read_all_coils(num_coils=48))
            await asyncio.gather(task1,task2)            # await clientWrapper.read_all_registers(num_regs=48)
            # await clientWrapper.read_all_coils(num_coils=48)

            end_time = datetime.datetime.now()
            print("************** Time TAKEN : ", ((end_time - start_time)))

    except Exception as e:
        print(e)
    finally:
        clientWrapper.client.close()


if __name__ == "__main__":
    asyncio.run(run_helper())
