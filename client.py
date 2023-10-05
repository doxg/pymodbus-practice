import pdb
import time

from pyModbusTCP.client import ModbusClient
from pyModbusTCP.utils import encode_ieee, decode_ieee, \
    long_list_to_word, word_list_to_long


def regular_transmission():
    c = ModbusClient(host="localhost", port=502, unit_id=1, auto_open=False)

    if c.write_multiple_registers(10, [44, 55]):
        print("write ok")
    else:
        print("write error")

    regs = c.read_holding_registers(10, 2)
    if regs:
        print(regs)
    else:
        print("read error")


class FloatModbusClient(ModbusClient):
    """A ModbusClient class with float support."""

    def read_float(self, address, number=1):
        """Read float(s) with read holding registers."""
        reg_l = self.read_holding_registers(address, number * 2)
        if reg_l:
            return [decode_ieee(f) for f in word_list_to_long(reg_l)]
        else:
            return None

    def write_float(self, address, floats_list):
        """Write float(s) with write multiple registers."""
        b32_l = [encode_ieee(f) for f in floats_list]
        b16_l = long_list_to_word(b32_l)
        return self.write_multiple_registers(address, b16_l)


# read&write coil -> Coils are 1-bit registers, are used to control discrete outputs, and may be read or written
def read_write_coil():
    c = ModbusClient(host='localhost', port=502, auto_open=True, debug=False)

    while True:
        # read 10 bits (= coils) at address 0, store result in coils list
        c.write_multiple_coils(0, [True, True, True, True])
        coils_l = c.read_coils(0, 10)

        # if success display registers
        if coils_l:
            print('coil ad #0 to 9: %s' % coils_l)
        else:
            print('unable to read coils')

        # sleep 2s before next polling
        time.sleep(2)


def float_transmission():
    client = FloatModbusClient(host='localhost', port=502, auto_open=True, auto_close=True)

    client.write_float(0, [-542, 423.415])
    # read @0 to 9
    float_l = client.read_float(0, 2)
    print(float_l)
    pdb.set_trace()


if __name__ == "__main__":
    # float_transmission()

    client = ModbusClient(host='localhost', port=502, auto_open=True, auto_close=True)

    while True:
        float_l = client.read_holding_registers(0, 30)
        print(float_l)
        time.sleep(0.5)
