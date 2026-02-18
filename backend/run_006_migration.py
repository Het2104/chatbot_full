"""
Apply migration 006: Update edge constraints to allow branching
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
        
        logger.info("Starting migration 006: Update edge constraints")
        print("Applying migration 006: Update edge constraints to allow branching...")
        
        # Read and execute migration file
        with open('migrations/006_update_edge_constraints.sql', 'r') as f:
            sql = f.read()
            
        cursor.execute(sql)
        conn.commit()
        
        logger.info("Migration 006 completed successfully")
        print("✓ Migration completed successfully")
        print("  - Dropped: uq_edge_from_node constraint")
        print("  - Dropped: uq_edge_to_node constraint")
        print("  - Added: uq_edge_from_to constraint")
        print("  - Nodes can now have multiple outgoing and incoming edges!")
        
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
