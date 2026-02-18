"""Run database migrations"""
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

# Parse the DATABASE_URL
# Format: postgresql://user:password@host:port/database
url_parts = DATABASE_URL.replace("postgresql://", "").split("@")
user_pass = url_parts[0].split(":")
host_port_db = url_parts[1].split("/")
host_port = host_port_db[0].split(":")

conn_params = {
    "user": user_pass[0],
    "password": user_pass[1],
    "host": host_port[0],
    "port": host_port[1],
    "database": host_port_db[1]
}

print(f"Connecting to database: {conn_params['host']}:{conn_params['port']}/{conn_params['database']}")

try:
    # Connect to the database
    conn = psycopg2.connect(**conn_params)
    conn.autocommit = False
    cursor = conn.cursor()
    
    print("Connected successfully!")
    
    # Read and execute the migration file
    migration_file = "migrations/001_split_nodes_edges.sql"
    print(f"\nRunning migration: {migration_file}")
    
    with open(migration_file, 'r') as f:
        sql = f.read()
    
    cursor.execute(sql)
    conn.commit()
    
    print("Migration completed successfully!")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    if 'conn' in locals():
        conn.rollback()
        conn.close()
    raise
