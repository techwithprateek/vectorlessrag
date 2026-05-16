"""
db/setup.py
-----------
One-time database setup script. Creates the products table and all indexes.

Run once before using the application:
    python db/setup.py

Uses config.DATABASE_URL to connect to PostgreSQL.
"""

import psycopg2
import sys
import os

# Allow imports from the project root (for config.py)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def setup_database():
    """
    Creates the products table and required indexes in PostgreSQL.
    Safe to run multiple times — uses IF NOT EXISTS.
    """
    conn = psycopg2.connect(config.DATABASE_URL)
    cursor = conn.cursor()

    try:
        # Create the products table
        # search_vector is a TSVECTOR column: a pre-processed, indexed representation
        # of the text (name + description + tags) optimized for full-text search.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                brand TEXT,
                category TEXT,
                price NUMERIC,
                rating NUMERIC,
                in_stock BOOLEAN DEFAULT true,
                tags TEXT[],
                description TEXT,
                search_vector TSVECTOR
            );
        """)

        # GIN index on search_vector: GIN (Generalized Inverted Index) is the standard
        # index type for tsvector columns — it inverts the index so each word maps
        # to the rows that contain it, enabling fast keyword lookups.
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fts ON products USING GIN(search_vector);
        """)

        # B-tree indexes on filter columns for fast WHERE clause evaluation
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON products(category);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price ON products(price);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rating ON products(rating);")

        conn.commit()
        print("✅ Database setup complete.")

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    setup_database()
