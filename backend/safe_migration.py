"""Safe migration that handles existing data"""
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

# Parse the DATABASE_URL
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
    conn = psycopg2.connect(**conn_params)
    conn.autocommit = False
    cursor = conn.cursor()
    
    print("Connected successfully!\n")
    
    # Step 1: Add new columns
    print("Step 1: Adding new columns...")
    cursor.execute("ALTER TABLE nodes ADD COLUMN IF NOT EXISTS node_type VARCHAR;")
    cursor.execute("ALTER TABLE nodes ADD COLUMN IF NOT EXISTS text VARCHAR;")
    print("✓ New columns added\n")
    
    # Step 2: Migrate data from input nodes (set node_type and text from input_text)
    print("Step 2: Migrating input nodes...")
    cursor.execute("""
        UPDATE nodes
        SET node_type = 'input',
            text = COALESCE(input_text, '')
        WHERE (node_type IS NULL OR node_type = '') 
        AND input_text IS NOT NULL
        AND input_text != '';
    """)
    rows_updated = cursor.rowcount
    print(f"✓ Updated {rows_updated} input nodes\n")
    
    # Step 3: Create edges table if it doesn't exist
    print("Step 3: Creating edges table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS edges (
            id SERIAL PRIMARY KEY,
            workflow_id INTEGER NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
            from_node_id INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
            to_node_id INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT uq_edge_from_node UNIQUE (from_node_id),
            CONSTRAINT uq_edge_to_node UNIQUE (to_node_id)
        );
    """)
    print("✓ Edges table created\n")
    
    # Step 4: Create output nodes for each input node that has output_text
    print("Step 4: Creating output nodes...")
    cursor.execute("""
        INSERT INTO nodes (workflow_id, node_type, text, created_at)
        SELECT workflow_id, 'output', COALESCE(output_text, ''), created_at
        FROM nodes
        WHERE node_type = 'input'
          AND output_text IS NOT NULL
          AND output_text != ''
          AND NOT EXISTS (
              SELECT 1 FROM nodes n2 
              WHERE n2.workflow_id = nodes.workflow_id 
              AND n2.node_type = 'output'
          )
        ON CONFLICT DO NOTHING;
    """)
    output_nodes_created = cursor.rowcount
    print(f"✓ Created {output_nodes_created} output nodes\n")
    
    # Step 5: Create edges connecting input to output nodes
    print("Step 5: Creating edges...")
    cursor.execute("""
        INSERT INTO edges (workflow_id, from_node_id, to_node_id)
        SELECT DISTINCT i.workflow_id, i.id, o.id
        FROM nodes i
        JOIN nodes o ON o.workflow_id = i.workflow_id AND o.node_type = 'output'
        WHERE i.node_type = 'input'
          AND i.output_text IS NOT NULL
          AND i.output_text != ''
        ON CONFLICT DO NOTHING;
    """)
    edges_created = cursor.rowcount
    print(f"✓ Created {edges_created} edges\n")
    
    # Step 6: Handle any remaining NULL values
    print("Step 6: Cleaning up NULL values...")
    cursor.execute("UPDATE nodes SET node_type = 'input' WHERE node_type IS NULL OR node_type = '';")
    cursor.execute("UPDATE nodes SET text = '' WHERE text IS NULL;")
    print("✓ NULL values cleaned\n")
    
    # Step 7: Drop old columns
    print("Step 7: Dropping old columns...")
    cursor.execute("ALTER TABLE nodes DROP COLUMN IF EXISTS input_text;")
    cursor.execute("ALTER TABLE nodes DROP COLUMN IF EXISTS output_text;")
    print("✓ Old columns dropped\n")
    
    # Step 8: Set NOT NULL constraints
    print("Step 8: Setting NOT NULL constraints...")
    cursor.execute("ALTER TABLE nodes ALTER COLUMN node_type SET NOT NULL;")
    cursor.execute("ALTER TABLE nodes ALTER COLUMN text SET NOT NULL;")
    print("✓ Constraints set\n")
    
    # Commit all changes
    conn.commit()
    print("=" * 50)
    print("✅ Migration completed successfully!")
    print("=" * 50)
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    if 'conn' in locals():
        conn.rollback()
        conn.close()
    raise
