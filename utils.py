"""
    This module houses general purpose utility functions and classes

    Copyright (C) 2021  David Worboys (-:alumnus Moyhu Primary School et al.:-)

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# Tell Black to leave this block alone (realm of isort)
# fmt: off
import collections
import dataclasses
import datetime
import getpass
import hashlib
import json
import math
import os
import random
import re
import string
import struct
import sys
import time
import uuid
from base64 import b64decode, b64encode
from collections.abc import MutableMapping
from enum import Enum, IntEnum
from typing import (Any, Generator, Generic, Literal, NamedTuple, Type,
                    TypeVar, Union, cast)

import dateutil.parser as dateparse
import netifaces
from Crypto.Cipher import AES
from PySide6 import QtCore, QtWidgets

# fmt: on

NUMBER = TypeVar("NUMBER", int, float)
TFILE_ERROR = TypeVar("TFILE_ERROR", bound="FILE_ERROR")


class Singleton(type):
    """Singleton metaclass"""

    def __init__(self, name, bases, dic):
        """Initialise the metaclass"""
        self.__single_instance = None
        super().__init__(name, bases, dic)

    def __call__(cls, *args, **kwargs):
        """If the class has a single instance, return it. Otherwise, create a new instance, save it, and return it

        Args:
            cls: the class that is being decorated

        Returns:
            The singleton object
        """
        if cls.__single_instance:
            return cls.__single_instance

        single_obj = cls.__new__(cls)
        single_obj.__init__(*args, **kwargs)
        cls.__single_instance = single_obj

        return single_obj


@dataclasses.dataclass(slots=True)
class Coords:
    """The coordinates class for rectangle objects and some associated functions"""

    top: Generic[NUMBER]
    left: Generic[NUMBER]
    width: Generic[NUMBER]
    height: Generic[NUMBER]

    def __post_init__(self):
        assert (
            isinstance(self.top, (int | float)) and self.top >= 0
        ), f"{self.top=}. Must be float >=0"
        assert (
            isinstance(self.left, (int | float)) and self.left >= 0
        ), f"{self.left=}. Must be float >=0"
        assert (
            isinstance(self.width, (int | float)) and self.width >= 0
        ), f"{self.width=}. Must be float >=0"
        assert (
            isinstance(self.height, (int | float)) and self.height >= 0
        ), f"{self.height=}. Must be float >=0"

    @property
    def area(self) -> NUMBER:
        """Calculates the area of the Coords

        Returns:
            NUMBER : Area in pixels
        """
        return self.width * self.height

    @property
    def perimeter(self) -> NUMBER:
        """Calculates the perimeter length of the Coords

        Returns:
            NUMBER : The perimeter of the Coords in pixels
        """
        return 2 * (self.width + self.height)

    @property
    def diagonal(self) -> NUMBER:
        """Calculates the diagonal length of the Coords

        Returns:
            NUMBER : The diagonal in pixels
        """
        return math.sqrt(math.pow(self.width, 2) + math.pow(self.height, 2))

    def overlaps(self, other_cords: "Coords", overlap_ratio: float = 0.3) -> bool:
        """Determines if another set of Coords overlaps this set of Coords

        Args:
            other_cords (Coords): The other set of coordinates to check for overlap
            overlap_ratio: The ratio to determine overlapping. 0 - No overlap to 1 - Complete overlap

        Returns:
            bool : True if overlaps, False if not
        """
        assert isinstance(other_cords, Coords), f"{other_cords=}. Must be Coords"
        assert (
            isinstance(overlap_ratio, float) and 0 <= overlap_ratio <= 1
        ), f" 0<= {overlap_ratio=} <= 1. Must be float in this range"

        return (
            intersection_over_union(coords_a=self, coords_b=other_cords)
            >= overlap_ratio
        )


# Enumerated Types


# The `DATA_TYPE` class is an enumeration of the data types that are supported by the `DataType` class
class DATA_TYPE(IntEnum):
    BOOL = 1
    DATE = 2
    DATETIME = 3
    FLOAT = 4
    INT = 5
    STR = 6


FILE_ERROR = NamedTuple("FILE_ERROR", [("error_no", int), ("error_message", str)])


# `strEnum` is a class that inherits from `str` and `Enum` and overrides the `__repr__` and `__str__` methods to return
# the `value` of the `Enum` member
class strEnum(str, Enum):
    def __repr__(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    @classmethod
    def list(cls) -> list[str]:
        """
        `list(cls) -> list[str]`

        This is a function that takes a class as an argument and returns a list of strings

        Args:
            cls: The class that the method is being called on.

        Returns:
            A list of strings.
        """

        str_list: list[str] = []

        for list_item in cls:
            str_list.append(list_item.value)

        return str_list  # list(map(lambda c: c.value, cls))


# Helper Functions
def alpha_only(text_string: str = "") -> str:
    """Strips a text string of non-alpha characters
    Args:
        text_string (str): Input text string
    Returns:
        str : A text string containing only alpha characters
    """
    assert isinstance(text_string, str), f"{text_string=}. Must be a string"

    return "".join([char for char in text_string if char.isalpha()])


def Find_Common_Words(word_list: list[str]) -> list[str]:
    """
    Finds the words that occur in all lines of words in the word list.

    Args:
        word_list (list): A list of strings containing lines of words.

    Returns:
        list: A list of strings representing the common words that occur in all lines of words in the word list.

    """
    assert isinstance(word_list, list), f"{word_list=}. Must be a list or str "
    assert all(
        isinstance(word, str) for word in word_list
    ), f"{word_list=}. Must be a list of str"

    common_words = []

    for outer_index, word_line in enumerate(word_list):
        words = re.sub(r"[\W_]+", " ", word_line.lower())
        words = words.split()
        words = set(word for word in words if word.isalpha())

        other_words = set()

        for inner_index, match_word_line in enumerate(word_list):
            if inner_index == outer_index:  # same thing, skip
                continue

            match_words = re.sub(r"[\W_]+", " ", match_word_line.lower())
            match_words = match_words.split()
            match_words = set(word for word in match_words if word.isalpha())
            other_words |= match_words

        common_words += {word for word in words if word in other_words}

    common_words = list(set(common_words))
    common_words.sort()

    return common_words


def Data_Type_Decode(data_type: int, value: str) -> any:  # TODO Remove QT dependence
    """
    Author          : David Worboys
    Date            : 2018/06
    Function Name   : Data_Type_Decode_Int
    Purpose         : Casts a string value to the selected data_type - Ref: Data_Type_Encode
    Arguments       : data_type - integer indicating type(check enumerated data_type), value - string
    Returns         : Value cast as the selected datatype
    """
    assert isinstance(value, str), "value must be a str"
    assert isinstance(
        data_type, (DATA_TYPE, int)
    ), "data_type is enumerated data_type or an int index into data_type"

    match data_type:
        case DATA_TYPE.BOOL:  # bool
            return bool(value in ("True", "T"))
        case DATA_TYPE.DATE:
            locale = QtCore.QLocale()
            date_format: Type[QtCore.QLocale.FormatType] = QtCore.QLocale.ShortFormat  # type: ignore

            return QtCore.QDate.fromString(str(value), locale.dateFormat(date_format))  # type: ignore
        case DATA_TYPE.DATETIME:
            locale = QtCore.QLocale()
            date_format: Type[QtCore.QLocale.FormatType] = QtCore.QLocale.ShortFormat  # type: ignore

            return QtCore.QDateTime.fromString(str(value), locale.dateTimeFormat(date_format))  # type: ignore
        case DATA_TYPE.FLOAT:
            return float(value)
        case DATA_TYPE.INT:
            return int(value)
        case DATA_TYPE.STR:
            return value
        case _:
            raise ValueError(f"Unknown data_type {data_type}")


def Data_Type_Encode(value: any) -> DATA_TYPE:
    """Returns the encoding type for a given value

    Args:
        value (any): The value for which an encoding type is required

    Raises:
        ValueError: Unrecognized Type

    Returns:
        DATA_TYPE: DATA_TYPE int value
    """
    data_type: DATA_TYPE

    if isinstance(value, bool):
        data_type = DATA_TYPE.BOOL
    elif isinstance(value, datetime.date):
        data_type = DATA_TYPE.DATE
    elif isinstance(value, datetime.datetime):
        data_type = DATA_TYPE.DATETIME
    elif isinstance(value, float):
        data_type = DATA_TYPE.FLOAT
    elif isinstance(value, int):
        data_type = DATA_TYPE.INT
    elif isinstance(value, str):
        data_type = DATA_TYPE.STR
    else:
        raise ValueError(f"Unrecognized Type <{value=} - {type(value)=}> ")

    return data_type


def Dict_Remove_Key(target_dict: dict, search_key: Union[str, int]) -> dict:
    """Removes an item from a dictionary.

    Args:
        target_dict (dict):
        search_key (Unon[str,int]):

    Returns:
        dict : Target dict with item removed

    """

    assert isinstance(target_dict, dict), f"{target_dict=}. Must be dict"
    assert isinstance(search_key, (int, str)), f"{search_key=}. Must be str or int"

    if search_key in target_dict:
        target_dict.pop(search_key)
    else:
        for key in target_dict.keys():
            if isinstance(target_dict[key], dict):
                Dict_Remove_Key(target_dict[key], search_key)
            elif isinstance(target_dict[key], list):
                if target_dict[key].count(search_key) > 0:
                    target_dict[key].remove(search_key)

    return target_dict


def Dump_Object(py_object: object):
    """Dumps an object to the console. Used for debugging.

    Args:
        py_object (object): The object to dump
    """
    for attr in dir(py_object):
        if type(attr) == object:
            Dump_Object(py_object)
        else:
            print("obj.%s = %r" % (attr, getattr(py_object, attr)))


def Dump_QtObject(qtObject: QtCore.QObject | QtWidgets.QWidget):
    """Dumps a Qt object to the console. Used for debugging.
    Args:
        qtObject (QtCore.QObject | QtWidgets.QWidget): The object to dump

    """
    assert isinstance(
        qtObject, QtCore.QObject
    ), f"qtobject <{qtObject}> must be of type QObject"

    try:
        parent: QtCore.QObject = qtObject.parentWidget()  # type: ignore

        if parent is not None:
            print("->", qtObject)
            Dump_QtObject(parent)
        else:
            print("-->", qtObject)
    except AttributeError:
        parent: QtWidgets.QWidget = qtObject.parentWidget()  # type: ignore

        try:
            if parent is not None:
                print("--->", qtObject)
                Dump_QtObject(parent)
            else:
                print("---->", qtObject)
        except AttributeError:
            print("---->", qtObject)


def Pack_Rational(
    endian_symbol: Literal[">", "<"],
    rationals: Union[
        list[tuple[int, int]],
        list[list[int]],
        tuple[tuple[int, int], ...],
        tuple[list[int], ...],
    ],
    word_width: int,
    signed: bool = False,
) -> bytes:
    """Packs a list or tuple of nominator/denominator tuple pairs into a byte string

    Args:
        endian_symbol: Big '>' or Little endian '< ' byte string
        rationals:  A list or tuple of nominator,denominator pairs in a tuple or list
        word_width: The bit width of the word
        signed: Signed or unsigned bytes

    Returns: A byte string

    """
    assert isinstance(endian_symbol, str) and endian_symbol in (
        "<",
        ">",
    ), f"{endian_symbol}=. Must be a one char str - < | >"
    assert isinstance(
        rationals, (list, tuple)
    ), f"{rationals=}. Must be a array | list of tuples"
    assert isinstance(word_width, int) and word_width in (
        1,
        2,
        4,
        8,
    ), f"{word_width=}. Must be an int 1 | 2 | 4 | 8"
    assert isinstance(signed, bool), f"{signed=}. Must be bool"

    byte_order = "big" if endian_symbol == ">" else "little"

    out_bytes = b""

    for number_pair in rationals:
        assert (
            isinstance(number_pair, tuple) and len(number_pair) == 2
        ), f"{number_pair=}. Must be a tuple of 2 ints - nominator, denominator"
        assert isinstance(
            number_pair[0], int
        ), f"Nominator {number_pair[0]=} must be an int"
        assert isinstance(
            number_pair[1], int
        ), f"Denominator {number_pair[1]=} must be an int"

        numerator: int = number_pair[0]
        denominator: int = number_pair[1]

        out_bytes += numerator.to_bytes(
            length=word_width, byteorder=cast(Literal, byte_order), signed=signed
        )
        out_bytes += denominator.to_bytes(
            length=word_width, byteorder=cast(Literal, byte_order), signed=signed
        )

    return out_bytes


def Unpack_Rational(
    endian_symbol: Literal[">", "<"],
    data_bytes: bytes,
    word_width: int,
    signed: bool = False,
) -> tuple[tuple[int, int], ...]:
    """Extracts a tuple of rational number pairs from the supplied data_bytes

    Args:
        endian_symbol (Literal['>','<']): Big '>' or Little endian '< ' byte string
        data_bytes (bytes):  The bytes string from which the rational numbers are extracted
        word_width (int):  The bit width of the word
        signed (signed): Signed or unsigned bytes

    Returns: A tuple containing tuples of nominator/denominator pairs

    """
    # print(f"DBG Extract_Rat {endian=} {data_bytes=} {word_width=} {signed=}")
    assert isinstance(endian_symbol, str) and endian_symbol in (
        "<",
        ">",
    ), f"{endian_symbol}=. Must be a one char str - < | >"
    assert isinstance(data_bytes, bytes), f"{data_bytes=}. Must be a byte string"
    assert isinstance(word_width, int) and word_width in (
        1,
        2,
        4,
        8,
    ), f"{word_width=}. Must be an int 1 | 2 | 4 | 8"
    assert isinstance(signed, bool), f"{signed=}. Must be bool"

    decode_format = ""

    if word_width == 1:
        decode_format = endian_symbol + ("b" if signed else "c")
    elif word_width == 2:
        decode_format = endian_symbol + ("h" if signed else "H")
    elif word_width == 4:
        decode_format = endian_symbol + ("l" if signed else "L")
    elif word_width == 8:
        decode_format = endian_symbol + ("q" if signed else "Q")

    lower = 0
    index = 0
    rationals: list[tuple[int, int]] = []

    for upper in range(word_width, len(data_bytes), word_width):
        numerator = struct.unpack_from(decode_format, data_bytes[lower:upper])[0]
        denominator = struct.unpack_from(
            decode_format, data_bytes[upper : upper + word_width]
        )[0]

        # print(
        #    f"DBG {numerator=} {denominator=} {decode_format=} {word_width=} {lower=} {upper=} {data_bytes[lower:upper]=} {data_bytes=}\n "
        # )

        if index % 2 == 0:
            rationals.append((numerator, denominator))
        index += 1
        lower = upper

    # test_bytes = Pack_Rational(endian=endian, rationals=rationals, word_width=word_width, signed=signed)
    # print(f"B DBG RAT { ':-)' if test_bytes == data_bytes else ':-(' } ==========>\n{rationals=}\n{test_bytes}\n{data_bytes}")

    return tuple(rationals)


def flatten(
    dictionary: dict, parent_key: str = "", separator: str = "."
) -> dict[str, any]:
    """
    Turn a nested dictionary into a flattened dictionary

    Args:
        dictionary (dict): The dictionary to flatten
        parent_key (str): The string to prepend to dictionary's keys
        separator (str): The string used to separate flattened keys

    Returns:
        dict: A flattened dictionary
    """
    assert isinstance(dictionary, dict), f"{dictionary=}. Must be dict"
    assert isinstance(parent_key, str), f"{parent_key=}. Must be str"
    assert isinstance(separator, str), f"{separator=}. Must be str"

    items = []
    for key, value in dictionary.items():
        new_key = str(parent_key) + separator + key if parent_key else key
        if isinstance(value, MutableMapping):
            items.extend(flatten(value, new_key, separator).items())
        elif isinstance(value, list):
            for child_key, child_value in enumerate(value):
                items.extend(flatten({str(child_key): child_value}, new_key).items())
        else:
            items.append((new_key, value))
    return dict(items)


def Find_All(search_string: str, pattern: str) -> Generator[int, Any, None]:
    """Find all generator  - gets the positions of the pattern  in the search_string."""
    assert isinstance(search_string, str), f"{search_string=}. Must be str"
    assert isinstance(pattern, str), f"{pattern=}. Must be str"

    pos = search_string.find(pattern)

    while pos != -1:
        yield pos
        pos = search_string.find(pattern, pos + 1)


def Get_File_Hash(file_path: str) -> str:
    """Get the hash of a file."""
    assert (
        isinstance(file_path, str) and file_path.strip() != ""
    ), f"{file_path=}. Must be non-empty str"

    # Check if file exists
    if os.path.isfile(file_path):
        with open(file_path, "rb") as file_handle:
            return hashlib.sha256(file_handle.read()).hexdigest()

    return ""


def Get_Unique_Sysid() -> str:
    """
    Returns a unique system_id - Based on MAC address if all goes well or a fixed random string with the username
    tacked on the end then all mixed-up. Not cryptographically secure but not obvious either.

    Note: Ignores USB interfaces and may not always return the same sys_id if an interface is deactivated

    Returns:
        str : A unique system id based on the MAC address or a random string if MAC address is not available
    """
    sys_id = (
        "jMSYkph66BhuhXRQGz6mHc4d" + getpass.getuser()
    )  # Use random string if no MAC address found

    for interface in netifaces.interfaces():
        address = netifaces.ifaddresses(interface)

        if (
            not interface.startswith("usb")
            and netifaces.AF_LINK in address
            and netifaces.AF_INET in address
        ):  # Grab last valid MAC address for non-usb interface
            mac_address = address[netifaces.AF_LINK][0]["addr"]
            # ip_address = address[netifaces.AF_INET][0]['addr']

            if mac_address != "00:00:00:00:00:00":
                sys_id = mac_address

    sys_list = []
    for index, character in enumerate(sys_id):
        if character != ":":
            number = ord(character) ^ index
            sys_list.append(str(number))

    sys_number = int("".join(sys_list))

    random.seed(sys_number)
    random.shuffle(sys_list)

    return "".join(sys_list)


def Get_Unique_Id() -> str:
    """Generate a random string of characters that is guaranteed to be unique

    Returns:
        str : A random string of 96 characters.
    """
    # Note the 48 random bits replaces the hardware MAC address from uuid1 generation
    unique_str = list(
        f"{uuid.uuid1(random.getrandbits(48) | 0x010000000000)}{uuid.uuid4()}".replace(
            "-", ""
        )
    )
    random.shuffle(unique_str)
    return "".join(unique_str)


def Get_Unique_Int() -> int:
    """Generates a unique integer ID using timestamp and random number.

    Returns:
        int: Unique integer ID.

    """
    timestamp = int(time.time() * 1000)  # Current timestamp in milliseconds
    random_num = random.randint(0, 20000)  # Random number between 0 and 9999

    unique_id = timestamp * 10000 + random_num  # Combine timestamp and random number

    return unique_id


def Is_Complied() -> bool:
    """Returns True if the current python interpreter is complied.

    Returns:
        bool :A boolean value.
    """
    if globals().get("__compiled__", False):
        # print("Nuitka compiled")
        return True
    elif getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # print("Pyinstaller")
        return True  # might need tristate in case of pyinstaller specials
    else:
        # print("Not compiled ")
        return False


def Is_HTMLXML(instring: str) -> bool:
    """Returns True if the string is an HTML or XML document.

    instring (str) : The string to check.

    Returns:
        bool : True if the string is an HTML or XML document. False otherwise.
    """
    if instring.startswith("<!DOCTYPE html") or instring.startswith("<html"):
        return True
    else:
        # Could be a separate function to extract text from XML/HTML
        tags = []
        tag = False
        quote = False
        tag_str = ""
        out_str = ""

        for char in instring:
            if char == "<" and not quote:
                tag = True
            elif char == ">" and not quote:
                tags.append(tag_str)
                tag_str = ""
                tag = False
            elif char in ('"', "'") and tag:
                quote = not quote
            elif not tag:
                out_str = out_str + char
            else:
                tag_str = tag_str + char

        if tags:
            return True

        return False


def Lcm(x: int, y: int) -> int:
    """
    "Returns the smallest number that is evenly divisible by both x and y."

    Args:
        x (int): int
        y (int): int

    Returns:
        int: The lowest common multiple of x and y
    """
    assert isinstance(x, int), f"{x=}. Must be int"
    assert isinstance(y, int), f"{y=}. Must be int"

    for currentPossibleLCM in range(max(x, y), (x * y) + 1):
        if (currentPossibleLCM % x == 0) and (currentPossibleLCM % y == 0):
            return currentPossibleLCM
    return 0


# Uses AES to encrypt and decrypt strings
class Crypt:
    def __init__(self, salt: str = "73cd33917b614eb7"):
        """Crypt has methods that will encode and decode a string using AES

        salt (str): The salt that AES will use to encrypt and decrypt strings (must be 16 chars long)
        """
        assert (
            isinstance(salt, str) and len(salt.strip()) == 16
        ), f"salt <{salt}> must be a non-empty str 16 chars long"

        random.seed(salt)
        str_key_len = len(salt)
        mixer = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=str_key_len * 2)
        )

        temp_key = salt + mixer[str_key_len:]
        temp_key = "".join(
            [
                hex(ord(temp_key[i % len(temp_key)]) ^ ord(mixer[i % (len(mixer))]))[2:]
                for i in range(max(len(temp_key), len(mixer)))
            ]
        )
        str_key_list = list(temp_key)
        random.shuffle(str_key_list)

        salt = ""
        x = 0

        while x < str_key_len:
            y = random.randint(0, str_key_len - 1)
            salt += f"{str_key_list[y]}"
            x += 1

        self.salt = salt.encode("utf8")
        self.enc_dec_method = "utf-8"

    def encrypt(self, str_to_enc: str, str_key: str) -> str:
        """Encrypts a string with the str_key

        str_to_enc (str): String that will be encrypted (non-empty)
        str_key (str): The key to do the encryption (must have only 16,24 or 32 chars)
        return (str) : The encrypted str

        """
        assert (
            isinstance(str_to_enc, str) and str_to_enc.strip() != ""
        ), f"str_to_enc <{str_to_enc}> must be a num-empty string"

        assert isinstance(str_key, str) and (
            len(str_key) % 16 == 0 or len(str_key) % 24 == 0 or len(str_key) % 32 == 0
        ), (
            f"str_key <{str_key}> must be a num-empty string with only  16,24 or 32"
            " characters"
        )

        random.seed(str_key)
        str_key_len = len(str_key)
        mixer = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=str_key_len * 2)
        )

        temp_key = str_key + mixer[str_key_len:]
        temp_key = "".join(
            [
                hex(ord(temp_key[i % len(temp_key)]) ^ ord(mixer[i % (len(mixer))]))[2:]
                for i in range(max(len(temp_key), len(mixer)))
            ]
        )
        str_key_list = list(temp_key)
        random.shuffle(str_key_list)

        str_key = ""
        x = 0

        while x < str_key_len:
            y = random.randint(0, str_key_len - 1)
            str_key += f"{str_key_list[y]}"
            x += 1

        try:
            aes_obj = AES.new(str_key, AES.MODE_CFB, self.salt)  # type: ignore
            hx_enc: bytes = aes_obj.encrypt(str_to_enc.encode("utf8"))
            mret = b64encode(hx_enc).decode(self.enc_dec_method)
            return mret
        except ValueError as value_error:
            if value_error.args[0] == "IV must be 16 bytes long":
                raise ValueError("Encryption Error: SALT must be 16 characters long")
            elif (
                value_error.args[0] == "AES key must be either 16, 24, or 32 bytes long"
            ):
                raise ValueError(
                    f"Encryption Error: Encryption key <{str_key}> must be either 16,"
                    " 24, or 32 characters long"
                )
            else:
                raise ValueError(value_error)

    def decrypt(self, enc_str: str, str_key: str) -> str:
        """Decrypts an encoded string with the str_key.  Must be the same str_key as used in the encode method

        enc_str (str): THen encoded string
        str_key (str): The key to do the encryption (must have only 16,24 or 32 chars)
        return (str): The decrypted string

        """
        assert (
            isinstance(enc_str, str) and enc_str.strip() != ""
        ), f"enc_str <{enc_str}> must be a num-empty string"

        assert isinstance(str_key, str) and (
            len(str_key) % 16 == 0 or len(str_key) % 24 == 0 or len(str_key) % 32 == 0
        ), (
            f"str_key <{str_key}> must be a num-empty string with only  16,24 or 32"
            " characters"
        )

        random.seed(str_key)
        str_key_len = len(str_key)
        mixer = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=str_key_len * 2)
        )

        temp_key = str_key + mixer[str_key_len:]
        temp_key = "".join(
            [
                hex(ord(temp_key[i % len(temp_key)]) ^ ord(mixer[i % (len(mixer))]))[2:]
                for i in range(max(len(temp_key), len(mixer)))
            ]
        )
        str_key_list = list(temp_key)
        random.shuffle(str_key_list)

        str_key = ""
        x = 0

        while x < str_key_len:
            y = random.randint(0, str_key_len - 1)
            str_key += f"{str_key_list[y]}"
            x += 1

        try:
            aes_obj = AES.new(str_key.encode("utf8"), AES.MODE_CFB, self.salt)
            str_tmp: bytes = b64decode(enc_str.encode(self.enc_dec_method))
            str_dec = aes_obj.decrypt(str_tmp)
            mret: str = str_dec.decode(self.enc_dec_method)
            return mret
        except ValueError as value_error:
            if value_error.args[0] == "IV must be 16 bytes long":
                raise ValueError("Decryption Error: SALT must be 16 characters long")
            elif (
                value_error.args[0] == "AES key must be either 16, 24, or 32 bytes long"
            ):
                raise ValueError(
                    "Decryption Error: Encryption key must be either 16, 24, or 32"
                    " characters long"
                )
            else:
                raise ValueError(value_error)


# The File class provides an easy-to-use wrapper around file info/manipulation calls
def country_date_formatmask(country_or_format: str = "") -> tuple[str, str]:
    """Pass in the country code and get the default format and QT mask for the date. Pass in a date format and get
    the QT mask for it.

    Args:
        country_or_format (str): 2 digit iso ISO639-2 country code or a date format string

    Returns:
        tuple(str,str) : country date format if found, otherwise iso date format yyyy-MM-dd and an edit mask for QT

    """
    country_format = {
        "AL": "yyyy-MM-dd",
        "AE": "dd/MM/yyyy",
        "AR": "dd/MM/yyyy",
        "AU": "dd/MM/yyyy",
        "AT": "dd.MM.yyyy",
        "BE": "dd/MM/yyyy",
        "Background": "yyyy-MM-dd",
        "BH": "dd/MM/yyyy",
        "BA": "yyyy-MM-dd",
        "BY": "dd.MM.yyyy",
        "BO": "dd-MM-yyyy",
        "BR": "dd/MM/yyyy",
        "CAF": "yyyy-MM-dd",
        "CA": "dd/MM/yyyy",
        "CH": "dd.MM.yyyy",
        "CL": "dd-MM-yyyy",
        "CN": "yyyy-MM-dd",
        "CO": "dd/MM/yyyy",
        "CR": "dd/MM/yyyy",
        "CY": "dd/MM/yyyy",
        "CZ": "dd.MM.yyyy",
        "DE": "dd.MM.yyyy",
        "DK": "dd-MM-yyyy",
        "DO": "MM/dd/yyyy",
        "DZ": "dd/MM/yyyy",
        "EC": "dd/MM/yyyy",
        "EG": "dd/MM/yyyy",
        "ES": "dd/MM/yyyy",
        "ESC": "dd/MM/yyyy",
        "EE": "dd.MM.yyyy",
        "FI": "dd.M.yyyy",
        "FR": "dd/MM/yyyy",
        "GB": "dd/MM/yyyy",
        "GR": "dd/MM/yyyy",
        "GT": "dd/MM/yyyy",
        "HK": "dd/MM/YYYY",
        "HN": "MM-dd-yyyy",
        "HR": "dd.MM.yyyy",
        "HU": "yyyy.MM.dd",
        "ID": "dd/MM/yyyy",
        "IND": "dd/MM/yyyy",
        "IN": "dd/MM/yyyy",
        "IE": "dd/MM/yyyy",
        "IRQ": "dd/MM/yyyy",
        "IS": "dd.MM.yyyy",
        "IL": "dd/MM/yyyy",
        "IT": "dd/MM/yyyy",
        "JO": "dd/MM/yyyy",
        "JP": "yyyy/MM/dd",
        "KR": "yyyy.MM.dd",
        "KW": "dd/MM/yyyy",
        "LB": "dd/MM/yyyy",
        "LY": "dd/MM/yyyy",
        "LT": "yyyy.MM.dd",
        "LU": "dd/MM/yyyy",
        "LUG": "dd.MM.yyyy",
        "LV": "yyyy.d.M",
        "MA": "dd/MM/yyyy",
        "MX": "dd/MM/yyyy",
        "MK": "dd.NM.yyyy",
        "MT": "dd/MM/yyyy",
        "ME": "dd.MM.yyyy",
        "MY": "dd/MM/yyyy",
        "NI": "MM-dd-yyyy",
        "NL": "dd-MM-yyyy",
        "NO": "dd.MM.yyyy",
        "NZ": "dd/MM/yyyy",
        "OM": "dd/MM/yyyy",
        "PA": "MM/dd/yyyy",
        "PE": "dd/MM/yyyy",
        "PH": "MM/dd/yyyy",
        "PL": "dd.MM.yyyy",
        "PR": "MM-dd-yyyy",
        "PT": "dd-MM-yyyy",
        "PY": "dd/MM/yyyy",
        "QA": "dd/MM/yyyy",
        "RO": "dd.MM.yyyy",
        "RU": "dd.MM.yyyy",
        "SA": "dd/MM/yyyy",
        "CS": "dd.MM.yyyy",
        "SD": "dd/MM/yyyy",
        "SGC": "dd/MM/yyyy",
        "SG": "MM/dd/yyyy",
        "SV": "MM-dd-yyyy",
        "RS": "dd.MM.yyyy",
        "SK": "dd.MM.yyyy",
        "SI": "dd.MM.yyyy",
        "SE": "yyyy-MM-dd",
        "SY": "dd/MM/yyyy",
        "TH": "dd/MM/MMMM",
        "THT": "dd/MM/YYYY",
        "TN": "dd/MM/yyyy",
        "TR": "dd.MM.yyyy",
        "TW": "yyyy/MM/dd",
        "UA": "dd.MM.yyyy",
        "UY": "dd/MM/yyyy",
        "US": "MM/dd/yyyy",
        "VE": "dd/MM/yyyy",
        "VN": "dd/MM/yyyy",
        "YE": "dd/MM/yyyy",
        "ZA": "yyyy/MM/dd",
    }

    assert (
        isinstance(country_or_format, str) and len(country_or_format.strip()) >= 2
    ), f"{country_or_format=}. Must be str and ISO639-2 code or a date mask"

    format = ""

    if country_or_format.upper() in country_format:
        format = country_format[country_or_format.upper()]

    if format.strip() == "" and country_or_format.strip() != "":
        format = country_or_format

    if format.strip() == "":
        format = "yyyy-MM-dd"  # iso date format country_or_format

    if format.find("/") > 0:
        date_sep = "/"
    elif format.find(".") > 0:
        date_sep = "."
    elif format.find("-") > 0:
        date_sep = "-"
    elif format.find(".") > 0:
        date_sep = "."
    else:
        raise AttributeError(f" {format=}. Not a valid date format")

    format_list = format.split(date_sep)

    mask = ""

    for item in format_list:
        if item == "MMM":
            mask += "AAA" + date_sep
        else:
            mask += ("9" * len(item.strip())) + date_sep

    mask = mask[:-1]

    return format, mask


def amper_length(in_str: str) -> int:
    """Returns the length of a string with ampersands in it.  Used in GUI controls the ampersand is an accelerator
    key and needs to be escaped with && - thus need special processing to get the real string length in this use case

    Args:
        in_str (str): The string with ampersands in it

    Returns (int) : The length of the string taking into account the embedded ampersands

    """
    amper_count = collections.Counter(in_str)

    text_len = len(in_str)

    if "&" in amper_count:
        # & is an accelerator key.  && escapes to an & in a string
        if amper_count["&"] % 2 == 0:
            # Double && is & so need to adjust count to reflect
            label_len = text_len - (amper_count["&"] // 2)
        else:
            # Have an accelerator key
            if amper_count["&"] == 1:
                label_len = text_len - 1
            else:
                # One & is accelerator the rest are && escaped to &
                label_len = (text_len - (amper_count["&"] // 2)) - 1
    else:
        label_len = text_len

    return label_len


def space_out_capitalised(in_str: str) -> str:
    """Inserts spaces before capital (A-Z) letters and numbers in a string

    Args:
        in_str (str): String with no spaces between words starting with A-Z or numbers (e.g IDon'tKnow 234becomes
        I Don't 234 Know)

    Returns (str): String with spaces inserted before capitals

    """
    assert isinstance(in_str, str), f"{in_str=}. Must be str!"

    out_str = ""

    for index, char in enumerate(in_str):
        if index > 0:
            if char in string.ascii_uppercase and (
                in_str[index - 1] in string.ascii_lowercase
                or in_str[index - 1] in string.digits
            ):
                out_str += " "
                out_str += char
            else:
                out_str += char
        else:  # Default 1st char to upper case
            out_str += char.upper()

    return out_str


def date_iso_extract(value: str, fuzzy: bool = False, year_first: bool = False) -> str:
    """Attempts to extract a data string in iso format from a string

    Args:
        value (str): input string with date
        fuzzy (bool): Do a fuzzy match
        year_first (bool): Force the year to be considered the first part of the date in the string

    Returns:
        str : Date extracted from the string or the original string if no date found

    """
    try:
        if fuzzy:
            date = cast(
                datetime,
                dateparse.parse(
                    timestr=value, fuzzy_with_tokens=fuzzy, yearfirst=year_first
                ),
            )[0]
        else:
            date = dateparse.parse(
                timestr=value, fuzzy_with_tokens=fuzzy, yearfirst=year_first
            )

        if date is not None:
            value = date.replace(microsecond=0).isoformat()
    except dateparse.ParserError:
        pass

    return value


def is_str_float(num: str) -> bool:
    """Returns True if the string number is a float

    Args:
        num (str): string number to check if a float

    Returns:
        bool: True id number is a float, False if not
    """
    assert (
        isinstance(num, str) and num.strip() != ""
    ), f"{num=}. Must be a non-empty str"

    if "." not in num:
        return False

    return num.replace(".", "").replace("-", "").replace("e", "").isdigit()


def cosine_similarity(data_x: list[float] | str, data_y: list[float] | str) -> float:
    """Calculates the cosine similarity between two vectors

    Args:
        data_x: List of floats or a string delimited by "," containing floats to be used as the x set
        data_y: List of floats or a string delimited by "," containing floats to be used as the y set

    Returns:
        float: The cosine similarity between the two vectors
    """

    if isinstance(data_x, str) and "," in data_x:
        x_set: list[float] = [float(item) for item in data_x.split(",")]
    elif isinstance(data_x, list):
        for num in data_x:
            assert isinstance(num, (int, float)), f"{num=}. Must be int or float"

        x_set = data_x
    else:
        raise RuntimeError(
            f"{data_x=}. Must be list of float or a string of float delimited by ,"
        )

    if isinstance(data_y, str) and "," in data_y:
        y_set: list[float] = [float(item) for item in data_y.split(",")]
    elif isinstance(data_y, list):
        for num in data_y:
            assert isinstance(num, (int, float)), f"{num=}. Must be int or float"
        y_set = data_y
    else:
        raise RuntimeError(
            f"{data_y=}. Must be list of float or a string of float delimited by ,"
        )

    if len(x_set) != len(y_set):  # DBG Remove Before Flight
        raise RuntimeError(
            f"Data sets\n {x_set=} \n {y_set=} \nmust be the same length"
        )

    norm_a = math.sqrt(sum(x * x for x in x_set))
    norm_b = math.sqrt(sum(x * x for x in y_set))

    dot = sum(a * b for a, b in zip(x_set, y_set))

    return dot / (norm_a * norm_b)


def euclidean_dist(data_x: str | list[float], data_y: str | list[float]) -> float:
    """
    Calculates the euclidean distance between two lists of data

    Args:
        data_x: List of floats or a string delimited by "," containing floats to be used as the x set
        data_y: List of floats or a string delimited by "," containing floats to be used as the y set

    Returns:
        float: Euclidean distance between the two lists
    """
    if isinstance(data_x, str) and "," in data_x:
        x_set: list[float] = [float(item) for item in data_x.split(",")]
    elif isinstance(data_x, list):
        for num in data_x:
            assert isinstance(num, (int, float)), f"{num=}. Must be int or float"

        x_set = data_x
    else:
        raise RuntimeError(
            f"{data_x=}. Must be list of float or a string of float delimited by ,"
        )

    if isinstance(data_y, str) and "," in data_y:
        y_set: list[float] = [float(item) for item in data_y.split(",")]
    elif isinstance(data_y, list):
        for num in data_y:
            assert isinstance(num, (int, float)), f"{num=}. Must be int or float"
        y_set = data_y
    else:
        raise RuntimeError(
            f"{data_y=}. Must be list of float or a string of float delimited by ,"
        )

    if len(x_set) != len(y_set):  # DBG Remove Before Flight
        raise RuntimeError(
            f"Data sets\n {x_set=} \n {y_set=} \nmust be the same length"
        )

    return 1 / (1 + math.dist(x_set, y_set))


def intersection_over_union(coords_a: Coords, coords_b: Coords) -> float:
    """Calculates the intersection over union ratio (modified Jacquard index) for two sets of bounding_box
    co-ordinates.  The returned ratio ranges between 0 - no intersection - and 1 - complete intersection.

    Args:
        coords_a (Coords): Bounding Box for co-ordinate set A
        coords_b (Coords): Bounding Box for co-ordinate set B

    Returns:
        float: A ratio between 0 and 1 indicating the intersection union of coords_a and coords_b.


    """
    assert isinstance(coords_a, Coords), f"{coords_a=}. Must be an type Coords"
    assert isinstance(coords_b, Coords), f"{coords_b=}. Must be type Coords"

    # Transform co-ords into internal values suitable for calcs
    a_x1 = coords_a.left
    a_y1 = coords_a.top
    a_x2 = coords_a.width + coords_a.left
    a_y2 = coords_a.height + coords_a.top

    b_x1 = coords_b.left
    b_y1 = coords_b.top
    b_x2 = coords_b.width + coords_b.left
    b_y2 = coords_b.height + coords_b.top

    # Quick calc - if all  a points are within all b points or vice versa (not quite Jacquard but what I want)
    if (a_x1 >= b_x1 and a_x2 <= b_x2 and a_y1 >= b_y1 and a_y2 <= b_y2) or (
        b_x1 >= a_x1 and b_x2 <= a_x2 and b_y1 >= a_y1 and b_y2 <= a_y2
    ):
        return 1

    # Calc the coordinates of the intersection rectangle
    xA = max(a_x1, b_x1)
    yA = max(a_y1, b_y1)
    xB = min(a_x2, b_x2)
    yB = min(a_y2, b_y2)

    boxA_area = abs((a_x2 - a_x1) * (a_y2 - a_y1))
    boxB_area = abs(((b_x2 - b_x1) * (b_y2 - b_y1)))

    # Calc the area of the intersection rectangle
    intersecting_area = abs(max((xB - xA, 0)) * max((yB - yA), 0))

    if (
        boxB_area == 0 or boxB_area == 0 or intersecting_area == 0
    ):  # No overlap or some coord error
        return 0

    # Calc the intersection over union ratio
    return intersecting_area / float(boxA_area + boxB_area - intersecting_area)


def json_deep_copy(data: any):
    """
    Takes a data  object and returns a JSON deep copy of it. This will work for any object that can be serialized.

    Args:
        data (any): The data to be copied.

    Returns:
        A copy of the data that is passed in.
    """

    def update_dict(data_copy: dict, data: dict):
        """Updates a dictionary with the values of another dictionary.

        Args:
            data_copy (dict): the dictionary that we want to update
            data (dict): The data that you want to update.
        """
        for k, v in data_copy.values():
            if v != data[k]:
                if isinstance(v, dict):
                    update_dict(v, data[k])
                elif isinstance(v, list):
                    update_list(v, data[k])
                elif isinstance(v, float):
                    data_copy[k] = data[k]

    def update_list(data_copy: list, data: list):
        """Updates a list with the values of another list.

        Args:
            data_copy (list): The list that we are going to update.
            data (list): The data to be updated.
        """
        for i, value in enumerate(data_copy):
            if value != data[i]:
                if isinstance(value, dict):
                    update_dict(value, data[i])
                elif isinstance(value, list):
                    update_list(value, data[i])
                elif isinstance(value, float):
                    data_copy[i] = data[i]

    if data is None:
        return data

    # try:
    data_copy = json.loads(
        json.dumps(data),
    )
    if isinstance(data_copy, list):
        update_list(data_copy, data)
    else:
        update_dict(data_copy, data)
    # except OverflowError:
    #    data_copy = json.loads(json.dumps(data))
    # except Exception:
    # Remove before flight
    #    print (f"DBG non-json safe object passed {data=}. falling back to deepcopy")
    #    data_copy = copy.deepcopy(data)
    return data_copy


def levenshtein(str1: str, str2: str) -> float:
    """Takes two strings and returns a float between 0 and 1, where 0 means the strings are completely different and 1
    means they are identical

    Args:
        str1: The first string to compare
        str2: The string to compare to

    Returns:
        float: The levenshtein distance between two strings.
    """
    assert isinstance(str1, str), f"{str1=}. Must be a string"
    assert isinstance(str2, str), f"{str2=}. Must be a string"

    str1_len = len(str1)
    str2_len = len(str2)

    matrix = [list(range(str1_len + 1))] * (str2_len + 1)
    for str2_index in list(range(str2_len + 1)):
        matrix[str2_index] = list(range(str2_index, str2_index + str1_len + 1))

    for str2_index in list(range(0, str2_len)):
        for str1_index in list(range(0, str1_len)):
            str1_index: int
            str2_index: int
            if str1[str1_index] == str2[str2_index]:
                matrix[str2_index + 1][str1_index + 1] = min(
                    matrix[str2_index + 1][str1_index] + 1,
                    matrix[str2_index][str1_index + 1] + 1,
                    matrix[str2_index][str1_index],
                )
            else:
                matrix[str2_index + 1][str1_index + 1] = min(
                    matrix[str2_index + 1][str1_index] + 1,
                    matrix[str2_index][str1_index + 1] + 1,
                    matrix[str2_index][str1_index] + 1,
                )

    distance = float(matrix[str2_len][str1_len])
    result = 1.0 - distance / max(str1_len, str2_len)

    return result


def soundex(text_string: str, census_type: int = 2) -> str:
    """
    Author      : David Worboys
    Date        : 2018/07/31
    Method Name : Soundex
    Purpose     : Return a Soundex code for a given string

    Args:
        text_string (str): The string to be converted to a Soundex code.
        census_type (int): Defaults to 2. The type of Soundex code to return.
            0 - pre 1920 US, 1 - post 1930 US, 2 - Enhanced

    Returns:
        object:
    """
    assert isinstance(census_type, int) and (
        census_type in (0, 1, 2)
    ), f"{census_type=}. Must be int: 0 - pre 1920 US, 1 - post 1930 US 2 - Enhanced"

    code_it = False
    soundex_index = 0

    # if text_string.strip() == "":
    #    return ""

    # strip punctuation
    text = "".join(
        (char for char in text_string if char not in string.punctuation)
    ).upper()

    if text == "":
        return ""

    soundex = text[0]

    # Remove Vowels
    text = text[1:].replace("A", "-")
    text = text.replace("E", "-")
    text = text.replace("I", "-")
    text = text.replace("O", "-")
    text = text.replace("U", "-")

    # Normal US Census from 1920 onwards and enhanced
    if census_type in (1, 2):  # Pseudo-vowels
        text = text.replace("H", "-")
        text = text.replace("W", "-")

    text = text.replace("Y", "-")

    if (
        census_type == 2
    ):  # Replace these char combos in any part of string after first char
        text = text.replace("GH", "H")

    text = soundex + text

    if census_type == 2:
        # Replace these char combos at start of text string
        if (text[:2]) == "AA":
            text = text.replace("AA", "E", 1)

        if (text[:2]) == "AE":
            text = text.replace("AE", "E", 1)

        if (text[:2]) == "AI":
            text = text.replace("AI", "E", 1)

        if (text[:2]) == "AO":
            text = text.replace("AO", "E", 1)

        if (text[:2]) == "AA":
            text = text.replace("AA", "E", 1)

        if (text[:2]) == "IE":
            text = text.replace("IE", "E", 1)

        if (text[:2]) == "II":
            text = text.replace("II", "E", 1)
        if (text[:2]) == "IO":
            text = text.replace("IO", "E", 1)

        if (text[:2]) == "PF":
            text = text.replace("PF", "F", 1)

        if (text[:2]) == "PS":
            text = text.replace("PS", "S", 1)

        # Replace these char combos in any part of text string
        text = text.replace("DG", "G")
        text = text.replace("GN", "N")
        text = text.replace("KN", "N")
        text = text.replace("PH", "F")
        text = text.replace("MB", "M")
        text = text.replace("TCH", "CH")
        text = text.replace("MPS", "MS")
        text = text.replace("MPZ", "MZ")
        text = text.replace("MPT", "MT")

        soundex = text[0]  # First letter might have changed

    # Perform consonant mapping
    for text_char in text:
        if text_char == "-":
            code_it = True
        elif text_char in "BFPV":
            if (
                soundex[soundex_index] != "1" and soundex[soundex_index] not in "BFPV"
            ) or code_it:
                soundex += "1"
                soundex_index += 1
                code_it = False
        elif text_char in "CGJKQSXZ":
            if (
                soundex[soundex_index] != "2"
                and soundex[soundex_index] not in "CGJKQSXZ"
            ) or code_it:
                soundex += "2"
                soundex_index += 1
                code_it = False
        elif text_char in "DT":
            if (
                soundex[soundex_index] != "3" and soundex[soundex_index] not in "DT"
            ) or code_it:
                soundex += "3"
                soundex_index += 1
                code_it = False
        elif text_char in "L":
            if (
                soundex[soundex_index] != "4" and soundex[soundex_index] != "L"
            ) or code_it:
                soundex += "4"
                soundex_index += 1
                code_it = False
        elif text_char in "MN":
            if (
                soundex[soundex_index] != "5" and soundex[soundex_index] not in "MN"
            ) or code_it:
                soundex += "5"
                soundex_index += 1
                code_it = False
        elif text_char in "R":
            if (
                soundex[soundex_index] != "6" and soundex[soundex_index] != "R"
            ) or code_it:
                soundex += "6"
                soundex_index += 1
                code_it = False

    soundex = soundex.ljust(4, "0")

    return soundex[:4]


def Text_To_File_Name(text: str) -> str:
    """
    This function takes a string and returns a cleaned version of the string that is safe to use as a file name.

    Args:
        text(str): The text string to be transformed into a file name

    Returns:
        A cleaned up version of a string that can be used as a file name

    """
    assert (
        isinstance(text, str) and text.strip() != ""
    ), f"{text=} must be a non-empty string"

    # Remove any characters that are not allowed in file names
    cleaned_text = re.sub(r'[<>:"/\\|?*]', "", text)

    # Remove leading/trailing whitespaces and periods
    cleaned_text = cleaned_text.strip().strip(".")

    # Replace spaces with underscores
    cleaned_text = cleaned_text.replace(" ", "_")

    # Truncate the filename to a maximum length (depends on the OS but 255 is safe)
    max_filename_length = 255

    if max_filename_length and len(cleaned_text) > int(max_filename_length):
        cleaned_text = cleaned_text[: int(max_filename_length)]

    return cleaned_text


""" Regex for email check TODO put in function
re.fullmatch(regex, email):
(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=^_`{|}~-]+)*
|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]
|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")
@
(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?
|\[(?:(?:(2(5[0-5]|[0-4][0-9])
|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])
|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]
|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])
"""
