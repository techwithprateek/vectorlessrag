"""
app/retriever.py
----------------
Step 2 of the RAG pipeline: Database Retrieval.

Takes the structured query dict from app/decomposer.py and runs a hybrid
PostgreSQL query that combines:
  - SQL WHERE filters (category, price range, rating, stock status)
  - Full-text search (tsvector @@ tsquery) for keyword matching

No vector embeddings are used. PostgreSQL's built-in tsvector/tsquery gives
us keyword-based relevance ranking (ts_rank) that's fast and accurate enough
for e-commerce product search.
"""

import psycopg2
import psycopg2.extras
import config


def retrieve(structured_query: dict, top_k: int = 5) -> list[dict]:
    """
    Runs a hybrid SQL query (filters + optional full-text search).
    Returns up to top_k product dicts.

    Args:
        structured_query: Dict from decompose_query() with keys:
            category, keywords, price_min, price_max, min_rating,
            in_stock_only, attributes.
        top_k: Maximum number of products to return. Default is 5.

    Returns:
        A list of product dicts (plain Python dicts, JSON-safe).
        Each dict matches the columns of the products table.
    """
    # Connect to PostgreSQL using the URL from config
    conn = psycopg2.connect(config.DATABASE_URL)
    # RealDictCursor returns rows as dicts instead of tuples, column names as keys
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # --- Step 1: Merge keywords and attributes into one FTS search string ---
        keywords = structured_query.get("keywords", "") or ""
        # attributes is a list like ["waterproof", "bass"] — join into a string
        attributes = " ".join(structured_query.get("attributes", []) or [])
        # Combine both for a richer full-text search
        all_terms = f"{keywords} {attributes}".strip()

        # --- Step 2: Build dynamic WHERE clause ---
        # Start with "1=1" so the clause is always syntactically valid
        # even if no filters are applied
        conditions = ["1=1"]
        params = []  # positional params for %s placeholders in psycopg2

        # Category: partial match (ILIKE) so "speaker" matches "bluetooth speaker"
        category = structured_query.get("category")
        if category:
            conditions.append("category ILIKE %s")
            params.append(f"%{category}%")

        # Price ceiling filter
        price_max = structured_query.get("price_max")
        if price_max is not None:
            conditions.append("price <= %s")
            params.append(price_max)

        # Price floor filter
        price_min = structured_query.get("price_min")
        if price_min is not None:
            conditions.append("price >= %s")
            params.append(price_min)

        # Minimum rating filter
        min_rating = structured_query.get("min_rating")
        if min_rating is not None:
            conditions.append("rating >= %s")
            params.append(min_rating)

        # Stock filter: only show available products if requested
        if structured_query.get("in_stock_only"):
            conditions.append("in_stock = true")  # no param needed — it's a literal

        # --- Step 3: Full-text search condition ---
        # Use plainto_tsquery for raw user text so hyphenated/quoted input
        # is parsed safely instead of raising tsquery syntax errors.
        if all_terms:
            # search_vector is a pre-built tsvector column; @@ tests if it matches
            conditions.append("search_vector @@ plainto_tsquery('english', %s)")
            params.append(all_terms)
            # ts_rank scores how well the document matches the query (higher = better)
            order_clause = "ORDER BY ts_rank(search_vector, plainto_tsquery('english', %s)) DESC, rating DESC"
            # Pass the same plain-text search string again for ranking
            order_params = [all_terms]
        else:
            # No keywords? Fall back to sorting by rating alone
            order_clause = "ORDER BY rating DESC"
            order_params = []

        # --- Step 4: Assemble and execute the full query ---
        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT id, name, brand, category, price, rating,
                   in_stock, tags, description
            FROM products
            WHERE {where_clause}
            {order_clause}
            LIMIT %s
        """
        # Final params: WHERE params + ORDER BY params + LIMIT value
        all_params = params + order_params + [top_k]

        cursor.execute(sql, all_params)
        results = cursor.fetchall()

        # Convert RealDictRow objects to plain Python dicts for JSON safety
        return [dict(row) for row in results]

    finally:
        # Always close the cursor and connection, even if an exception occurred
        cursor.close()
        conn.close()
