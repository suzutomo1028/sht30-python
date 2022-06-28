#!/usr/bin/env python3

import sys, os
sys.path.append(os.pardir)
from sc18im700 import SC18IM700
import time
import logging

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s : %(module)s : %(funcName)s : %(message)s')

SHT30_I2C_ADDR = 0x44

SOFT_RESET          = [0x30, 0xA2]
HEATER_ENABLE       = [0x30, 0x6D]
HEATER_DISABLE      = [0x30, 0x66]
READ_STATUS         = [0xF3, 0x2D]
CLEAR_STATUS        = [0x30, 0x41]
SINGLESHOT_MEASURE  = [0x2C, 0x06]
PERIODIC_MEASURE    = [0x21, 0x30]
READ_MEASURED_VALUE = [0x0E, 0x00]
STOP_MEASURE        = [0x30, 0x93]

class SHT30:
    """ 温湿度センサー（SHT30）の制御ドライバ """

    def __init__(self, sc18: SC18IM700) -> None:
        """ インスタンスを初期化する
        """
        self.sc18: SC18IM700 = sc18

    def begin(self) -> None:
        """ デバイスを開始する
        """
        self.soft_reset()
        self.heater_disable()
        self.clear_status()
        if self.is_alerting:
            raise RuntimeError

    def soft_reset(self) -> None:
        """ デバイスをソフトリセットする
        """
        wdata = bytes(SOFT_RESET)
        self.sc18.write_i2c(SHT30_I2C_ADDR, wdata)
        time.sleep(1)

    def heater_enable(self) -> None:
        """ 内臓ヒーターを稼働する
        """
        wdata = bytes(HEATER_ENABLE)
        self.sc18.write_i2c(SHT30_I2C_ADDR, wdata)
        time.sleep(10/1000)

    def heater_disable(self) -> None:
        """ 内臓ヒーターを停止する
        """
        wdata = bytes(HEATER_DISABLE)
        self.sc18.write_i2c(SHT30_I2C_ADDR, wdata)
        time.sleep(10/1000)

    def read_status(self) -> int:
        """ ステータスを読み込む
        """
        wdata = bytes(READ_STATUS)
        self.sc18.write_i2c(SHT30_I2C_ADDR, wdata)
        time.sleep(10/1000)
        rdata = self.sc18.read_i2c(SHT30_I2C_ADDR, size=3)
        crc = self.crc8(rdata[0:2])
        if crc != rdata[2]:
            raise RuntimeError
        value = int.from_bytes(rdata[0:2], byteorder='big')
        return value

    def clear_status(self) -> None:
        """ ステータスをクリアする
        """
        wdata = bytes(CLEAR_STATUS)
        self.sc18.write_i2c(SHT30_I2C_ADDR, wdata)
        time.sleep(10/1000)

    @property
    def is_alerting(self) -> bool:
        """ アラートが発信中のとき True を返す
        """
        status = self.read_status()
        return bool(status & 0x8000)

    @property
    def heater_enabled(self) -> bool:
        """ 内臓ヒーターが稼働中のとき True を返す
        """
        status = self.read_status()
        return bool(status & 0x2000)

    @property
    def is_humi_alerting(self) -> bool:
        """ 湿度アラームが発信中にとき True を返す
        """
        status = self.read_status()
        return bool(status & 0x0800)

    @property
    def is_temp_alerting(self) -> bool:
        """ 温度アラームが発信中のとき True を返す
        """
        status = self.read_status()
        return bool(status & 0x0400)

    @property
    def is_reset_detected(self) -> bool:
        """ リセット履歴があるとき True を返す
        """
        status = self.read_status()
        return bool(status & 0x0010)

    @property
    def is_command_failed(self) -> bool:
        """ 最後に受信したコマンドがエラーのとき True を返す
        """
        status = self.read_status()
        return bool(status & 0x0002)

    @property
    def is_write_crc_error(self) -> bool:
        """ 最後に受信した電文のCRCが不一致のとき True を返す
        """
        status = self.read_status()
        return bool(status & 0x0001)

    def singleshot_measure(self) -> tuple[int, int]:
        """ 温度と湿度を単発測定する
        """
        wdata = bytes(SINGLESHOT_MEASURE)
        self.sc18.write_i2c(SHT30_I2C_ADDR, wdata)
        time.sleep(30/1000)
        rdata = self.sc18.read_i2c(SHT30_I2C_ADDR, size=6)
        crc_temp = self.crc8(rdata[0:2])
        crc_humi = self.crc8(rdata[3:5])
        if (crc_temp != rdata[2]) or (crc_humi != rdata[5]):
            raise RuntimeError
        raw_temp = int.from_bytes(rdata[0:2], byteorder='big')
        raw_humi = int.from_bytes(rdata[3:5], byteorder='big')
        return (raw_temp, raw_humi)

    def temperature_C(self, raw_temp: int) -> float:
        """ 摂氏温度を返す
        """
        return float(-45 + 175 * (raw_temp / (2**16 - 1)))

    def temperature_F(self, raw_temp: int) -> float:
        """ 華氏温度を返す
        """
        return float(-49 + 315 * (raw_temp / (2**16 - 1)))

    def relative_humidity(self, raw_humi: int) -> float:
        """ 相対湿度を返す
        """
        return float(100 * (raw_humi / (2**16 - 1)))

    def crc8(self, data: bytes) ->  int:
        """ CRCを返す
        """
        POLYNOMIAL = 0x31
        crc = 0xFF
        for d in data:
            crc ^= d
            for _ in range(8):
                if crc & 0x80:
                    crc <<= 1
                    crc ^= POLYNOMIAL
                else:
                    crc <<= 1
        return int(crc & 0xFF)

if __name__ == '__main__':
    pass
