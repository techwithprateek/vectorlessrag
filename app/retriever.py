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

        # --- Step 2: Build filters as (tag, sql_snippet, param_or_None) triples ---
        # Using triples lets us easily drop individual filters (e.g. category)
        # without misaligning positional params later.
        category = structured_query.get("category")
        price_max = structured_query.get("price_max")
        price_min = structured_query.get("price_min")
        min_rating = structured_query.get("min_rating")

        # Each entry: (tag, condition_sql, param_value | None)
        # tag is used to identify which filter to drop in fallback attempts
        filter_specs = [("base", "1=1", None)]
        if category:
            filter_specs.append(("category", "category ILIKE %s", f"%{category}%"))
        if price_max is not None:
            filter_specs.append(("price_max", "price <= %s", price_max))
        if price_min is not None:
            filter_specs.append(("price_min", "price >= %s", price_min))
        if min_rating is not None:
            filter_specs.append(("rating", "rating >= %s", min_rating))
        if structured_query.get("in_stock_only"):
            filter_specs.append(("stock", "in_stock = true", None))

        def build_query(specs, include_fts: bool):
            """Assemble conditions + params from a list of filter specs.

            Args:
                specs: List of (tag, sql, param_or_None) triples.
                include_fts: If True, appends the FTS condition on all_terms.

            Returns:
                (conditions_list, params_list, order_clause, order_params_list)
            """
            conds = [sql for _, sql, _ in specs]
            prms  = [p   for _, _,   p in specs if p is not None]
            if include_fts and all_terms:
                conds.append("search_vector @@ plainto_tsquery('english', %s)")
                prms.append(all_terms)
                order = "ORDER BY ts_rank(search_vector, plainto_tsquery('english', %s)) DESC, rating DESC"
                ord_p = [all_terms]
            else:
                order = "ORDER BY rating DESC"
                ord_p = []
            return conds, prms, order, ord_p

        def run_query(conds, qparams, order, order_params):
            """Execute the assembled SQL and return rows as plain dicts."""
            where = " AND ".join(conds)
            sql = f"""
                SELECT id, name, brand, category, price, rating,
                       in_stock, tags, description
                FROM products
                WHERE {where}
                {order}
                LIMIT %s
            """
            cursor.execute(sql, qparams + order_params + [top_k])
            return [dict(row) for row in cursor.fetchall()]

        # --- Step 3: Try queries in order of strictness, falling back on each miss ---

        # Attempt 1: all SQL filters + FTS
        conds, prms, order, ord_p = build_query(filter_specs, include_fts=True)
        results = run_query(conds, prms, order, ord_p)

        if not results and all_terms:
            # FTS terms not found in search_vector (e.g. LLM included adjectives
            # like "good" that aren't indexed). Drop FTS, keep SQL filters.
            print("[retriever] FTS returned 0 — retrying with SQL filters only.")
            conds, prms, order, ord_p = build_query(filter_specs, include_fts=False)
            results = run_query(conds, prms, order, ord_p)

        if not results and category:
            # Category label from LLM doesn't match catalog (e.g. "earphones" vs
            # "headphones"). Drop category filter and retry with FTS + other filters.
            print("[retriever] Category filter matched nothing — dropping category and retrying.")
            no_cat = [s for s in filter_specs if s[0] != "category"]
            conds, prms, order, ord_p = build_query(no_cat, include_fts=bool(all_terms))
            results = run_query(conds, prms, order, ord_p)
            if not results and all_terms:
                # Still nothing — also drop FTS
                conds, prms, order, ord_p = build_query(no_cat, include_fts=False)
                results = run_query(conds, prms, order, ord_p)

        return results

    finally:
        # Always close the cursor and connection, even if an exception occurred
        cursor.close()
        conn.close()
