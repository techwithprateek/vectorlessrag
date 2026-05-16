"""
app/rag.py
----------
Step 3 of the RAG pipeline: Answer Generation.

Takes the user's original query and the list of products retrieved from
PostgreSQL, formats them into a prompt, and asks the LLM to generate a
friendly, helpful product recommendation.

This is the "Augmented Generation" part of RAG: the LLM is grounded in
real retrieved data, so it can't hallucinate product details.
"""

from app.llm import call_llm

# System prompt defines the LLM's persona and response format.
# The LLM should be helpful, specific, and honest about missing matches.
RAG_SYSTEM_PROMPT = """You are ShopSense, a helpful e-commerce shopping assistant.
Given retrieved product results and the user's original query,
provide a helpful, concise recommendation.

Format your response as:
1. A brief direct answer (one sentence)
2. Top 2-3 product recommendations with name, price, rating, and why it fits
3. One buying tip if relevant

Be friendly and specific. If no products match well, say so honestly."""


def _format_product(product: dict) -> str:
    """
    Formats a single product dict as a human-readable text block for the LLM prompt.

    Args:
        product: A product dict from the retriever (keys: name, brand, category,
                 price, rating, in_stock, tags, description).

    Returns:
        A multiline string block describing the product.
    """
    # Convert the tags array to a comma-separated string for readability
    tags_str = ", ".join(product.get("tags") or [])
    stock_status = "In Stock" if product.get("in_stock") else "Out of Stock"

    return (
        f"Name: {product.get('name')}\n"
        f"Brand: {product.get('brand')}\n"
        f"Category: {product.get('category')}\n"
        f"Price: ₹{product.get('price')}\n"
        f"Rating: {product.get('rating')}/5\n"
        f"Availability: {stock_status}\n"
        f"Tags: {tags_str}\n"
        f"Description: {product.get('description')}"
    )


def generate_answer(user_query: str, products: list[dict]) -> str:
    """
    Formats retrieved products and asks the LLM to generate a recommendation.

    Args:
        user_query: The original natural language query from the user.
        products: List of product dicts returned by the retriever.

    Returns:
        The LLM's recommendation as a plain string.
        Returns a hardcoded sorry message if no products were found.
    """
    # Handle the empty case gracefully — no need to call the LLM
    if not products:
        return (
            "Sorry, I couldn't find any products matching your requirements. "
            "Try broadening your search."
        )

    # Format each product as a text block; separate blocks with a divider
    product_blocks = [_format_product(p) for p in products]
    formatted_products = "\n\n---\n\n".join(product_blocks)

    # Build the user message: include the query + all product details
    user_message = (
        f"User query: {user_query}\n\n"
        f"Retrieved products:\n\n{formatted_products}"
    )

    # Ask the LLM to generate a recommendation grounded in the retrieved products
    return call_llm(RAG_SYSTEM_PROMPT, user_message)
