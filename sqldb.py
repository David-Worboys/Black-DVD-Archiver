"""
SQL Database interface layer for sqllite

Copyright (C) 2020  David Worboys (-:alumnus Moyhu Primary School et al.:-)

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
import base64
import binascii
import dataclasses
import hashlib
import pickle

import os
import sqlite3 as pysqlite3
from decimal import Decimal
from enum import unique
from pathlib import Path
from sqlite3 import Connection
from typing import Callable, TextIO, overload

import platformdirs

from file_utils import File
from sys_consts import SDELIM
from utils import NUMBER, Get_Unique_Sysid, Is_Complied, strEnum

# fmt: on


@dataclasses.dataclass(slots=True)
class Error:
    """Used to store the error status"""

    _code: int = 1
    _message: str = ""

    def __post_init__(self):
        pass

    @property
    def code(self) -> int:
        """Gets the error code

        Returns:
            int: The error code
        """
        return self._code

    @code.setter
    def code(self, value: int):
        """Sets the error code

        Args:
            value (int): The integer error code
        """
        assert isinstance(value, int), f"{value=}. Must be int"
        self._code = value

    @property
    def message(self) -> str:
        """Gets the error message

        Returns:
            str: The error message

        """
        return self._message

    @message.setter
    def message(self, value: str):
        """Sets the error message

        Args:
            value (str): The error message
        """
        assert isinstance(value, str), f"{value=}. Must be str"
        self._message = value


@unique
class SQLFUN(strEnum):  # SQLLITE Functions
    """Hardcodes sqllite function names to prevent spelling errors"""

    COUNT = "count"
    INSTR = "instr"
    LENGTH = "length"
    LTRIM = "ltrim"
    LOWER = "lower"
    RTRIM = "rtrim"
    REPLACE = "replace"
    SUBSTR = "substr"
    TRIM = "trim"
    UPPER = "upper"


@unique
class PRAGMA(strEnum):
    TABLE_INFO = "pragma_table_info"


@unique
class SQL(strEnum):
    """Hardcodes sqllite SQL names to prevent spelling errors"""

    AND = "AND"
    AS = "AS"
    AUTOINCREMENT = "AUTOINCREMENT"
    BOOLEAN = "BOOLEAN"  # DT
    BLOB = "BLOB"  # DT
    CHECK = "CHECK"
    COMMIT = "COMMIT"
    COUNT = "COUNT"
    CREATE_TABLE = "CREATE TABLE"
    CREATE_INDEX = "CREATE INDEX"
    CREATE_UNIQUE_INDEX = "CREATE UNIQUE INDEX"
    CURRENCY = "CURRENCY"  # DT
    DATE = "DATE"  # DT
    DECIMAL = "DECIMAL"  # DT
    DELETE = "DELETE"
    DROP_TABLE = "DROP TABLE"
    FOREIGN_KEY = "FOREIGN KEY"
    FROM = "FROM"
    IF_EXISTS = " IF EXISTS"
    IF_NOT_EXISTS = " IF NOT EXISTS"
    INSERTINTO = "INSERT INTO"
    INTEGER = "INTEGER"  # DT
    IS_NULL = "IS NULL"
    LIKE = "LIKE"
    NOT_NULL = "NOT NULL"
    NUMERIC = "NUMERIC"  # DT
    ON = "ON"
    OR = "OR"
    ORDERBY = "ORDER BY"
    PRIMARY_KEY = "PRIMARY KEY"
    REFERENCES = "REFERENCES"
    SELECT = "SELECT"
    SET = "SET"
    TEXT = "TEXT"  # DT
    TIME = "TIME"  # DT
    TIMESTAMP = "TIMESTAMP"  # DT
    TRANSACTION_BEGIN = "BEGIN TRANSACTION"
    TRANSACTION_END = "END TRANSACTION"
    TRANSACTION_ROLLBACK = "ROLLBACK"
    UPDATE = "UPDATE"
    UNIQUE = "UNIQUE"
    VALUES = "VALUES"
    VARCHAR = "VARCHAR"  # DT
    WHERE = "WHERE"


DATATYPES = (
    SQL.BOOLEAN,
    SQL.BLOB,
    SQL.CURRENCY,
    SQL.DATE,
    SQL.DECIMAL,
    SQL.INTEGER,
    SQL.NUMERIC,
    SQL.TEXT,
    SQL.TIME,
    SQL.TIMESTAMP,
    SQL.VARCHAR,
)


@unique
class SYSDEF(strEnum):
    SYSTABLE = "sys_def"
    SYSSETTINGS = "sys_settings"
    SQLMASTERTABLE = "sqlite_master"


@dataclasses.dataclass(slots=True)
class ColDef:
    """A class that defines a column in a table"""

    name: str
    data_type: SQL = SQL.VARCHAR
    size: int = 20
    num_decs: int = 0
    description: str = ""
    primary_key: bool = False
    foreign_key: bool = (
        False  # Kind of optional as code uses parent table and col to ascertain this
    )
    parent_table: str = ""  # Only used when foreign_key is true
    parent_col: str = ""  # Only used when foreign_key is true
    unique: bool = False
    deferrable: bool = True  # FK updates are deferred until transaction commit
    cascaded_update: bool = True  # FK updates cascade to children
    cascade_delete: bool = True  # FK deletes cascade to children
    index: bool = False

    def __post_init__(self) -> None:
        assert (
            isinstance(self.name, str) and self.name.strip() != ""
        ), f"{self.name=}. Must be a non-empty str"

        assert (
            self.data_type in DATATYPES
        ), f"data_type <{self.data_type}> not in list <{list(DATATYPES)}>"

        assert (
            isinstance(self.size, int) and self.size >= 0
        ), f"{self.size=}. Must be int >= 0"
        assert (
            isinstance(self.num_decs, int) and self.num_decs >= 0
        ), f"{self.num_decs=}. Must be int >= 0"
        assert isinstance(self.description, str), f"{self.description}. Must be str"
        assert isinstance(self.primary_key, bool), f"{self.primary_key=}. Must be bool"
        assert isinstance(self.foreign_key, bool), f"{self.foreign_key=}. Must be bool"
        assert isinstance(self.unique, bool), f"{self.unique=}. Must be bool"
        assert isinstance(self.deferrable, bool), f"{self.deferrable=}. Must be bool"
        assert isinstance(
            self.cascade_delete, bool
        ), f"{self.cascade_delete=}. Must be bool"
        assert isinstance(
            self.cascaded_update, bool
        ), f"{self.cascaded_update=}. Must be bool"
        assert isinstance(self.index, bool), f"{self.index=}. Must be bool"

        if self.foreign_key:  # Must have parent table and col
            assert (
                isinstance(self.parent_table, str) and self.parent_table.strip() != ""
            ), f"{self.parent_table}. Must be a mom-empty str for FK"
            assert (
                isinstance(self.parent_col, str) and self.parent_col.strip() != ""
            ), f"{self.parent_col=}. Must be  a non-empty str for FK"

        # Numbers need massaging depending on Num Decs
        if self.data_type in (SQL.INTEGER, SQL.DECIMAL):
            if self.num_decs == 0:
                self.data_type = SQL.INTEGER
            else:
                self.data_type = SQL.DECIMAL

    @property
    def type(self) -> SQL:
        """Returns the type of the column

        Returns:
            SQL: The type of the column.
        """
        return self.data_type


class App_Settings:
    """This class provides an easy interface for storing the most common types of application configuration settings"""

    def __init__(self, app_name: str):
        """Used to store application settings in an application database

        Args:
            app_name (str): Application name
        """

        assert (
            isinstance(app_name, str) and app_name.strip() != ""
        ), f"app_name <{app_name}> must be a non-empty str"

        self._app_name = app_name
        self._error_code = 1
        self._error_txt = ""
        self._new_cfg = True

        self._db_create()

    @property
    def db_get(self) -> "SQLDB":
        """
        Gets the SQL database connection

        Returns:
            SQLDB: The SQL database connection
        """
        return self._appcfg_db

    @property
    def db_path_get(self) -> str:
        """
        Returns the database path stored in the App cfg database.

        Returns:
            str: database path or empty string ""
        """
        path: str = self.setting_get("dbpath")

        file_handler = File()

        if self._error_code == 1:
            if file_handler.path_exists(path):
                if file_handler.path_writeable(path):
                    return path

                self._error_code = file_handler.Path_Error.NOTWRITEABLE
                self._error_txt = file_handler.Error_Dict[self._error_code]
            else:
                self._error_code = file_handler.Path_Error.NOTEXIST
                self._error_txt = file_handler.Error_Dict[self._error_code]
        return ""

    def db_path_set(self, path: str) -> int:
        """
        Sets the database path in the App cfg database.  Path must exist and be writeable

        Args:
            path (str): A non-empty file path

        Returns:
            str: 1 - path saved ok, -1 path not saved
        """
        assert isinstance(path, str), f"{path=}. Must be non-empty str"

        file_handler = File()

        if not file_handler.path_exists(path):
            self._error_message(
                "DB Path Error...", f"DB Path ~|<{path}>~| Does Not Exist!", fatal=False
            )
            return -1

        if not file_handler.path_writeable(path):
            self._error_message(
                "DB Path Error...",
                f"DB Path ~|<{path}>~| Is Not Writeable - Check Permissions!!",
                fatal=False,
            )
            return -1

        return self.setting_set("dbpath", path)

    def db_path_setnull(self) -> int:
        """Sets the database path to null (empty) in the App cfg database.

        Returns:
            int: 1 - path set null, -1 path not set
        """

        return self.setting_set("dbpath", None)

    def db_password_get(self) -> str | None:
        """Returns the password stored in the database

        Returns:
            str | None: Password

        """
        result = self.setting_get("dbpass")

        if self._error_code == 1:
            return result

        return ""

    def db_password_set(self, password: str, password_hash: bool = True) -> int:
        """Saves a database password

        Args:
            password (str): Password text in the clear
            password_hash (bool): True hash the password, False save in the clear

        Returns:
            int : 1 - Ok, -1 Failed to set

        """
        assert (
            isinstance(password, str) and password.strip() != ""
        ), f"{password}. Must be non-empty str"

        if password_hash:
            password = Crypto().hash_password(password)

        return self.setting_set("dbpass", password)

    def db_password_verify(self, password: str, password_hash: bool = True) -> bool:
        """Verifies the database password against the given password. If the database password is hashed, then the
        given password must also be hashed.

        Args:
            password (str): Password in clear text
            password_hash (bool): True hash the password, False save in the clear

        Returns:
            bool : True - passwords match, False - no match

        """
        assert (
            isinstance(password, str) and password.strip() != ""
        ), f"{password}. Must be non-empty str"
        assert isinstance(password_hash, bool), f"{password_hash=}. Must be bool"

        if password_hash:
            if Crypto().verify_password(self.db_password_get(), password):
                return True
        else:
            return self.db_password_get() == password

        return False

    @property
    def error_code(self) -> int:
        """Returns the error code

        Returns:
            int : The error code...if -1 then something is wrong, 1 is good

        """
        return self._error_code

    @property
    def error_message(self) -> str:
        """Returns the error message

        Returns:
            str : The error message.
        """
        return self._error_txt

    def setting_exist(self, setting_name: str) -> bool:
        """Determines if a database setting exists

        Args:
            setting_name (str): The setting name

        Returns:
            bool : True - setting exists, False it does not

        """
        assert (
            isinstance(setting_name, str) and setting_name.strip() != ""
        ), f"{setting_name=}. Must be str"

        sql_statement = (
            f"{SQL.SELECT} id {SQL.FROM} {SYSDEF.SYSTABLE} "
            + f"{SQL.WHERE} app_name ='{self._app_name}' "
        )

        setting_result = self._appcfg_db.sql_execute(sql_statement)
        result: Error = self._appcfg_db.get_error_status()

        self._error_code = result.code
        self._error_txt = result.message

        if self._error_code == 1:
            app_id = setting_result[0][0]  # Row 1, Col 1

            if app_id > 0:
                sql_statement = (
                    f"{SQL.SELECT} {SQL.COUNT}('*') {SQL.FROM} {SYSDEF.SYSSETTINGS} "
                    + f" {SQL.WHERE} app_id = {app_id} {SQL.AND} setting_name ="
                    f" '{setting_name}' "
                )

                setting_result = self._appcfg_db.sql_execute(sql_statement)
                result = self._appcfg_db.get_error_status()

                self._error_code = result.code

                if self._error_code == 1:
                    if setting_result[0][0] == 0:  # Setting Does Not Exist
                        return False

                    return True
        return False

    @overload
    def setting_get(self, setting_name: str) -> str: ...

    @overload
    def setting_get(self, setting_name: str) -> bool: ...

    @overload
    def setting_get(self, setting_name: str) -> int: ...

    @overload
    def setting_get(self, setting_name: str) -> float: ...

    @overload
    def setting_get(self, setting_name: str) -> None: ...

    def setting_get(self, setting_name: str) -> str | bool | int | float | None:
        """Gets the setting referred to bby the setting_name

        Args:
            setting_name (str): NAme of setting

        Returns:
            str| bool| int| float| None:: The setting value
        """
        assert (
            isinstance(setting_name, str) and setting_name.strip() != ""
        ), f"{setting_name=}. Must be non-empty str"

        sql_statement = (
            f"{SQL.SELECT} id {SQL.FROM} {SYSDEF.SYSTABLE} "
            + f"{SQL.WHERE} app_name ='{self._app_name}' "
        )

        setting_result = self._appcfg_db.sql_execute(sql_statement)
        error: Error = self._appcfg_db.get_error_status()

        self._error_code = error.code
        self._error_txt = error.message

        if self._error_code == 1:
            app_id = setting_result[0][0]  # Row 1, Col 1

            sql_statement = (
                f"{SQL.SELECT} setting_value, datatype"
                + f" {SQL.FROM} {SYSDEF.SYSSETTINGS} "
                + f"{SQL.WHERE} app_id ="
                f" {app_id} {SQL.AND} setting_name='{setting_name}'"
            )

            sql_result = self._appcfg_db.sql_execute(sql_statement)
            error: Error = self._appcfg_db.get_error_status()

            self._error_code = error.code
            self._error_txt = error.message

            if self._error_code == 1:
                if not sql_result:  # No Rows
                    return None

                setting_value: str | bool | int | float = sql_result[0][
                    0
                ]  # row 1 col 1
                setting_datatype: SQL = sql_result[0][1]  # row 1 col 2

                match setting_datatype:
                    case SQL.BOOLEAN:
                        # Setting value should always be either "True" or "False"
                        if str(setting_value).lower() == "true":
                            return True

                        return False
                    case SQL.INTEGER:
                        return int(setting_value)
                    case SQL.DECIMAL:
                        return float(setting_value)
                    case SQL.TEXT:
                        return setting_value  # Already a str!
                    case _:
                        raise Exception(
                            f"Invalid Datatype {setting_datatype} : {setting_value}"
                        )
        return None

    def setting_set(
        self, setting_name: str, setting_value: bool | int | float | str | None
    ) -> int:
        """Sets the value associated with the setting_name

        Args:
            setting_name (str): Name of setting
            setting_value (bool | int | float | str | None): Value of setting

        Returns:
            int: 1 ok, -1 fail
        """
        assert (
            isinstance(setting_name, str) and setting_name.strip() != ""
        ), f"{setting_name=}. Must be non-empty str"

        assert isinstance(
            setting_value, (bool, int, float, str)
        ), f"{setting_value=}. Must be bool, int, float or str"

        sql_statement = (
            f"{SQL.SELECT} id {SQL.FROM} {SYSDEF.SYSTABLE} "
            + f"{SQL.WHERE} app_name ='{self._app_name}' "
        )

        app = self._appcfg_db.sql_execute(sql_statement)
        result: Error = self._appcfg_db.get_error_status()

        self._error_code = result.code

        if self._error_code == 1:
            app_id: int = app[0][0]  # Row 1 Col 1

            if app_id > 0:
                sql_statement = (
                    f"{SQL.SELECT} {SQL.COUNT}('*') {SQL.FROM} {SYSDEF.SYSSETTINGS} "
                    + f" {SQL.WHERE} app_id = {app_id} {SQL.AND} setting_name ="
                    f" '{setting_name}' "
                )

                setting_result = self._appcfg_db.sql_execute(sql_statement)
                result: Error = self._appcfg_db.get_error_status()

                self._error_code = result.code

                if self._error_code == 1:
                    if setting_result[0][0] == 0:  # Setting Does Not Exist
                        match setting_value:
                            case bool():
                                datatype = SQL.BOOLEAN
                            case int():
                                datatype = SQL.INTEGER
                            case float():
                                datatype = SQL.DECIMAL
                            case str():
                                datatype = SQL.TEXT
                            case _:
                                raise ValueError(
                                    f"setting_name <{setting_name}>, setting_value"
                                    f" <{setting_value}> " + "has an unsupported_type"
                                    f" <{type(setting_value)}> "
                                )

                        sql_statement = (
                            f"{SQL.INSERTINTO} {SYSDEF.SYSSETTINGS} "
                            + "('app_id','setting_name','setting_value','datatype') "
                            + f"{SQL.VALUES} "
                            + f" ({app_id},'{setting_name}','{str(setting_value)}','{datatype}')"
                        )

                    else:
                        sql_statement = (
                            f"{SQL.UPDATE} {SYSDEF.SYSSETTINGS} {SQL.SET} "
                            + f"setting_value = '{str(setting_value)}' {SQL.WHERE} "
                            + f" setting_name = '{setting_name}' and app_id={app_id}"
                        )

                    self._appcfg_db.sql_execute(sql_statement)
                    result = self._appcfg_db.get_error_status()

                    self._error_code = result.code
                    self._error_txt = result.message

                    if self._error_code == 1:
                        return self._appcfg_db.sql_commit
        return -1

    @property
    def new_cfg(self) -> bool:
        """Used to determine if this instance is a new App cfg installation

        Returns:
            bool: True if new configuration, False if existing configuration
        """
        return self._new_cfg

    @property
    def unique_sysid_get(self) -> str:
        """Gets a unique system id

        Returns:
            str: The unique system ID

        """
        return Get_Unique_Sysid()

    # ----------------------------------------------------------------------------#
    #        Private Methods                                                      #
    # ----------------------------------------------------------------------------#
    def _db_create(self) -> int:
        """
        Creates the App cfg database if this is a new App cfg installation

        Returns:
            int: 1 DB Created, -1 DB Creation Failed

        """
        self._new_cfg = True
        suffix = "cfg"

        self._app_data_dir = platformdirs.user_config_dir(self._app_name)
        file_handler = File()

        if file_handler.file_exists(self._app_data_dir, self._app_name, suffix):
            self._new_cfg = False

        if not file_handler.path_exists(self._app_data_dir):
            file_handler.make_dir(self._app_data_dir)

        if file_handler.path_exists(self._app_data_dir):
            if not file_handler.path_writeable(self._app_data_dir):
                raise ValueError(
                    f"Folder <{self._app_data_dir}> Cannot Be Written To! - Check"
                    " Permissions"
                )
        else:
            raise ValueError(f"Folder <{self._app_data_dir}> Cannot Be Created!")

        password = self.unique_sysid_get

        self._appcfg_db = SQLDB(
            appname=self._app_name,
            dbpath=self._app_data_dir,
            dbfile=self._app_name,
            suffix=suffix,
            dbpassword=password,
        )

        if not self._appcfg_db.table_exists(
            SYSDEF.SYSTABLE
        ):  # Belts and Braces are good!
            self._new_cfg = True

        if self._new_cfg:  # Create Appcfg Database tables
            result = self._appcfg_db.table_create(
                SYSDEF.SYSTABLE,
                (
                    ColDef(
                        name="id",
                        description="pk_id",
                        data_type=SQL.INTEGER,
                        primary_key=True,
                    ),
                    ColDef(
                        name="app_name",
                        description="application_name",
                        data_type=SQL.VARCHAR,
                        size=255,
                    ),
                ),
            )

            if result == 1:
                result = self._appcfg_db.table_create(
                    SYSDEF.SYSSETTINGS,
                    (
                        ColDef(
                            name="id",
                            description="pk_id",
                            data_type=SQL.INTEGER,
                            primary_key=True,
                        ),
                        ColDef(
                            name="app_id",
                            description="fk1_id",
                            data_type=SQL.INTEGER,
                            foreign_key=True,
                            parent_table=SYSDEF.SYSTABLE,
                            parent_col="id",
                        ),
                        ColDef(
                            name="setting_name",
                            description="setting_name",
                            data_type=SQL.VARCHAR,
                            size=255,
                        ),
                        ColDef(
                            name="setting_value",
                            description="setting_value",
                            data_type=SQL.VARCHAR,
                            size=255,
                        ),
                        ColDef(
                            name="datatype",
                            description="setting datatype",
                            data_type=SQL.VARCHAR,
                            size=50,
                        ),
                    ),
                )

            if result == 1:
                sql_statement = (
                    f"{SQL.INSERTINTO} {SYSDEF.SYSTABLE} "
                    + f"(app_name) {SQL.VALUES} ('{self._app_name}')"
                )

                self._appcfg_db.sql_execute(sql_statement)
                result_error: Error = self._appcfg_db.get_error_status()

                self._error_code = result_error.code

                if self._error_code == 1:
                    if self._appcfg_db.sql_commit == 1:
                        if self.db_path_set(path=self._app_data_dir) == 1:
                            return self.setting_set("First_Run", True)

                        return -1
                else:
                    return -1
        else:
            if self.setting_exist("dbpath"):
                if self.setting_get("dbpath") == "":
                    self.setting_set("dbpath", self._app_data_dir)
        return 1

    def _error_message(self, title: str, message: str, fatal: bool = True) -> int:
        """

        Args:
            title (str): Title of error
            message (str ): Error Message
            fatal (bool): True if fatal otherwise raise ValueError

        Returns:
            int: 1 if not fatal otherwise raises a value _error halting app execution and displays an _error message
        """
        assert (
            isinstance(title, str) and title.strip() != ""
        ), f"{title=}. Must be non-empty str"
        assert (
            isinstance(message, str) and message.strip() != ""
        ), f"{message=}. Must be non-empty str"
        assert isinstance(fatal, bool), f"{fatal=}. Must be bool"

        self._error_code = -1
        self._error_txt = message

        if fatal:
            raise ValueError(message)

        return 1


# ----------------------------------------------------------------------------#
#        Crypto - Crypto class for handling passwords                         #
# ----------------------------------------------------------------------------#
class Crypto:
    """Crypto class for handling passwords securely"""

    def hash_password(self, clear_password: str) -> str:
        """Hashes a password.

        Args:
            clear_password: Non-hashed password

        Returns:
            str: The hashed password
        """
        assert (
            isinstance(clear_password, str) and clear_password.strip() != ""
        ), f"{clear_password=}. Must be non-empty str"

        salt = hashlib.sha256(os.urandom(60)).hexdigest().encode("ascii")

        pwdhash = hashlib.pbkdf2_hmac(
            "sha512", clear_password.encode("utf-8"), salt, 100_000
        )
        pwdhash = binascii.hexlify(pwdhash)

        return (salt + pwdhash).decode("ascii")

    def verify_password(self, password_hash: str, clear_password: str) -> bool:
        """Verifies a non-hashed password against a hashed password

        Args:
            password_hash (str): password hash
            clear_password (str): non-hashed password

        Returns:
            bool: True - Passwords match, False Passwords do not match
        """
        assert (
            isinstance(password_hash, str) and password_hash.strip() != ""
        ), f"{password_hash=}. Must be non-empty str"
        assert (
            isinstance(clear_password, str) and clear_password.strip() != ""
        ), f"{clear_password=}. Must be non-empty str"

        salt = password_hash[:64]
        password_hash = password_hash[64:]

        pwdhash = hashlib.pbkdf2_hmac(
            "sha512", clear_password.encode("utf-8"), salt.encode("ascii"), 100_000
        )

        pwdhash_str = binascii.hexlify(pwdhash).decode("ascii")

        return pwdhash_str == password_hash


def get_rowcol_value(row: int, col: int, row_list: list) -> str:
    """Gets the value at a given row col from the row list produced by a select statement

    Args:
        row (int): The row of the desired value
        col (int): The col of the desired value
        row_list (list): The row list structure returned form a select statement

    Returns:
        str: The value at the given row and column in a row list

    """
    return row_list[1][row][col]


@dataclasses.dataclass(slots=True)
class SQL_Shelf:
    """Stores dictionaries in a Python shelf like manner"""

    # Public
    db_name: str = ""
    error: Error = dataclasses.field(default_factory=Error)

    # Private
    _app_database: "SQLDB" = None
    _data_path: str = ""

    def __post_init__(self):
        """Initialises the object"""
        assert (
            isinstance(self.db_name, str) and self.db_name.strip() != ""
        ), f"{self.db_name=}. Must be non-empty str"

        file_handler = File()
        self._data_path = platformdirs.user_data_dir(self.db_name)

        if not file_handler.path_exists(self._data_path):
            file_handler.make_dir(self._data_path)

            if not file_handler.path_exists(self._data_path):
                self.error.message = f"Failed To Create {self.db_name} Data Folder"
                return None

        self._app_database = SQLDB(
            appname=self.db_name,
            dbpath=self._data_path,
            dbfile=self.db_name,
            suffix=".db",
            dbpassword="666evil",
        )

        error_status = self._app_database.get_error_status()

        if error_status.code == -1:
            return None

        self._db_init()

        return None

    def _db_init(self) -> tuple[int, str]:
        """Initialises the database

        Returns:
            tuple[int, Optional[float]]: tuple containing result code and

            - arg 1: If the status code is 1, the operation was successful otherwise it failed.
            - arg 2: If the status code is -1, an error occurred, and the message provides details.:
        """

        if not self._app_database.table_exists("shelves"):
            shelve_def = (
                ColDef(
                    name="id",
                    description="pk_id",
                    data_type=SQL.INTEGER,
                    primary_key=True,
                ),
                ColDef(
                    name="name",
                    description="Shelve Name",
                    data_type=SQL.VARCHAR,
                    size=255,
                ),
                ColDef(
                    name="value",
                    description="Shelve Value",
                    data_type=SQL.VARCHAR,
                    size=1000000000,  # Has to be big
                ),
            )

            if (
                self._app_database.table_create(
                    table_name="shelves", col_defs=shelve_def
                )
                == -1
            ):
                self.error = self._app_database.get_error_status()

                if self.error.code == -1:
                    return -1, self.error.message

        return 1, ""

    def open(self, shelf_name: str) -> dict:
        """Opens a shelf for use

        Args:
            shelf_name (str): THe shelf name

        Returns:
            dict: Dictionary stored on the shelf
        """
        assert (
            isinstance(shelf_name, str) and shelf_name.strip() != ""
        ), f"{shelf_name=}. Must be non-empty str"

        sql_statement = (
            f"{SQL.SELECT} {SQL.COUNT}('name') {SQL.FROM} shelves "
            + f" {SQL.WHERE} name = '{shelf_name}' "
        )

        setting_result = self._app_database.sql_execute(sql_statement)
        result: Error = self._app_database.get_error_status()

        self.error.code = result.code
        self.error.message = result.message

        if self.error.code == 1:
            if setting_result[0][0] == 0:  # Shelf Does Not Exist:
                self.error.code, self.error.message = self._app_database.sql_update(
                    col_dict={"name": shelf_name, "value": {}},
                    table_str="shelves",
                    debug=False,
                )
            else:
                select_result = self._app_database.sql_select(
                    col_str="name,value",
                    table_str="shelves",
                    where_str=f"name='{shelf_name}'",
                    debug=False,
                )

                # The "{}" check addresses a rare issue where "{}" is in the sql output instead of "" - I have not been
                # able to track down why this occurs but suspect an empty dict is getting saved as string somewhere.
                if (
                    select_result
                    and select_result[0][1] is not None
                    and select_result[0][1].strip() != ""
                    and select_result[0][1].strip() != "{}"
                ):
                    try:
                        shelf_dict = pickle.loads(
                            base64.b64decode(select_result[0][1].encode())
                        )

                        return shelf_dict
                    except Exception as e:
                        self.error.code = -1
                        self.error.message = f"{e}"

        return {}

    def delete(self, shelf_name: str, shelf_key: str) -> tuple[int, str]:
        """Deletes an item from the shelf

        Args:
            shelf_name: The shelf name
            shelf_key: The key of the shelf item to be deleted

        Returns:
            tuple[int, Optional[float]]: tuple containing result code and

            - arg 1: If the status code is 1, the operation was successful otherwise it failed.
            - arg 2: If the status code is -1, an error occurred, and the message provides details.:

        """
        assert (
            isinstance(shelf_name, str) and shelf_name.strip() != ""
        ), f"{shelf_name=}. Must be non-empty str"

        assert (
            isinstance(shelf_key, str) and shelf_key.strip() != ""
        ), f"{shelf_key=}. Must be non-empty str"

        shelf_dict = self.open(shelf_name=shelf_name)

        if self.error.code == -1:
            return -1, self.error.message

        if shelf_key in shelf_dict:
            shelf_dict.pop(shelf_key)
            self.update(shelf_name=shelf_name, shelf_data=shelf_dict)

            if self.error.code == -1:
                return -1, self.error.message

        return 1, ""

    def update(self, shelf_name: str, shelf_data: dict) -> tuple[int, str]:
        """Updates the contents of the shelf with the passed in dictionary

        Args:
            shelf_name (str): THe shelf name
            shelf_data (dict): The dictionary to store on the shelf

        Returns:
            tuple[int, Optional[float]]: tuple containing result code and

            - arg 1: If the status code is 1, the operation was successful otherwise it failed.
            - arg 2: If the status code is -1, an error occurred, and the message provides details.:
        """
        assert (
            isinstance(shelf_name, str) and shelf_name.strip() != ""
        ), f"{shelf_name=}. Must be non-empty str"

        assert isinstance(shelf_data, dict), f"{shelf_data=}. Must be a dict"

        try:
            pickle_dict_dump = base64.b64encode(pickle.dumps(shelf_data)).decode()

            sql_statement = (
                f"{SQL.SELECT} {SQL.COUNT}('name') {SQL.FROM} shelves "
                + f" {SQL.WHERE} name = '{shelf_name}' "
            )

            setting_result = self._app_database.sql_execute(sql_statement)
            result: Error = self._app_database.get_error_status()

            self.error.code = result.code
            self.error.message = result.message

            if self.error.code == 1:
                if setting_result[0][0] == 0:  # Shelf Does Not Exist:
                    self.error.code, self.error.message = self._app_database.sql_update(
                        col_dict={
                            "value": pickle_dict_dump,
                        },
                        table_str="shelves",
                        debug=False,
                    )
                else:
                    self.error.code, self.error.message = self._app_database.sql_update(
                        col_dict={
                            "value": pickle_dict_dump,
                        },
                        table_str="shelves",
                        where_str=f"name='{shelf_name}'",
                        debug=False,
                    )

        except Exception as e:
            self.error.code = -1
            self.error.message = str(e)

        return self.error.code, self.error.message


class SQLDB:
    """Class provides app database, utility and SQL methods -> SQLLITE focused but could be extended"""

    def __init__(
        self,
        appname: str,
        dbpath: str,
        dbfile: str,
        suffix: str,
        dbpassword: str,  # Need a special sqllite build for this to work
        currency_num_decs: int = 2,
    ):
        # Private instance methods
        self._db_new = False
        self._transaction_begun = False  # Used in SQL Statements execution

        assert (
            isinstance(appname, str) and appname.strip() != ""
        ), f"{appname=}. Must be a non-rmpty str"
        assert isinstance(dbpath, str), f"{dbpath=}. Must be a str"
        assert (
            isinstance(dbfile, str)
            and dbfile.strip() != f"{dbfile=}. Must be a non-empty str"
        )
        assert (
            isinstance(suffix, str)
            and suffix.strip() != f"{suffix=}. Must be a non-empty str"
        )
        assert isinstance(dbpassword, str), f"{dbpassword=}. Must be a str"
        assert (
            isinstance(currency_num_decs, int) and currency_num_decs >= 0
        ), f"{currency_num_decs=}. Must be an int >= 0"

        if dbpath.strip() == "":
            dbpath = os.getcwd()

        self._multiplier_int: int = 10**currency_num_decs

        if not suffix.startswith("."):
            suffix = "." + suffix

        self._error = -1
        self._error_txt = ""

        file_handler = File()

        if file_handler.path_exists(dbpath):
            if file_handler.path_writeable(dbpath):
                dbfile_instance = Path(dbpath, dbfile).with_suffix(suffix)

                if file_handler.file_exists(dbpath, dbfile, suffix):
                    self._db_new = True

                try:
                    self._dbconnection = pysqlite3.dbapi2.connect(
                        str(dbfile_instance.resolve()),
                        detect_types=1,  # PARSE_DECLTYPES = 1
                    )

                    if file_handler.file_exists(dbpath, dbfile, suffix) is not True:
                        self._error_message(
                            "DB Error...",
                            f"dbpath ~|<{dbpath}>~| File Could Not Be Accessed",
                        )
                except:
                    self._error_message(
                        "DB_Error",
                        f"Database File <{str(dbfile_instance.resolve())}> Not"
                        " Found or Could Not Be created ",
                    )

                try:
                    self._dbconnection.execute(f'pragma key="{dbpassword}"')
                    self._error = 1
                except:
                    self._error_message("DB_Error", "Incorrect Password For Database")

                try:
                    self._dbconnection.execute("pragma foreign_keys = ON")
                    self._error = 1
                except:
                    self._error_message("DB_Error", "Could not set foreign_keys ON!")

                # Used for Currency conversions
                pysqlite3.register_adapter(Decimal, self._convert_to_base)
                pysqlite3.register_converter("CURRENCY", self._convert_from_base)

                pysqlite3.register_adapter(bool, int)
                pysqlite3.register_converter(SQL.BOOLEAN, lambda v: bool(int(v)))

            else:
                self._error_message(
                    "DB Error..", f"Cannot Write To {dbpath=} - Check Permissions!"
                )
        else:
            self._error_message("DB Error..", f"{dbpath=} does not exist")

    def disconnect(self) -> None:
        """Disconnects from the database"""
        self._dbconnection.close()

    def load_csv_file(
        self,
        file_name: str,
        table_name: str,
        text_index: int = 1,
        has_header: bool = True,
        delimiter: str = ",",
        drop_table: bool = True,
    ) -> None:
        """Loads a CSV file into the database

        Args:
            file_name (str): Name of CSV file (can contain the path)
            table_name (str): Name of database table
            text_index (int): line in file to start loading from (default: {1})
            has_header (bool): Set True if the CSV file has a header row (default: {True})
            delimiter (str): CSV field separator (default: {","})
            drop_table (bool): Set True to drop table (default: {True})

        Returns:
            None:
        """

        def _get_col_props(
            file_ptr: TextIO, delimiter: str, has_header: bool
        ) -> dict[str, list[int | None]]:
            """Get column properties

            Args:
                file_ptr (TextIO): File Handle
                delimiter (str): Delimiter used to extract columns
                has_header (bool): Determine if the hile has a header row

            Returns:
                dict[str, list[int | None]]: Dictionary containing the column properties

            """
            current_pos = file_ptr.tell()
            file_ptr.seek(0)
            col_def = {}
            col_names = []

            for line_no, line in enumerate(csv_file.readlines()):
                if line_no == 0:
                    if has_header:
                        col_names: list[str] = line.strip().split(delimiter)
                    else:
                        for col_index, _ in enumerate(line.strip().split(delimiter)):
                            col_names.append(f"col{col_index}")
                else:
                    scan_pos: int = file_ptr.tell()

                    for col_index, col_name in enumerate(col_names):
                        col_values: list[str] = line.strip().split(delimiter)

                        if col_name not in col_def:
                            col_def[col_name] = [-1, None, 0, 0]

                        col_definition: dict | None = col_def[col_name]

                        if len(col_values[col_index]) > col_definition[0]:
                            col_definition[0] = len(col_values[col_index])

                        if col_definition[1] is None:
                            if col_values[col_index].replace("-", "").isdigit():
                                col_definition[1] = SQL.INTEGER
                            elif col_values[col_index].replace(".", "").isdigit():
                                col_definition[1] = SQL.DECIMAL
                                col_definition[2] = (
                                    len(col_values[col_index])
                                    - col_values[col_index].index(".")
                                ) - 1
                            else:
                                col_definition[1] = SQL.VARCHAR

                        col_definition[3] = col_index

                        col_def[col_name] = col_definition

                    file_ptr.seek(scan_pos)

            file_ptr.seek(current_pos)

            return col_def

        # ####### Main body #######
        assert (
            isinstance(file_name, str) and file_name.strip() != ""
        ), f"{file_name=}. Must be non-empty str"
        assert (
            isinstance(table_name, str) and table_name.strip() != ""
        ), f"{table_name=}. Must be non-empty str"
        assert isinstance(text_index, int), f"{text_index=}. Must be int"
        assert isinstance(has_header, bool), f"{has_header=}. Must be bool"
        assert isinstance(delimiter, str), f"{delimiter=}. Must be str"

        assert len(delimiter) == 1, "delimiter must be a single char"

        if not os.path.isfile(file_name) and not os.access(file_name, os.R_OK):
            self._error_message(
                "CSV File Access Error...",
                f"File ~|{file_name}~| doesn't exist or is not readable",
            )

        if self.table_exists(table_name) and drop_table:
            # self.table_create()
            pass

        with open(file_name, "r") as csv_file:
            for line_no, line in enumerate(csv_file.readlines()):
                line_list = line.strip().split(delimiter)

                if line_no == 0:
                    assert (
                        0 <= text_index - 1 <= len(line)
                    ), f"text_index({text_index - 1}) >= 0 and text_index <={len(line)}"
                    column_definition = _get_col_props(csv_file, delimiter, has_header)

                    table_def = []

                    for key, value in column_definition.items():
                        table_def.append(
                            ColDef(
                                name=key,
                                data_type=value[1],
                                size=value[0],
                                num_decs=value[2],
                            )
                        )

                    self.table_create(table_name, table_def)

                    sql_insert = f"({SQL.INSERTINTO} {table_name}"

                    if has_header:
                        continue

                sql_value = ""
                col_names = ""

                for key, value in column_definition.items():
                    if value[1] == SQL.VARCHAR:
                        if line_list[value[3]] == "":
                            pass
                        else:
                            char_value = line_list[value[3]].replace("'", "''")
                            sql_value += f"'{char_value}',"
                            col_names += key + ","

                    else:
                        if line_list[value[3]] == "":
                            pass
                        else:
                            sql_value += f"{line_list[value[3]]},"
                            col_names += key + ","

                col_names = col_names[-1]
                sql_value = sql_value[-1]

                sql_value = f" ({col_names}) {SQL.VALUES} ({sql_value})"

                self.sql_execute(sql_insert + sql_value)

            self.sql_commit

    @property
    def sql_commit(self) -> int:
        """Finalises and saves the database changes made in a transaction block

        Returns:
            int: 1 Database changes committed, -1 Database error occurred
        """
        try:
            if self._transaction_begun:
                self._dbconnection.execute(SQL.TRANSACTION_END)
            self._transaction_begun = False
            return 1
        except Exception as error:
            self._dbconnection.execute(SQL.TRANSACTION_ROLLBACK)

            print(f" DB Commit Failed! {error=}")

            return -1

    def sql_execute(
        self, sql_statement: str, transactional: bool = True, debug: bool = False
    ) -> list | tuple:
        """Executes a SQL statement

        Args:
            sql_statement (str): THe SQL statement
            transactional (bool): Use Transactions (Default)
            debug (bool): True - print debug statements, False - Do not print

        Returns:
            list | tuple: List containing rows returned from database or empty tuple if not a select statement or error
        """
        assert (
            isinstance(sql_statement, str) and sql_statement.strip() != ""
        ), f"{sql_statement=}. Must be non-empty str"
        assert isinstance(transactional, bool), f"{transactional=}. Must be bool"
        assert isinstance(debug, bool), f"{debug=}. Must be bool"

        sql_statement = sql_statement.strip()

        if sql_statement.upper().startswith(SQL.SELECT):
            if debug and not Is_Complied():
                print("DBG @@@================>", sql_statement)

            try:
                cursor = self._dbconnection.cursor()
                cursor.execute(sql_statement)

                self._error = 1
                self._error_txt = ""

                return cursor.fetchall()
            except Exception as error:
                self._transaction_begun = False

                print(f"{sql_statement=} - {error=}")

                self._error = -1
                self._error_txt = error

                raise ValueError(f"{error=}\n{sql_statement}")
        else:
            if debug and not Is_Complied():
                print("DBG ***================>", sql_statement)
            try:
                if transactional:  # Could be multiple sql statements in transaction
                    if (
                        not self._transaction_begun
                    ):  # Begins transaction. sql_commit ends transaction
                        self._transaction_begun = True
                        self._dbconnection.execute(SQL.TRANSACTION_BEGIN)

                    self._dbconnection.execute(sql_statement)

                elif not transactional:  # One SQL statement in transaction
                    self._transaction_begun = True
                    self._dbconnection.execute(SQL.TRANSACTION_BEGIN)

                    self._dbconnection.execute(sql_statement)

                    if self.sql_commit == -1:
                        return ()

                self._error = 1
                self._error_txt = ""

                return ()
            except Exception as error:
                self._transaction_begun = False

                print(f"DBG Dev Error {error} \n {sql_statement}")

                self._error = -1
                self._error_txt = error

                raise ValueError(error)

    def sql_delete(
        self,
        table: str,
        where_str: str,
        transactional: bool = True,
        debug: bool = False,
    ) -> list | tuple:
        """Simplified way of doing a SQL Delete

        Args:
            table (str): Table from which data is to be deleted
            where_str (str): Where a statement specifying scope of deletion
            transactional (bool): Use Transactions (Default)
            debug (bool): Prints the SQL statement for debugging purposes

        Returns:
            list | tuple: Expect an empty tuple to be returned. Check error after executing
        """
        assert (
            isinstance(table, str) and table.strip() != ""
        ), f"{table=}. Must be non-empty str"
        assert isinstance(where_str, str), f"{where_str=}. Must be non-empty str"

        if not self.table_exists(table):
            raise ValueError(f"Table <{table}> does not exist!")

        sql_statement = f"{SQL.DELETE} {SQL.FROM} {table}"

        if where_str.strip() != "":
            sql_statement += f" {SQL.WHERE} {where_str} "

        return self.sql_execute(sql_statement, transactional=transactional, debug=debug)

    def _check_col(self, col_item: list[str], tables: list[str]) -> None:
        """Check if the column exists in the table. Throws an exception if it does not

        Args:
            col_item (list[str]): lid of column names
            tables (list[str]): list of tables
        """

        # Table/Column cannot start with a quote(') or ('-') or be a number
        assert (
            isinstance(col_item, list) and col_item
        ), f"DBG {col_item=}. Must be a list with at least one entry"

        match len(col_item):
            case 1:  # Col Only
                if (
                    col_item[0].startswith("'")
                    or col_item[0].startswith("-")
                    or col_item[0].isdigit()
                ):  # Text data
                    return None

                assert len(tables) == 1, (
                    f"col <{col_item[0]}> must be in this format: "
                    + f" <table_name.{col_item[0]}> as there is more "
                    + f" than 1 table listed! <{tables}>"
                )

                table_name = "".join(tables)

                assert self.table_exists(
                    table_name
                ), f"table <{table_name}> does not exist!"

            case 2:  # Table.Col
                if (
                    col_item[0].startswith("'")
                    or col_item[0].startswith("-")
                    or col_item[0].isdigit()
                ):  # Text data
                    return None

                if (
                    col_item[1].startswith("'")
                    or col_item[1].startswith("-")
                    or col_item[1].isdigit()
                ):  # Text data
                    return None

                assert self.table_exists(
                    col_item[0]
                ), f"table <{col_item[0]}> does not exist!"

                assert self.col_exists(
                    col_item[0], col_item[1]
                ), f"Col <{col_item[1]}> does not exist in table <{col_item[0]}>!"

            case _:  # Not legal
                raise ValueError(f"col <{col_item}> must be [column | table.column]")

    def sql_select(
        self,
        col_str: str,
        table_str: str,
        where_str: str = "",
        orderby_str: str = "",
        udf_function_name: str = "",
        debug: bool = False,
    ) -> list | tuple:
        """Simplified way to generate simple SQL statements

        Args:
            col_str (str): String of col names delimited by ,
            table_str (str): String of table names delimited by ,
            where_str (str): String of where conditions delimited by ,
            orderby_str (str): String of order by conditions delimited by ,
            udf_function_name(str): User defined function name used in query
            debug (bool): True - print debug statements, False - Do not print

        Returns:
            list | tuple: The result of the select statement
        """

        assert (
            isinstance(col_str, str) and col_str.strip() != ""
        ), f"{col_str=}. Must be non-empty str"
        assert (
            isinstance(table_str, str) and table_str.strip() != ""
        ), f"{table_str=}. Must be non-empty str"
        assert isinstance(where_str, str), f"{where_str=}. Must be str"
        assert isinstance(orderby_str, str), f"{orderby_str=}. Must be str"
        assert isinstance(udf_function_name, str), f"{udf_function_name=}. Must be str"
        assert isinstance(debug, bool), f"{debug=}. Must be bool"

        columns = col_str.split(",")
        tables = table_str.split(",")
        orderby = orderby_str.split(",")

        for column in columns:
            if udf_function_name in column or (
                func_name in column.lower() for func_name in SQLFUN.list()
            ):
                # Ignore user defined and SQL Lite function massaging of cols - coder knows what they are doing!:
                # TODO: Process it!
                pass
            elif SDELIM in column:  # SQL Lite Concat -
                concat_cols = column.split(SDELIM)

                for concat_col in concat_cols:
                    column_components = concat_col.split(".")
                    self._check_col(column_components, tables)
            else:
                column_components = column.split(".")
                self._check_col(column_components, tables)

        for table in tables:
            if not self.table_exists(table):
                raise ValueError(f"Table <{table}> does not exist!")

        if orderby != "":
            for column in orderby:
                if (func_name in column.lower() for func_name in SQLFUN.list()):
                    # Ignore SQL Lite function massaging of cols - coder knows what they are doing!: TODO: Process it!
                    continue

                column_components = column.split(".")
                self._check_col(column_components, tables)

        sql_statement = f"{SQL.SELECT} {col_str} " + f"{SQL.FROM} {table_str}"

        if where_str.strip() != "":
            sql_statement += f" {SQL.WHERE} {where_str} "

        if orderby_str.strip() != "":
            sql_statement += f" {SQL.ORDERBY} {orderby_str}"

        if debug and not Is_Complied():
            print(f">> {where_str=} <<")
            print(f">> {orderby_str=} <<")
            print(f">>>>>>>>>>>>>>>>>>>>>>>>> {sql_statement} <<<<<<<<<<<<<<<<")

        return self.sql_execute(sql_statement=sql_statement, debug=debug)

    def sql_update(
        self,
        col_dict: dict,
        table_str: str,
        where_str: str = "",
        transaction_commit: bool = True,
        debug: bool = False,
    ) -> tuple[int, str]:
        """Updates a table in the database - either insert or update depending on if a where clause exists.

        Args:
            col_dict (dict): A dictionary of columns/values to be updated.
            table_str (str): The table name(s) to be updated. Delimited by,
            where_str (str): Where clause of the update statement
            transaction_commit (bool): Commits the database transaction if true. Defaults to True
            debug (bool): If True, prints the SQL statement to the console. Defaults to False
        """

        assert (
            isinstance(col_dict, dict) and col_dict
        ), f"{col_dict=}. Must be non-empty dict  of column name/value pairs"
        assert (
            isinstance(table_str, str) and table_str.strip() != ""
        ), f"{table_str=}. Must be non-empty str"
        assert isinstance(where_str, str), f"{where_str=}. Must be str"

        tables = table_str.split(",")

        for table in tables:
            if not self.table_exists(table):
                raise ValueError(f"Table <{table}> does not exist!")

        column_clause = ""
        value_clause = ""

        for column, value in col_dict.items():
            if value is None:
                continue

            if (func_name in column.lower() for func_name in SQLFUN.list()):
                # Ignore SQL Lite function massaging of cols - coder knows what they are doing!: TODO: Process it!
                pass
            elif SDELIM in column:  # SQL Lite Concat -
                concat_cols = column.split(SDELIM)

                for concat_col in concat_cols:
                    column_components = concat_col.split(".")
                    self._check_col(column_components, tables)
            else:
                column_components = column.split(".")
                self._check_col(column_components, tables)

            if isinstance(value, list):
                temp_value = "'"
                for item in value:
                    temp_value += f"{item},"
                temp_value = temp_value[:-1]
                temp_value += "'"

                if where_str.strip() == "":  # Insert statement
                    value_clause += f"{temp_value} ,"
                    column_clause += f"{column} ,"
                else:  # Update statement
                    value_clause += f"{column} = {temp_value} ,"

            elif isinstance(value, (int, float)):
                if where_str.strip() == "":  # Insert statement
                    value_clause += f"{value} ,"
                    column_clause += f"{column} ,"
                else:  # Update statement
                    value_clause += f"{column} = {value} ,"
            else:
                if where_str.strip() == "":  # Insert statement
                    value_clause += f"'{value}' ,"
                    column_clause += f"{column} ,"
                else:  # Update statement
                    value_clause += f"{column} = '{value}' ,"

        column_clause = column_clause[:-1]
        value_clause = value_clause[:-1]

        if where_str.strip() == "":  # Insert statement
            sql_statement = (
                f"{SQL.INSERTINTO} {table_str} ({column_clause})"
                f" {SQL.VALUES} ({value_clause})"
            )
        else:  # Update statement
            sql_statement = f"{SQL.UPDATE} {table_str} {SQL.SET} {value_clause} {SQL.WHERE} {where_str}"

        if debug and not Is_Complied():
            print(f">>>>>>>>>>>>>>>>>>>>>>>>> {sql_statement} <<<<<<<<<<<<<<<<")
        result = self.sql_execute(sql_statement)
        error = self.get_error_status()

        if error.code == 1 and transaction_commit:
            self.sql_commit
            error = self.get_error_status()

        return error.code, error.message

    def table_cols(self, table_name: str) -> list[tuple[str, str, bool, str, int]]:
        """Returns a list of tuples defining the columns comprising a table

        Returns:
            list[tuple[str,str,bool,str,int],...]:
                List Defining Column Properties as a tuple [0] col_name,
                [1] data type [2] Col Nullable [3] Default value [4] 0 or index of PK col
        """
        assert (
            isinstance(table_name, str) and table_name.strip() != ""
        ), f"{table_name=}. Must be non-empty str"
        assert self.table_exists(
            table_name
        ), f"table <{table_name}> does not exist in database"

        cursor = self._dbconnection.execute(f"pragma table_info({table_name})")

        col_list = cursor.fetchall()

        return col_list

    def table_create(
        self,
        table_name: str,
        col_defs: list[ColDef] | tuple[ColDef, ...],
        drop_table: bool = True,
    ) -> int:
        """
        Creates a table in the database

        Args:
            table_name (str): Table name
            col_defs (list[ColDef, ...]| tuple[ColDef, ...]): list or tuple of Col_Def objects
            drop_table (bool): Drop the pre-existing table (Default True)

        Returns:
            int: 1 if table created, -1 if failed. Check error!
        """
        assert (
            isinstance(table_name, str) and table_name.strip() != ""
        ), f"{table_name=}. Must be non-empty str"
        assert isinstance(
            col_defs, (list, tuple)
        ), f"{col_defs=}. Must be list|tuple of col_defs"
        assert isinstance(drop_table, bool), f"{drop_table=}. Must be bool"

        col_list, primary_key_stmt = self._build_column_definition(col_defs)
        col_list = self._build_foreign_key_definition(col_defs, col_list)

        sql_statement = (
            f"{SQL.CREATE_TABLE} {table_name} ({col_list.strip()} "
            f"{',' + primary_key_stmt if '(' in primary_key_stmt else ''}) ;"
        )

        if drop_table:
            self.sql_execute(f"{SQL.DROP_TABLE} {SQL.IF_EXISTS} {table_name}")

            if self.get_error_status().code == -1:
                return -1

        self.sql_execute(sql_statement)

        if self.get_error_status().code == 1 and self.sql_commit == 1:
            if self.get_error_status().code == 1:
                for col_def in col_defs:
                    if col_def.index:
                        if col_def.unique:
                            sql_statement = (
                                f"{SQL.CREATE_UNIQUE_INDEX} idx_{col_def.name} {SQL.ON} "
                                f"{table_name}({col_def.name})"
                            )
                        else:
                            sql_statement = (
                                f"{SQL.CREATE_INDEX} idx_{col_def.name} {SQL.ON} "
                                f"{table_name}({col_def.name})"
                            )
                        self.sql_execute(sql_statement)

                        if self.get_error_status().code == -1 or self.sql_commit == -1:
                            return -1
                return 1

        return -1

    def _build_foreign_key_definition(self, col_defs: list[ColDef], col_list: str):
        """If the column definition has a foreign key, then add the foreign key definition to the column list

        Args:
            col_defs (list[ColDef]): A list of ColumnDef objects.
            col_list (str): This is the string that will be used to create the table.

        Returns:
            str: A string of column definitions
        """
        # Foreign Keys are set after the col_declarations are done
        for col_def in col_defs:
            if col_def.foreign_key or (
                col_def.parent_table.strip() != "" and col_def.parent_col.strip() != ""
            ):
                assert self.table_exists(col_def.parent_table), (
                    f"parent_table <{col_def.parent_table}> does not exist and"
                    + "must be created before being used in a foreign key relationship!"
                )

                assert self.col_exists(col_def.parent_table, col_def.parent_col), (
                    f"parent_col <{col_def.parent_col}> does not exist in"
                    f" parent_table<{col_def.parent_table}>"
                )

                col_list += (
                    f", {SQL.FOREIGN_KEY}({col_def.name}) {SQL.REFERENCES} "
                    + f"{col_def.parent_table}({col_def.parent_col})"
                    + f" {'ON DELETE CASCADE' if col_def.cascade_delete else ''}"
                    + f" {'ON UPDATE CASCADE' if col_def.cascaded_update else ''}"
                    + f" {'DEFERRABLE ' if col_def.deferrable else ''}"
                )

        return col_list

    @staticmethod
    def _build_column_definition(col_defs: list[ColDef]) -> tuple[str, str]:
        """Takes a list of `ColDef` objects and returns a string of column definitions for a SQL table

        Args:
            col_defs (list[ColDef]): A list of ColDef objects.

        Returns:
            str,str : A string of SQL column definitions, and the primary key definition
        """

        col_list = ""
        primary_key_statement = ""

        for col_def in col_defs:
            col_def: ColDef

            assert isinstance(col_def, ColDef), f"{col_def=}. Must be ColDef Instance"

            # Build column definition statement
            col_declaration = f"{col_def.name} "  # Name of column

            # Bools are ints in sqllite, so check is a good idea
            match col_def.data_type:
                case str(SQL.BOOLEAN) | str(SQL.INTEGER):
                    col_declaration += f"{SQL.INTEGER} "

                    if col_def.data_type == SQL.BOOLEAN:
                        col_declaration += (
                            f"{SQL.CHECK}({SQL.INTEGER} >= 0 AND {col_def.name} <= 1 )"
                        )
                case str(SQL.VARCHAR):
                    col_declaration += f"{col_def.data_type}({col_def.size}) "

                    # Does a length check - good if moved to another SQL database engine
                    col_declaration += (
                        f"{SQL.CHECK}(length({col_def.name}) <= {col_def.size})"
                    )
                case str(SQL.DECIMAL):
                    col_declaration += (
                        f"{col_def.data_type}({col_def.size},{col_def.num_decs})"
                    )
                case _:
                    col_declaration += f"{col_def.data_type}"

            if col_def.primary_key:
                col_declaration += f" {SQL.NOT_NULL} "

            if col_def.primary_key and primary_key_statement == "":
                pk_defs = [pk_def for pk_def in col_defs if pk_def.primary_key]
                pk_count = len(pk_defs)

                if col_def.data_type == SQL.INTEGER and pk_count == 1:
                    primary_key_statement = f" {SQL.PRIMARY_KEY} {SQL.AUTOINCREMENT}"
                else:
                    temp = ""
                    for pk_def in pk_defs:
                        temp += f"{pk_def.name},"
                    temp = temp[:-1]

                    primary_key_statement = f"{SQL.PRIMARY_KEY}({temp})"

            col_list += (
                f"{col_declaration} "
                f"{primary_key_statement if col_def.primary_key and '(' not in primary_key_statement else ''} "
                f"{SQL.UNIQUE if not col_def.primary_key and col_def.unique else ''} ,"
            )

        if col_list.endswith(","):  # Remove trailing comma
            col_list = col_list[:-1]

        return col_list, primary_key_statement

    def col_exists(self, table_name: str, column_name: str) -> bool:
        """Checks if a column exists on a given table

        Args:
            table_name (str): Table name
            column_name (str): Column name

        Returns:
            bool: True if column exists, False if it does not exist

        """
        assert (
            isinstance(table_name, str) and table_name.strip() != ""
        ), f"{table_name=}. Must be non-empty str"
        assert (
            isinstance(column_name, str) and column_name.strip() != ""
        ), f"{column_name=}. Must be non-empty str"

        if self.table_exists(table_name):
            sql_statement = (
                f"{SQL.SELECT} {SQL.COUNT}(*) AS CNTCOL {SQL.FROM} "
                + f"{PRAGMA.TABLE_INFO}('{table_name.strip()}')"
                f" {SQL.WHERE} name='{column_name.strip()}'"
            )

            column_result = self.sql_execute(sql_statement)

            if self.get_error_status().code == 1:
                if column_result[0][0] > 0:
                    return True

        return False

    def table_exists(self, table_name: str) -> bool:
        """Checks if the given table exists in the database

        Args:
            table_name (str): Database table name

        Returns:
            bool: True if table exists, False if table does not exist
        """
        assert (
            isinstance(table_name, str) and table_name.strip() != ""
        ), f"{table_name=}. Must be non-empty str"

        sql_statement = (
            f"{SQL.SELECT} name {SQL.FROM} {SYSDEF.SQLMASTERTABLE} "
            + f"{SQL.WHERE} type = 'table' {SQL.AND} name = '{table_name.strip()}';"
        )

        table_result = self.sql_execute(sql_statement)

        if self.get_error_status().code == 1:
            if len(table_result) > 0:
                return True
        return False

    def _convert_from_base(self, value: int) -> Decimal:
        """
        Converts an int value from the base value - most likely used with Currency Conversion,
        e.g., Integer 1234 will be converted to Decimal('12.34')

        Args:
            value (int): Base value

        Returns:
            int| float: Converted int value to decimal
        """
        assert isinstance(value, int), f"{value=}. Must be int"

        return Decimal(value) / self._multiplier_int

    def _convert_to_base(self, value: NUMBER) -> int:
        """
        Coverts a numeric value to a base value - most likely used with Currency Conversion
        e.g. value = Column(Sqlite Decimal(2)) means a value such as
        Decimal('12.34') will be converted to 1234

        Args:
            value (NUMBER): Numeric value to be converted

        Returns:
            int: The converted value
        """
        assert isinstance(value, (int, float)), f"{value=}. Must be int|float"

        return int(Decimal(value) * self._multiplier_int)

    def _error_message(self, title: str, message: str, fatal: bool = True) -> int:
        """Packages an _error message into the correct instance variables
        Args:
            title (str): Title of error message
            message (str): Text of error message
            fatal (bool): True if _error message fatal otherwise False

        Returns:
            int: 1 if not fatal otherwise raises a value _error halting app execution and displays an _error message
        """
        assert (
            isinstance(title, str) and title.strip() != ""
        ), f"{title=}. Must be non-empty str"
        assert (
            isinstance(message, str) and message.strip() != ""
        ), f"{message=}. Must be non-empty str"
        assert isinstance(fatal, bool), f"{fatal=}. Must be bool"

        self._error_txt = message

        if fatal:
            raise ValueError(message)

        return 1

    def add_func(self, func: Callable, num_args: int, func_name: str) -> None:
        """Adds a function to the database instance

        Args:
            func (Callable): Func|Method|Lambda etc. reference
            num_args (int): Number of arguments
            func_name (str): Name of function
        """
        assert isinstance(func, Callable), f"{func=}. Must be Func|Method|Lambda etc."
        assert (
            isinstance(num_args, int) and num_args >= 0
        ), f"{num_args=}. Must be the number of args to the func"
        assert (
            isinstance(func_name, str) and func_name.strip() != ""
        ), f"{func_name=}. Must be str and the name of the func"

        self._dbconnection.create_function(func_name, num_args, func)

    @property
    def get_connection(self) -> Connection:
        """Gets the database connection

        Returns:
            Connection : Database connection

        """
        return self._dbconnection

    def get_error_status(self) -> Error:
        """
        Return _error code and text in a tuple

        :return: (Error): code =  1 if ok, -1 if _error message = _error text
        """

        error = Error()
        error.code = self._error
        error.message = self._error_txt

        return error
