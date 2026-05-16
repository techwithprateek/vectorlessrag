"""
db/seed.py
----------
Seeds the products table with a sample catalog of 10 products across 4 categories.

Run once after db/setup.py:
    python db/seed.py

Skips products that already exist (idempotent).
"""

import psycopg2
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Sample product catalog: (name, brand, category, price, rating, in_stock, tags_list, description)
PRODUCTS = [
    ("boAt Stone 1200",        "boAt",      "bluetooth speaker",   2499, 4.3, True,
     ["waterproof","outdoor","bass","portable"],
     "Powerful 40W outdoor speaker with deep bass and IPX7 waterproof rating. 12hr battery."),

    ("JBL Flip 6",             "JBL",       "bluetooth speaker",   7999, 4.6, True,
     ["waterproof","portable","premium","outdoor"],
     "Premium portable speaker with JBL Pro Sound, IP67 waterproof, 12hr playtime."),

    ("Zebronics Zeb-Bellow",   "Zebronics", "bluetooth speaker",    899, 3.8, True,
     ["budget","portable","bass"],
     "Budget-friendly portable speaker with decent bass. Best for indoor casual use."),

    ("Sony SRS-XB23",          "Sony",      "bluetooth speaker",   5999, 4.5, True,
     ["waterproof","bass","outdoor","portable","extra-bass"],
     "Sony Extra Bass speaker with IP67 waterproof, 12hr battery and vivid lights."),

    ("Apple AirPods Pro",      "Apple",     "headphones",         24900, 4.7, True,
     ["wireless","noise-cancelling","premium","earbuds"],
     "Active noise cancellation, transparency mode, spatial audio. H2 chip."),

    ("boAt Rockerz 450",       "boAt",      "headphones",          1299, 4.1, True,
     ["wireless","budget","over-ear","bass"],
     "Over-ear wireless headphones with 15hr battery and powerful bass drivers."),

    ("Sony WH-1000XM5",        "Sony",      "headphones",         28990, 4.8, False,
     ["wireless","noise-cancelling","premium","over-ear"],
     "Industry-leading noise cancellation, 30hr battery, multipoint connection."),

    ("Realme Buds Wireless 2", "Realme",    "headphones",          1499, 4.0, True,
     ["wireless","budget","neckband","bass"],
     "Neckband earphones with magnetic clasp, bass boost, 17hr battery."),

    ("Logitech MK345",         "Logitech",  "keyboard mouse combo",1995, 4.2, True,
     ["wireless","combo","office","ergonomic"],
     "Wireless keyboard and mouse combo. Comfortable full-size keyboard with number pad."),

    ("Mi Smart Band 7",        "Xiaomi",    "fitness band",        2799, 4.3, True,
     ["fitness","waterproof","heart-rate","budget","smartband"],
     "1.62 inch AMOLED display, SpO2 monitoring, 14-day battery, 110 workout modes."),
]


def seed_products():
    """
    Inserts sample products into the products table.
    Skips any product whose name already exists (ON CONFLICT DO NOTHING).
    """
    conn = psycopg2.connect(config.DATABASE_URL)
    cursor = conn.cursor()

    try:
        inserted = 0
        for name, brand, category, price, rating, in_stock, tags, description in PRODUCTS:
            # Build search_vector inline using PostgreSQL's to_tsvector function.
            # We concatenate name + description + tags (as space-separated string)
            # so the FTS index covers all searchable text for this product.
            # 'english' config applies stemming (run→running) and stop-word removal.
            cursor.execute("""
                INSERT INTO products
                    (name, brand, category, price, rating, in_stock, tags, description, search_vector)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                    to_tsvector('english', %s || ' ' || %s || ' ' || array_to_string(%s::text[], ' '))
                )
                ON CONFLICT (name) DO NOTHING
            """, (
                name, brand, category, price, rating, in_stock, tags, description,
                # Three values for the to_tsvector concat: name, description, tags array
                name, description, tags
            ))
            # rowcount is 1 if inserted, 0 if skipped due to conflict
            if cursor.rowcount > 0:
                inserted += 1

        conn.commit()
        print(f"✅ Seeded {inserted} products.")

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    seed_products()
