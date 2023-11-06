import asyncio
import random

import pymodbus
from pyModbusTCP.utils import encode_ieee, decode_ieee, \
    long_list_to_word, word_list_to_long
from pymodbus.client import AsyncModbusSerialClient
from pymodbus.exceptions import ModbusException

from pymodbus.transaction import (
    #    ModbusAsciiFramer,
    #    ModbusBinaryFramer,
    ModbusRtuFramer,
    ModbusSocketFramer,
    ModbusTlsFramer,
)


from utils import read_args
pymodbus.pymodbus_apply_logging_config()


class FloatModbusClient:
    """A ModbusClient class with float support."""

    def __init__(self, **kwargs):
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

    async def write_float(self, address, floats_list):
        """Write float(s) with write multiple registers."""
        b32_l = [encode_ieee(f) for f in floats_list]
        b16_l = long_list_to_word(b32_l)
        await self.client.write_registers(address, b16_l, slave=1)

    async def write_pack(self, args):
        rand_num = random.randint(1, 100)
        for category, address in args.reg_addr.items():
            await self.write_float(address, [rand_num])
            print(f'Successfully wrote {rand_num} to {address}')

        # rand_bit = random.randint(0,1)
        # for sensor, coil_address in args.coil_addr.items():
        #     await self.protocol.write_single_coil(coil_address, rand_bit)
        #     print(f'Successfully wrote {rand_bit} to {coil_address}')


async def run_helper():
    args = read_args('./configs/configs.yaml')
    clientWrapper = FloatModbusClient(port="COM1", baudrate=9600, stopbits=1, parity="N", framer=ModbusRtuFramer)
    await clientWrapper.client.connect()
    if clientWrapper.client.connected:
        print("Client is connected")
    try:
        while True:
            await clientWrapper.write_pack(args)
            await asyncio.sleep(1)

            # float_l = await clientWrapper.read_float(200, 1)
            # print("Printing values: ", float_l)

            await asyncio.sleep(1)
    except Exception as e:
        print(e)
    finally:
        clientWrapper.client.close()


if __name__ == "__main__":
    asyncio.run(run_helper())
