
# per mio pc
'''
import psycopg2

DB_CONFIG = {
    "dbname": "ristorante",
    "user": "postgres",
    "password": "1234",   
    "host": "localhost",
    "port": "5432"
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)
    
'''

import psycopg2
import os

def get_connection():
    return psycopg2.connect(
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT")
    )
