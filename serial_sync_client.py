import datetime
import logging

from pyModbusTCP.utils import decode_ieee, \
    word_list_to_long, get_list_2comp
from pymodbus.client import (
    ModbusSerialClient,
)
from pymodbus.payload import BinaryPayloadDecoder

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)

client = ModbusSerialClient(
    port='COM3',
    timeout=1,
    baudrate=19200
)

client.connect()

while (True):
    start_time = datetime.datetime.now()
    start = 100
    i = 0
    while i < 2:
        try:
            res = client.read_coils(start, 83, slave=1)
            decoder = BinaryPayloadDecoder.fromRegisters(res.registers)
            first_reading = decoder.decode_bits()
            print(f'coil, try number {i} >>>>>>>>>>>>', first_reading, res.bits)
            if len(res.bits) <= 5:
                i -= 1
                continue

        except Exception as e:
            print(f'!!! eeeeee digital, failed try {i}')

        finally:
            i += 1

    regs_cnt = 0
    j = 0
    while j < 2:
        try:
            regs_1 = client.read_holding_registers(301, 89, slave=1)
            if regs_1.registers:
                print(f"Register values 1, try number {j} : ",
                      [f for f in get_list_2comp(regs_1.registers, 16)])

            if len(regs_1.registers) <= 5:
                j -= 1
                continue

        except Exception as e:
            print(f"!!! eeee analog 1, failed try {j}")
        finally:
            j += 1

    end = datetime.datetime.now()
    print("************** Time TAKEN : ", ((end - start_time)))

"""
WARNING:pymodbus.logging:Cleanup recv buffer before send: 0x1 0x1 0x0 0x21 0x90 appeared
"""
# client.write_coil(0, True, slave=1)
# client.write_register(40001, 10, slave=1)
# rr = client.read_coils(0, 1, slave=1)
# print(rr.bits)


"""
print(client.connected)
res1 = client.read_coils(11, 1, slave=1)
#assert not res1.isError()
print(res1)
print(res1.bits)

builder = BinaryPayloadBuilder()
builder.add_32bit_float(75.87)
payload = builder.build()
result  = client.write_registers(40200, payload, skip_encode=True)
"""

"""
while(True):
    try:
        res = client.read_holding_registers(1, 20, slave=1)
        decoder = BinaryPayloadDecoder.fromRegisters(res.registers, byteorder=Endian.BIG, wordorder=Endian.BIG)
        first_reading = decoder.decode_32bit_float()
        print(first_reading)

        time.sleep(1)
    except Exception as e:
        print(res)
"""

# res = client.read_holding_registers(40200, 2, slave=1)
# print(res.registers)

client.close()
