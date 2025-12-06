import pymysql

def get_connection():
    return pymysql.connect(
        host='127.0.0.1',
        user='root',
        password='apple@sql',
        database='immunibuddy',
        cursorclass=pymysql.cursors.DictCursor
    )
