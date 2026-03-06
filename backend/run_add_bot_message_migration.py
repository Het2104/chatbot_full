"""
Migration: Add bot_message column to nodes table.

Run this script once to add the bot_message column to existing databases.
Safe to run multiple times – it checks if the column already exists first.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from database import engine


def run():
    with engine.connect() as conn:
        # Check if column already exists
        result = conn.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name='nodes' AND column_name='bot_message'")
        )
        if result.fetchone():
            print("✅ Column 'bot_message' already exists – nothing to do.")
            return

        conn.execute(text("ALTER TABLE nodes ADD COLUMN bot_message VARCHAR"))
        conn.commit()
        print("✅ Successfully added 'bot_message' column to 'nodes' table.")


if __name__ == "__main__":
    run()
