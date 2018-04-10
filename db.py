import sqlite3
from sqlite3 import Error

def create_db_connection(db_file):
    try:
        global conn
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)

def close_db_connection():
    conn.close()

def commit_db_connection():
    conn.commit()

def drop_db_table(tablename):
    conn.execute('DROP TABLE IF EXISTS {tn}'.format(tn=tablename))

def create_db_table(tablename,dbcolumns):
    query = 'CREATE table IF NOT EXISTS {0} ({1} text)'
    query = query.format(tablename," text, ".join(dbcolumns))
    conn.execute(query)

def insert_db_table(tablename,query,values):
#    conn.execute(query,"','".join(values))
     dbvalues='"'+'","'.join(values)+'"'
#     print(dbvalues)
     conn.execute(query,values)
def read_db_table(query):
    return conn.execute(query)
