#!/usr/bin/env python3

from typing import Any
from typing_extensions import Self
import serial
import time
import logging

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s : %(module)s : %(funcName)s : %(message)s')

S_CHAR = b'S'
P_CHAR = b'P'
R_CHAR = b'R' 
W_CHAR = b'W'
I_CHAR = b'I'
O_CHAR = b'O'
Z_CHAR = b'Z'

BRG0      = 0x00
BRG1      = 0x01
PORTCONF1 = 0x02
PORTCONF2 = 0x03
IOSTATE   = 0x04
RESERVED  = 0x05
I2CADR    = 0x06
I2CCLKL   = 0x07
I2CCLKH   = 0x08
I2CTO     = 0x09
I2CSTAT   = 0x0A

class SC18IM700:
    """ USBシリアル-I2C変換（SC18IM700）の制御ドライバ """

    def __init__(self, port: Any) -> None:
        """ インスタンスを初期化する
        """
        self.serial: serial.Serial = serial.Serial(port)
        self.serial.baudrate = 9600
        self.serial.bytesize = serial.EIGHTBITS
        self.serial.parity = serial.PARITY_NONE
        self.serial.stopbits = serial.STOPBITS_ONE
        self.serial.timeout = 0.5
        if self.serial.is_open:
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()

    def open(self) -> None:
        """ シリアルポートを開く
        """
        if not self.serial.is_open:
            self.serial.open()
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()

    def close(self) -> None:
        """ シリアルポートを閉じる
        """
        if self.serial.is_open:
            self.serial.close()

    def __enter__(self) -> Self:
        self.open()
        return self

    def __exit__(self, *args, **kwargs) -> None:
        self.close()

    @classmethod
    def bytes_to_str(cls, data: bytes) -> str:
        """ バイト列の文字列表現を返す
        """
        return ''.join(r'\x{:02X}'.format(d) for d in data)

    def read(self, size: int = 1) -> bytes:
        """ シリアルポートからデータを読み込む
        """
        data = self.serial.read(size)
        if len(data) < size:
            raise RuntimeError
        return data

    def write(self, data: bytes) -> None:
        """ シリアルポートへデータを書き込む
        """
        self.serial.write(data)

    @classmethod
    def i2c_read_addr(cls, i2c_addr: int) -> int:
        """ I2C読み込みアドレスを返す
        """
        if (i2c_addr < 0x00) or (0x7F < i2c_addr):
            raise ValueError
        return int((i2c_addr << 1) | 0x01)

    @classmethod
    def i2c_write_addr(cls, i2c_addr: int) -> int:
        """ I2C書き込みアドレスを返す
        """
        if (i2c_addr < 0x00) or (0x7F  < i2c_addr):
            raise ValueError
        return int((i2c_addr << 1) & 0xFE)

    def read_i2c(self, i2c_addr: int, size: int) -> bytes:
        """ I2Cバスからデータを読み込む
        """
        i2c_read_addr =self.i2c_read_addr(i2c_addr)
        if (size < 0x00) or (0xFF < size):
            raise ValueError
        payload = bytes([i2c_read_addr, size])
        tx_data = S_CHAR + payload + P_CHAR
        self.write(tx_data)
        logging.debug('%s', self.bytes_to_str(tx_data))
        time.sleep(10/1000)
        rx_data = self.read(size)
        logging.debug('%s', self.bytes_to_str(rx_data))
        return rx_data

    def write_i2c(self, i2c_addr: int, data: bytes) -> None:
        """ I2Cバスへデータを書き込む
        """
        i2c_write_addr = self.i2c_write_addr(i2c_addr)
        size = len(data)
        if (size < 0x00) or (0xFF < size):
            raise ValueError
        payload = bytes([i2c_write_addr, size]) + bytes(data)
        tx_data = S_CHAR + payload + P_CHAR
        self.write(tx_data)
        logging.debug('%s', self.bytes_to_str(tx_data))

    def read_reg(self, reg_addr: bytes) -> None:
        """ 内部レジスタから値を読み込む
        """
        size = len(reg_addr)
        if (size < 0x00) or (0xFF < size):
            raise ValueError
        payload = bytes(reg_addr)
        tx_data = R_CHAR + payload + P_CHAR
        self.write(tx_data)
        logging.debug('%s', self.bytes_to_str(tx_data))
        time.sleep(10/1000)
        rx_data = self.read(size)
        logging.debug('%s', self.bytes_to_str(rx_data))
        return rx_data

    def write_reg(self, reg_addr: bytes, data: bytes) -> None:
        """ 内部レジスタへ値を書き込む
        """
        payload = b''.join(bytes([r, d]) for r, d in zip(reg_addr, data))
        tx_data = W_CHAR + payload + P_CHAR
        self.write(tx_data)
        logging.debug('%s', self.bytes_to_str(tx_data))

    def read_gpio(self) -> bytes:
        """ GPIOから値を読み込む
        """
        tx_data = I_CHAR + P_CHAR
        self.write(tx_data)
        logging.debug('%s', self.bytes_to_str(tx_data))
        time.sleep(10/1000)
        rx_data = self.read()
        logging.debug('%s', self.bytes_to_str(rx_data))
        return rx_data

    def write_gpio(self, data: bytes) -> None:
        """ GPIOへ値を書き込む
        """
        if len(data) != 1:
            raise ValueError
        payload = data
        tx_data = O_CHAR + payload + P_CHAR
        self.write(tx_data)
        logging.debug('%s', self.bytes_to_str(tx_data))

    @property
    def baudrate(self) -> int:
        """ シリアルポートのボーレートを返す
        """
        reg_addr = bytes([BRG0, BRG1])
        rdata = self.read_reg(reg_addr)
        brg = int.from_bytes(rdata, byteorder='little')
        value = int(7.3728e6 / (16 + brg))
        return value

    def change_baudrate(self, value: int) -> None:
        """ シリアルポートのボーレートを変更する
        """
        reg_addr = bytes([BRG0, BRG1])
        brg = int((7.3728e6 / value) - 16)
        wdata = brg.to_bytes(len(reg_addr), byteorder='little')
        self.write_reg(reg_addr, wdata)
        time.sleep(1)
        self.serial.baudrate = value

    def get_port_conf(self, port: int) -> int:
        """ GPIOポートの機能を返す
        """
        if (port < 0) or (7 < port):
            raise ValueError
        reg_addr = bytes([PORTCONF1, PORTCONF2])
        rdata = self.read_reg(reg_addr)
        port_conf = int.from_bytes(rdata, byteorder='little')
        shift = port * 2
        mask = 0b11 << shift
        value = int((port_conf & mask) >> shift)
        return value

    def set_port_conf(self, port: int, value: int) -> None:
        """ GPIOポートの機能を設定する
        """
        if (port < 0) or (7 < port):
            raise ValueError
        if (value < 0) or (3 < value):
            raise ValueError
        reg_addr = bytes([PORTCONF1, PORTCONF2])
        rdata = self.read_reg(reg_addr)
        port_conf = int.from_bytes(rdata, byteorder='little')
        shift = port * 2
        mask = 0b11 << shift
        port_conf = int((port_conf & ~mask) | (value << shift))
        wdata = port_conf.to_bytes(len(reg_addr), byteorder='little')
        self.write_reg(reg_addr, wdata)

    def port_in(self, port: int) -> bool:
        """ GPIOポートから値を入力する
        """
        if (port < 0) or (7 < port):
            raise ValueError
        rdata = self.read_gpio()
        io_state = int.from_bytes(rdata, byteorder='little')
        shift = port * 1
        mask = 0b1 << shift
        value = bool((io_state & mask) >> shift)
        return value

    def port_out(self, port: int, value: bool) -> None:
        """ GPIOポートへ値を出力する
        """
        if (port < 0) or (7 < port):
            raise ValueError
        rdata = self.read_gpio()
        io_state = int.from_bytes(rdata, byteorder='little')
        shift = port * 1
        mask = 0b1 << shift
        io_state = int((io_state & ~mask) | (int(value) << shift))
        wdata = io_state.to_bytes(1, byteorder='little')
        self.write_gpio(wdata)

    def get_i2c_master_addr(self) -> int:
        """ デバイスのI2Cアドレスを返す
        """
        reg_addr = bytes([I2CADR])
        rdata = self.read_reg(reg_addr)
        i2c_addr = int.from_bytes(rdata, byteorder='little')
        value = int((i2c_addr >> 1) & 0x7F)
        return value

    def set_i2c_master_addr(self, value: int) -> None:
        """ デバイスのI2Cアドレスを設定する
        """
        if (value < 0x00) or (0x7F < value):
            raise ValueError
        reg_addr = bytes([I2CADR])
        i2c_addr = int((value << 1) & 0xFE)
        wdata = i2c_addr.to_bytes(1, byteorder='little')
        self.write_reg(reg_addr, wdata)

    def get_i2c_status(self) -> int:
        """ I2Cステータスを返す
        """
        reg_addr = bytes([I2CSTAT])
        rdata = self.read_reg(reg_addr)
        value = int.from_bytes(rdata, byteorder='little')
        return value

if __name__ == '__main__':
    pass
