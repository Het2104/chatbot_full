"""
Run authentication migration.

This script runs the 008_add_users_table.sql migration to set up
the authentication system database tables.
"""

import psycopg2
from dotenv import load_dotenv
import os
import sys
from pathlib import Path

def main():
    """Run the authentication migration."""
    
    print("=" * 60)
    print("Running Authentication Migration (008_add_users_table.sql)")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv()
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL is not set in .env file")
        return False
    
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
    
    migration_file = Path(__file__).parent / "migrations" / "008_add_users_table.sql"
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    print(f"\n📁 Database: {conn_params['host']}:{conn_params['port']}/{conn_params['database']}")
    print(f"📁 Migration file: {migration_file.name}")
    print("\n🔄 Connecting to database...")
    
    try:
        # Connect to the database
        conn = psycopg2.connect(**conn_params)
        conn.autocommit = False
        cursor = conn.cursor()
        
        print("✅ Connected successfully!")
        print("\n🔄 Running migration...")
        
        # Read and execute the migration file
        with open(migration_file, 'r') as f:
            sql = f.read()
        
        cursor.execute(sql)
        conn.commit()
        
        print("\n✅ Migration completed successfully!")
        print("\nChanges applied:")
        print("  - Created 'users' table")
        print("  - Added 'user_id' foreign key to 'chatbots' table")
        print("  - Added 'user_id' foreign key to 'chat_sessions' table")
        print("  - Created indexes for faster lookups")
        print("\n📝 Next steps:")
        print("  1. Run: python create_admin.py (to create admin user)")
        print("  2. Start backend: uvicorn app.main:app --reload")
        print("  3. Test: python test_auth.py")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.Error as e:
        print(f"\n❌ Migration failed: {e}")
        
        # Check if error is because tables already exist
        if "already exists" in str(e):
            print("\n⚠️  Tables already exist - migration may have been run before.")
            print("This is OK - you can proceed to next steps.")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return True
        
        print("\nTroubleshooting:")
        print("  - Check DATABASE_URL in .env file")
        print("  - Ensure PostgreSQL is running")
        print("  - Verify you have database permissions")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
