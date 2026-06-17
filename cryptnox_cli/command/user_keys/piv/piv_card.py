# -*- coding: utf-8 -*-
"""
Module for handling operations related to PIV.
"""
import time
from contextlib import ContextDecorator
from typing import (
    List,
    Tuple,
    Union
)

from smartcard.CardConnection import CardConnection
from smartcard.Exceptions import CardConnectionException
from smartcard.System import readers
from smartcard.util import toBytes, toHexString


class PIVBaseException(Exception):
    """
    Base exception for module from which all others are inherited
    """


class PIVCardConnectionException(PIVBaseException):
    """
    There was an issue in connecting to PIV
    """


class PIVCardException(PIVBaseException):
    """
    The card status code indicates and issue that the module doesn't handle
    """

    def __init__(self, sw_byte1, sw_byte2):
        self.sw_byte1 = sw_byte1
        self.sw_byte2 = sw_byte2
        self.sw_code = (sw_byte1 << 8) | sw_byte2
        self.message = "Error status : 0x%02X%02X" % (sw_byte1, sw_byte2)
        super().__init__(self.message)


class DataException(PIVBaseException):
    """
    There was in issue in receiving data from the PIV
    """


class NotFoundException(PIVBaseException):
    """
    PIV wasn't found
    """


class PinException(PIVBaseException):
    """
    Wrong PIN code was given to the PIV.
    retries_left contains the number of retries that are left for the PIV before locked.
    """

    def __init__(self, retries_left: int):
        self.retries_left = retries_left
        if self.retries_left >= 2:
            self.message = f"Wrong PIN. {self.retries_left} tries left"
        else:
            self.message = f"Wrong PIN. {self.retries_left} try left"
        super().__init__(self.message)


def decode_dol(data: List[int], level: int = 0):
    """
    Decode ASN1 BER/DER Data Objects into a Python object

    :param List[int] data:
    :param int level:
    :return:
    """
    dol_out = {}
    idx = 0
    len_all_data = len(data)

    while idx < len_all_data:
        tag, idx, data_list = decode_do(data, idx)

        if (tag < 256 and tag & 32) or (tag >= 256 and tag & (32 << 8)):
            dol_out[f"{tag:02X}"] = decode_dol(data_list, level + 1)
        else:
            dol_out[f"{tag:02X}"] = bytes(data_list)

    return dol_out


def decode_do(data: List[int], start_index: int) -> Tuple[int, int, List[int]]:
    """
    Basic ASN1 BER/DER decoder for a DO

    :param List[int] data: Data to decode
    :param int start_index: Index where the decoding should start

    :return: Decoded data
    """
    i = start_index
    if data[i] & 31 == 31:
        # Tag has 2 bytes
        tag = data[i] * 256 + data[i + 1]
        i += 2
    else:
        # tag is 1 byte
        tag = data[i]
        i += 1
    if data[i] & 128 > 0:
        # composed len
        len_len = data[i] - 128
        len_data = 0
        while len_len:
            len_data *= 256
            i += 1
            len_data += data[i]
            len_len -= 1
        i += 1
    else:
        # simple len
        len_data = data[i]
        i += 1
    data_read = data[i:i + len_data]

    return tag, i + len_data, data_read


class PIVcard(ContextDecorator):
    """
    Class for handling PIV
    """
    APPLET_ID = toBytes("A000000308000010000100")

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.connection = None

    def __enter__(self):
        found_readers = list(filter(lambda x: str(x).startswith("Yubico"), readers()))
        try:
            piv = found_readers[0]
        except IndexError as error:
            raise NotFoundException("PIV not found") from error

        self.connection = piv.createConnection()
        try:
            self.connection.connect(CardConnection.T1_protocol)
        except CardConnectionException as error:
            raise PIVCardConnectionException("Error in connecting to PIV") from error

        self._select()

        return self

    def __exit__(self, exc_type, exc, exc_tb):
        if self.connection:
            self.connection.disconnect()
            del self.connection

    def generate_asymmetric_key(self, key: int, algorithm: int):
        """
        Generate asymmetric key in key location using the algorithm

        :param int key:
        :param int algorithm:
        :return:
        """
        apdu_command = [0x00, 0x47, 0x00, key]
        data = [0xAC, 0x06, 0x80, 0x01, algorithm, 0xAB, 0x01, 0x02]

        gen_resp = self._send_command(apdu_command, data)

        if gen_resp[:2] != [0x7F, 0x49] or len(gen_resp) != gen_resp[2] + 3:
            raise DataException("Bad data received from Generate Asymmetric command")

        return decode_dol(gen_resp[3:])

    def get_data(self, file_tlv_hex: str) -> bytes:
        """
        Get data on location from the PIV

        :param str file_tlv_hex: HEX code of location in PIV from where to get the information

        :return: Requested information
        :rtype: bytes
        """
        address_length = len(file_tlv_hex) // 2
        data_hex = f"5C{'%02X' % address_length}" + file_tlv_hex

        if self.debug:
            print(f"Read Data {data_hex} in 0x{file_tlv_hex}")

        apdu_command = [0x00, 0xCB, 0x3F, 0xFF]
        data = bytes.fromhex(data_hex)
        response = self._send_command(apdu_command, data)

        if address_length == 3:
            if response[0] != 0x53:
                raise DataException("Bad data received from Get Data command")
            return decode_dol(response)["53"]

        if address_length == 1 and response[0] != int(file_tlv_hex, 16):
            raise DataException("Bad data received from Get Data command")

        return decode_dol(response)[file_tlv_hex]

    def is_locked(self, pin_bank: int) -> bool:
        """
        Check if the PIV is open for PIN verification

        This can be used to check if the PIV is locked before asking the user for PIN

        :param int pin_bank: The PIN bank to check
        :return: Whether the PIV is locked for pin_bank
        :rtype: bool
        """
        try:
            self.verify_pin(pin_bank, "")
        except PinException:
            # Empty PIN rejected as expected; card is not locked
            pass
        except PIVCardException as error:
            if error.sw_code == 0x6983:
                return True
            raise

        return False

    def sign(self, key: int, algorithm: int, data: bytes) -> bytes:
        """
        Sign the given data in the PIV use key on location key and using the algorithm
        :param int key: Desired location to use
        :param int algorithm: Algorithm to use
        :param bytes data: Data to sign

        :return: Signature from the PIV
        :rtype: bytes
        """

        data = [0x82, 0x00, 0x81, len(data), *data]

        result = self._send_command([0x00, 0x87, algorithm, key], [0x7C, len(data), *data])
        decoded = decode_dol(result)

        return decoded["7C"]["82"]

    def verify_pin(self, pin_bank: int, pin_string: str) -> None:
        """
        Verify PIN code in PIN bank

        :param int pin_bank: PIN bank to open
        :param str pin_string: PIN code to use to open the PIV
        """
        if pin_string:
            pin_string = pin_string.encode("ascii")
            pin_string += bytes.fromhex("FF") * (8 - len(pin_string))
            self._send_command([0, 0x20, 0, pin_bank], pin_string)
        else:
            self._send_command([0, 0x20, 0, pin_bank], b"")

    def _select(self):
        apdu_select = [0x00, 0xA4, 0x04, 0x00, len(PIVcard.APPLET_ID)] + PIVcard.APPLET_ID
        self._send_apdu(apdu_select)
        time.sleep(0.25)

    def _send_apdu(self, apdu: List[int]) -> Tuple[List[int], int, int]:
        t_env = 0
        if self.debug:
            print(f" Sending 0x{apdu[1]:X} command with {(len(apdu) - 5)} bytes data")
            print(f"-> {toHexString(apdu)}")
            t_env = time.time()

        data, sw_byte1, sw_byte2 = self.connection.transmit(apdu)

        if self.debug:
            t_ans = (time.time() - t_env) * 1000
            print(" Received %i bytes data : SW 0x%02X%02X - duration: %.1f ms" %
                  (len(data), sw_byte1, sw_byte2, t_ans))
            if len(data) > 0:
                print(f"<- {toHexString(data)}")

        return data, sw_byte1, sw_byte2

    def _send_command(self, apdu: List[int], data: Union[List[int], bytes]) -> List[int]:
        t_env = 0
        data_block_size = 247
        current_block = 0

        data_length = len(data)
        full_data = bytes(data) if isinstance(data, list) else data

        while data_length > data_block_size:
            data_apdu = full_data[current_block:current_block + data_block_size]
            apdu_command = apdu + [len(data_apdu)] + toBytes(data_apdu.hex())
            apdu_command[0] |= 0x10
            self._send_apdu(apdu_command)
            current_block += data_block_size
            data_length -= data_block_size

        data_apdu = full_data[current_block:]
        apdu_command = apdu + [len(data_apdu)] + toBytes(data_apdu.hex())
        received, sw_byte1, sw_byte2 = self._send_apdu(apdu_command)

        while sw_byte1 == 0x61:
            if self.debug:
                t_env = time.time()
            partial, sw_byte1, sw_byte2 = self.connection.transmit([0x00, 0xC0, 0x00, 0x00, 0x00])

            if self.debug:
                t_ans = int((time.time() - t_env) * 10000) / 10.0
                print(" Received remaining %i bytes : 0x%02X%02X - duration: %.1f ms"
                      % (len(partial), sw_byte1, sw_byte2, t_ans))
                print(f"<- {toHexString(partial)}")

            received += partial

        if sw_byte1 == 0x63 and sw_byte2 & 0xF0 == 0xC0:
            raise PinException(sw_byte2 - 0xC0)
        if sw_byte1 != 0x90 or sw_byte2 != 0x00:
            raise PIVCardException(sw_byte1, sw_byte2)

        return received
