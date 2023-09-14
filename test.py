import sqlite3 as pysqlite3

if __name__ == "__main__":
    _dbconnection = pysqlite3.dbapi2.connect(
        "./test.db",
        detect_types=1,  # PARSE_DECLTYPES = 1
    )
    _dbconnection.execute("pragma foreign_keys = ON")
    _dbconnection.execute("'CREATE TABLE test")

    _dbconnection.execute(
        f"SELECT name FROM SQLMASTERTABLE " + f"WHERE type = 'table' AND name = 'test';"
    )

    print("Test")
