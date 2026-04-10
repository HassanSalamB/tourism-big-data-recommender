import psycopg2

def get_connection():
    return psycopg2.connect(
        dbname="tourism",
        user="postgres",
        password="your password",  #change this
        host="localhost",
        port="5432"
    )