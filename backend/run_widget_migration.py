"""
Run widget embed migration.

Adds 4 new columns to the chatbots table:
  - embed_key   (UUID, unique) — used in the public embed script URL
  - widget_color
  - widget_welcome_message
  - widget_position

Also auto-generates an embed_key for any existing chatbots that don't have one.
"""

import psycopg2
from dotenv import load_dotenv
import os
import sys
import uuid
from pathlib import Path


def main():
    print("=" * 60)
    print("Running Widget Embed Migration")
    print("=" * 60)

    load_dotenv()
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("❌ DATABASE_URL is not set in .env file")
        return False

    # Parse postgresql://user:password@host:port/database
    url_parts = DATABASE_URL.replace("postgresql://", "").split("@")
    user_pass = url_parts[0].split(":")
    host_port_db = url_parts[1].split("/")
    host_port = host_port_db[0].split(":")

    conn_params = {
        "user": user_pass[0],
        "password": user_pass[1],
        "host": host_port[0],
        "port": host_port[1],
        "database": host_port_db[1],
    }

    print(f"\n📁 Database: {conn_params['host']}:{conn_params['port']}/{conn_params['database']}")
    print("\n🔄 Connecting to database...")

    try:
        conn = psycopg2.connect(**conn_params)
        conn.autocommit = False
        cursor = conn.cursor()
        print("✅ Connected successfully!")

        # Add columns (IF NOT EXISTS so idempotent)
        migrations = [
            ("embed_key",             "ALTER TABLE chatbots ADD COLUMN IF NOT EXISTS embed_key VARCHAR UNIQUE;"),
            ("widget_color",          "ALTER TABLE chatbots ADD COLUMN IF NOT EXISTS widget_color VARCHAR NOT NULL DEFAULT '#2563EB';"),
            ("widget_welcome_message","ALTER TABLE chatbots ADD COLUMN IF NOT EXISTS widget_welcome_message VARCHAR NOT NULL DEFAULT 'Hi! How can I help you?';"),
            ("widget_position",       "ALTER TABLE chatbots ADD COLUMN IF NOT EXISTS widget_position VARCHAR NOT NULL DEFAULT 'bottom-right';"),
        ]

        for label, sql in migrations:
            print(f"\n🔄 Adding column: {label}")
            cursor.execute(sql)
            print(f"   ✅ Done")

        # Create index on embed_key
        print("\n🔄 Creating index on embed_key (if not exists)...")
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE tablename = 'chatbots' AND indexname = 'ix_chatbots_embed_key'
                ) THEN
                    CREATE INDEX ix_chatbots_embed_key ON chatbots(embed_key);
                END IF;
            END$$;
        """)
        print("   ✅ Done")

        # Back-fill embed_key for existing chatbots that have NULL
        print("\n🔄 Back-filling embed_key for existing chatbots...")
        cursor.execute("SELECT id FROM chatbots WHERE embed_key IS NULL;")
        rows = cursor.fetchall()
        for (chatbot_id,) in rows:
            new_key = str(uuid.uuid4())
            cursor.execute("UPDATE chatbots SET embed_key = %s WHERE id = %s;", (new_key, chatbot_id))
            print(f"   ✅ Chatbot {chatbot_id} → embed_key={new_key}")

        if not rows:
            print("   ✅ All chatbots already have an embed_key")

        conn.commit()
        print("\n✅ Migration completed successfully!")
        print("\nChanges applied:")
        print("  - Added 'embed_key' column (UUID, unique, indexed)")
        print("  - Added 'widget_color' column (default: #2563EB)")
        print("  - Added 'widget_welcome_message' column")
        print("  - Added 'widget_position' column (default: bottom-right)")
        print("  - Back-filled embed_key for existing chatbots")
        print("\n📝 Next steps:")
        print("  1. Start backend: uvicorn app.main:app --reload")
        print("  2. GET /chatbots → each chatbot now has an embed_key")
        print("  3. GET /widget/{embed_key}.js → returns the embed script")

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        print(f"\n❌ Migration failed: {e}")
        if "already exists" in str(e):
            print("\n⚠️  Some columns already exist — migration may have been run before.")
            print("This is OK — you can proceed.")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return True
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
