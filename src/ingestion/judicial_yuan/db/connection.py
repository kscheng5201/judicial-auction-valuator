import os
from contextlib import contextmanager

import pymysql
import pymysql.cursors
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("JUDICIAL_YUAN_DB_HOST", "localhost")
DB_PORT = int(os.getenv("JUDICIAL_YUAN_DB_PORT", "3306"))
DB_USER = os.getenv("JUDICIAL_YUAN_DB_USER", "root")
DB_PASS = os.getenv("JUDICIAL_YUAN_DB_PASS", "")
DB_NAME = os.getenv("JUDICIAL_YUAN_DB_NAME", "judicial_auctions")


def _connect():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


@contextmanager
def get_cursor():
    conn = _connect()
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
