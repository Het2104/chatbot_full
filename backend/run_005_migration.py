"""
Apply migration 005: Make workflow_id nullable in chat_sessions
"""
import psycopg2
from urllib.parse import urlparse
from app.config import DATABASE_URL
from app.logging_config import get_logger

logger = get_logger(__name__)


def run_migration():
    """Apply the migration"""
    conn = None
    try:
        # Parse DATABASE_URL to get connection parameters
        url = urlparse(DATABASE_URL)
        
        # Connect to database
        conn = psycopg2.connect(
            host=url.hostname,
            port=url.port,
            database=url.path[1:],  # Remove leading slash
            user=url.username,
            password=url.password
        )
        conn.autocommit = False
        cursor = conn.cursor()
        
        logger.info("Starting migration 005: Make workflow_id nullable")
        print("Applying migration 005: Make workflow_id nullable in chat_sessions...")
        
        # Read and execute migration file
        with open('migrations/005_make_workflow_id_nullable.sql', 'r') as f:
            sql = f.read()
            
        cursor.execute(sql)
        conn.commit()
        
        logger.info("Migration 005 completed successfully")
        print("✓ Migration completed successfully")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        print(f"✗ Migration failed: {e}")
        if conn:
            conn.rollback()
            conn.close()
        raise


if __name__ == "__main__":
    run_migration()
