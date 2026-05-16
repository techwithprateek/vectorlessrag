"""
streamlit_app.py
----------------
Main entry point for the ShopSense application.

Run with:
    streamlit run streamlit_app.py

This file wires together the three pipeline steps:
    1. decompose_query()  — parse natural language → structured filters
    2. retrieve()         — query PostgreSQL with those filters
    3. generate_answer()  — LLM writes a recommendation from results

The UI has a sidebar for settings and example queries, and a tabbed main area
showing the final answer, the decomposed query JSON, and raw product cards.
"""

import streamlit as st

# Must be the very first Streamlit call — sets page title, icon, and layout
st.set_page_config(page_title="ShopSense", page_icon="🛍️", layout="wide")

import config
from app.decomposer import decompose_query
from app.retriever import retrieve
from app.rag import generate_answer

# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ Settings")

    # Show which LLM provider is currently active
    st.info(f"LLM: {config.LLM_PROVIDER}")

    # Slider to control how many products the retriever fetches
    top_k = st.slider("Max products to retrieve", min_value=1, max_value=10, value=5)

    st.divider()

    st.subheader("💡 Example queries")

    # Pre-canned queries — clicking one sets the session_state query variable,
    # which pre-fills the text input in the main area
    example_queries = [
        "waterproof bluetooth speaker under ₹2500 with good bass",
        "wireless noise cancelling headphones premium quality",
        "budget wireless earphones under 1500 rupees",
        "fitness band with heart rate monitoring under 3000",
    ]

    for example in example_queries:
        # Each button click writes directly into the text input's own session-state
        # key so Streamlit updates the widget regardless of prior user input.
        if st.button(example, use_container_width=True):
            st.session_state["query_input"] = example
            st.rerun()

# --- Main area ---
st.title("🛍️ ShopSense")
st.caption("Natural language product search — powered by LLM + PostgreSQL full-text search")

# Text input — the key "query_input" is the single source of truth for its value
query = st.text_input(
    "What are you looking for?",
    placeholder="e.g. waterproof bluetooth speaker under ₹2000 with good bass",
    key="query_input",
)

search_clicked = st.button("🔍 Search", type="primary")

# Only run the pipeline when Search is clicked and a query was entered
if search_clicked and query.strip():
    try:
        with st.spinner("Thinking..."):
            # Step 1: Decompose the natural language query into structured filters
            decomposed = decompose_query(query)

            # Step 2: Run the hybrid SQL query against PostgreSQL
            products = retrieve(decomposed, top_k=top_k)

            # Step 3: Ask the LLM to write a recommendation from the results
            answer = generate_answer(query, products)

        # --- Results in tabs ---
        tab_answer, tab_decomposed, tab_products = st.tabs([
            "💬 Answer",
            "🔎 Decomposed Query",
            "📦 Products",
        ])

        with tab_answer:
            st.markdown(answer)
            st.metric("Products found", len(products))

        with tab_decomposed:
            st.json(decomposed)
            st.info(
                "**How to read this:**\n\n"
                "- **category** — the product type the LLM inferred from your query\n"
                "- **keywords** — key feature words sent to the full-text search index\n"
                "- **price_min / price_max** — price range filter in INR\n"
                "- **min_rating** — minimum star rating filter\n"
                "- **in_stock_only** — whether only available products are shown\n"
                "- **attributes** — specific product features (e.g. waterproof, wireless)"
            )

        with tab_products:
            if not products:
                st.warning("No products matched your query.")
            for product in products:
                with st.container(border=True):
                    st.markdown(f"### {product['name']}")

                    # Two-column layout for key metrics
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Brand", product.get("brand", "—"))
                    col2.metric("Category", product.get("category", "—"))
                    col3.metric("Price", f"₹{product.get('price', '—')}")
                    col4.metric("Rating", f"{product.get('rating', '—')}/5")

                    # Stock status badge
                    if product.get("in_stock"):
                        st.success("🟢 In Stock")
                    else:
                        st.error("🔴 Out of Stock")

                    # Tags shown as a small caption
                    tags = product.get("tags") or []
                    if tags:
                        st.caption("🏷️ " + "  ·  ".join(tags))

                    st.markdown(product.get("description", ""))

    except Exception as e:
        # Show a friendly error instead of crashing the app
        st.error(f"Something went wrong: {e}")

elif search_clicked and not query.strip():
    st.warning("Please enter a search query first.")
