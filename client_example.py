import datetime
import logging

from pymodbus.client import (
    ModbusSerialClient,
)
from pymodbus.payload import BinaryPayloadDecoder

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)

client = ModbusSerialClient(
    port='COM3',  # serial port
    # Common optional paramers:
    #    framer=ModbusRtuFramer,
    timeout=1,
    #    retries=3,
    #    retry_on_empty=False,
    #    close_comm_on_error=False,.
    #    strict=True,
    # Serial setup parameters
    baudrate=19200,
    #    bytesize=8,
    #    parity="N",
    #    stopbits=1,
    #    handle_local_echo=False,
)

client.connect()

while (True):
    start_time = datetime.datetime.now()
    coil_start_address = 0
    num_coils = 10

    try:
        res = client.read_coils(coil_start_address, num_coils, slave=1)
        decoder = BinaryPayloadDecoder.fromRegisters(res.registers)
        first_reading = decoder.decode_bits()
        print(f'coil, start {coil_start_address} >>>>>>>>>>>>', first_reading, res.bits)
        coil_start_address += 10
        # time.sleep(0.5)

    except Exception as e:
        print('eee')

    reg_start_address = 0
    num_regs = 0
    try:
        regs_1 = client.read_holding_registers(reg_start_address, num_regs, slave=1)
        print("Register values >>>>>>>>>> ", regs_1.registers)

    except Exception as e:
        print(e)

    end = datetime.datetime.now()

    print("Time TAKEN : ", end, start_time)
