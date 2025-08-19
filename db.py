# db.py

import mysql.connector
from mysql.connector import Error

def get_db_connection():
    """
    Cria e retorna uma conexão com o banco de dados MySQL.
    Certifique-se de que o XAMPP esteja rodando e que o banco exista.
    """
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',  # padrão do XAMPP
            database='recrutamentodb',
            connection_timeout=60
        )
        return conn
    except Error as e:
        print(f"[ERRO] Falha ao conectar no banco de dados: {e}")
        return None
