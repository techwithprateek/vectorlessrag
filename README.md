# 🧠 Vectorless RAG — Concept Guide & ShopSense Setup

> **Two things in one README:** A deep-dive into the Vectorless RAG pattern, and a practical setup guide for **ShopSense** — the demo app that brings it to life.

---

## 📚 Table of Contents

1. [🔍 What is RAG?](#-what-is-rag)
2. [🧠 What is Vectorless RAG?](#-what-is-vectorless-rag)
3. [🆚 Traditional Vector RAG vs Vectorless RAG](#-side-by-side-comparison)
4. [⚡ When to Use Each Approach](#-when-to-use-each-approach)
5. [🔬 Why Query Decomposition is Powerful](#-why-query-decomposition-is-powerful)
6. [🏗️ Architecture Diagram](#-architecture-diagram)
7. [🛍️ ShopSense Setup Guide](#️-shopsense-setup-guide)
8. [💬 Example Queries](#-example-queries)
9. [📁 Project Structure](#-project-structure)

---

## 🔍 What is RAG?

**RAG (Retrieval-Augmented Generation)** is a pattern that grounds an LLM's responses in real, retrieved data rather than relying solely on its parametric memory (what it "learned" during training).

The core idea:

```
User Query → Retrieve relevant data → Feed data to LLM → Generate grounded answer
```

Without RAG, an LLM might hallucinate facts, cite outdated information, or invent product details that don't exist in your catalog. With RAG, the LLM can only work with what you hand it — making it accurate, controllable, and trustworthy.

**Traditional RAG pipelines use vector databases** to retrieve relevant documents via semantic similarity. But that's not the only way. Enter: **Vectorless RAG**.

---

## 🧠 What is Vectorless RAG?

Vectorless RAG achieves the **same grounding effect** as traditional RAG — but **without vector embeddings or a vector database**.

Instead of:
- 🔢 Converting documents to embedding vectors
- 📐 Running cosine/dot-product similarity search
- 🗄️ Hosting a vector DB (Pinecone, Weaviate, pgvector, Chroma...)

Vectorless RAG uses:
- 🧩 **LLM-powered query decomposition** — the LLM reads the natural language query and extracts structured filters (category, price range, attributes, keywords)
- 🗃️ **Traditional database search** — SQL `WHERE` filters + full-text search (`tsvector` in PostgreSQL) do the retrieval

The result is a system that's **⚡ faster to build, 💰 cheaper to run, 🔍 more explainable, and 🎯 often more precise** for structured data like product catalogs.

```
"waterproof bluetooth speaker under ₹2000 with good bass"
           │
           ▼  LLM decomposes to:
{
  "category": "bluetooth speaker",
  "price_max": 2000,
  "keywords": "waterproof bass portable",
  "attributes": ["waterproof", "bass"]
}
           │
           ▼  PostgreSQL retrieves:
SELECT * FROM products
WHERE category ILIKE '%bluetooth speaker%'
  AND price <= 2000
  AND search_vector @@ to_tsquery('english', 'waterproof & bass & portable')
ORDER BY ts_rank(...) DESC
LIMIT 5;
```

No embeddings. No vector index. Just structured SQL — powered by LLM intent parsing.

---

## 🆚 Side-by-Side Comparison

| Aspect | Traditional Vector RAG | Vectorless RAG |
|---|---|---|
| **Retrieval method** | Embedding similarity search (cosine / dot product) | SQL filters + full-text search (`tsvector`) |
| **Infrastructure** | Vector DB (Pinecone, Weaviate, pgvector, Chroma) | Standard relational DB (PostgreSQL, SQLite, MySQL) |
| **Embedding model** | Required (e.g. `text-embedding-ada-002`, BGE) | ❌ Not needed |
| **Query understanding** | Implicit via embedding space | Explicit via LLM decomposition |
| **Precision on structured filters** | ⚠️ Weak — price ranges, exact attributes are hard | ✅ Strong — native SQL operators |
| **Scalability** | Very high (billions of vectors) | High for most apps (millions of rows) |
| **Cost** | Higher — embedding API calls + vector DB hosting | Lower — no embedding calls, standard DB |
| **Setup complexity** | High — embedding pipeline, index management, chunking strategy | Low — standard SQL, no vector index |
| **Best for** | Semantic / conceptual search over unstructured text | Product catalogs, structured data with clear attributes |
| **Explainability** | Low — why did cosine = 0.87 match this result? | High — can show exact SQL filters used |
| **Cold start** | Requires embedding all documents first | Insert data normally, no pre-processing needed |
| **Query latency** | Depends on embedding + ANN search | Standard indexed SQL — typically very fast |

---

## ⚡ When to Use Each Approach

### ✅ Use Vectorless RAG when:

- 🛒 **Product catalogs** with structured attributes (price, category, brand, rating, tags)
- 📋 **Inventory or FAQ search** where exact field matching matters more than semantic similarity
- 💸 **Budget-constrained projects** — no embedding API costs, no vector DB subscription
- 🔍 **Explainability is important** — show users exactly what filters were applied and why
- 📊 **Small to medium datasets** (< 10M rows) where SQL scales just fine
- 🗄️ **You already have a relational database** and don't want to maintain a second data store
- 🚀 **Speed of development** — spinning up a Postgres table is much faster than an embedding pipeline

### ✅ Use Traditional Vector RAG when:

- 📄 **Semantic document search** — e.g. "what does our refund policy say about damaged goods?" over thousands of PDFs
- 📚 **Long-form text corpora** — legal documents, research papers, support tickets, knowledge base articles
- 🌀 **Queries are conceptual or abstract**, not attribute-based (e.g. "find articles about climate anxiety")
- 🏗️ **You already have a vector DB** in your stack and the team knows how to operate it
- 🌐 **Cross-lingual or fuzzy semantic matching** is needed (e.g. synonyms, paraphrases, concept overlap)
- 📝 **Unstructured content** where there are no clear filter fields to extract

---

## 🔬 Why Query Decomposition is Powerful

Query decomposition — the **Decompose → Retrieve → Generate** pattern — is the core mechanism that makes Vectorless RAG work. Here's why it's so powerful:

---

### 1. 🌉 Bridges Natural Language and Structured Data

Users speak naturally. Databases speak SQL. Decomposition is the **translation layer** between them.

Without decomposition, you'd have to do fuzzy full-text search across the entire catalog for every query — matching "under two thousand rupees waterproof speaker" against raw product descriptions. With decomposition, you get exact SQL operators:

```sql
-- "under ₹2000" → price <= 2000
-- "waterproof" → attribute filter or FTS keyword
-- "bluetooth speaker" → category ILIKE '%bluetooth speaker%'
```

The LLM understands human language. The database understands structure. Decomposition makes them speak the same language.

---

### 2. 🎯 Precision Through Structured Filters

`"Under ₹2000"` maps to `price <= 2000` — **exact, not approximate**.

Vector similarity cannot reliably distinguish a ₹1,999 product from a ₹50,000 one if they are semantically similar (both are "premium wireless speakers"). SQL numeric operators are deterministic.

The same applies to:
- 🏷️ **Brand filters**: `brand = 'Sony'` is exact; embeddings might match "Sony-like" brands
- 📦 **In-stock filters**: `in_stock = true` is boolean; embeddings have no notion of inventory
- ⭐ **Rating thresholds**: `rating >= 4.5` is precise; semantic similarity treats "highly rated" vaguely

---

### 3. 🔍 Explainability and Debugging

With decomposition, you can show users **exactly what the system understood**:

```
🔎 I searched for:
  🏷️ Category: bluetooth speaker
  💰 Max price: ₹2,000
  ✨ Must have: waterproof, bass
  ✅ In stock only: yes
```

This builds trust, helps users refine queries, and makes debugging trivial — you can inspect the decomposed dict and the SQL that ran.

Vector RAG is a black box. "Cosine similarity = 0.87" tells you nothing actionable.

---

### 4. 🧩 Composability — Fan Out to Multiple Sources

The decomposed dict is **just a Python dictionary**. You can fan it out to multiple data sources in parallel:

```python
decomposed = decompose_query(user_query)

products  = retrieve_from_product_db(decomposed)     # PostgreSQL
inventory = check_inventory(decomposed["category"])  # Inventory service
reviews   = fetch_top_reviews(product_ids)           # Reviews DB

answer = generate_answer(query, products, inventory, reviews)
```

One natural language query fans out to multiple structured queries, then recombines into one answer. This is extremely hard to replicate with a single vector search.

---

### 5. 🤖 LLM as Intent Parser, Not Search Engine

The key insight: **the LLM's job is just to understand intent and format it as structured data**. The heavy search lifting is done by battle-tested database engines — PostgreSQL, MySQL, Elasticsearch — that have been optimized over decades.

This is a much better division of labor than asking an LLM (or an embedding model) to also be a search engine. LLMs are excellent at language understanding. They are not excellent at reliably ranking thousands of numerical records.

---

### 6. 🔌 Works With Any Database

The decompose-then-query pattern works with **any system that can filter on structured fields**:

| Database | How filters apply |
|---|---|
| PostgreSQL | `WHERE` clauses + `tsvector` FTS |
| MySQL | `WHERE` clauses + `FULLTEXT` indexes |
| SQLite | `WHERE` clauses + FTS5 |
| MongoDB | `$match` aggregation pipeline |
| Elasticsearch | `bool` query with `filter` and `must` clauses |
| BigQuery / Athena | Standard SQL `WHERE` on large tables |

You're not locked into any specific vector DB vendor, embedding model version, or similarity metric.

---

### 7. 🌟 Scenarios Where This Pattern Shines

🛒 **E-commerce product search (ShopSense)**
> "wireless noise-cancelling headphones under ₹5000 from Sony"
> → `brand='Sony', category='headphones', price<=5000, attributes=['noise-cancelling','wireless']`

👥 **HR / Talent matching**
> "senior engineers with Python and Kubernetes experience in Bangalore, CTC under 20 LPA"
> → SQL on employee DB with skill tags, location, salary band filters

🏠 **Real estate search**
> "3BHK flat in Mumbai under ₹80 lakhs near a metro station"
> → Spatial SQL + price filter + bedroom count filter

🏥 **Medical / Clinical data**
> "patients over 60 with Type 2 diabetes currently on metformin"
> → Structured clinical DB query with age range, diagnosis code, medication filter

💼 **Job board search**
> "remote React developer jobs with equity at Series A startups"
> → Multi-field filter: `remote=true, tech_stack CONTAINS 'React', compensation CONTAINS 'equity', stage='Series A'`

In every case, the user speaks naturally — and the LLM translates that intent into something a structured database understands perfectly.

---

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   Vectorless RAG Pipeline                │
└─────────────────────────────────────────────────────────┘

  User: "waterproof bluetooth speaker under ₹2000 with bass"
                           │
                           ▼
              ┌────────────────────────┐
              │   LLM Decomposer       │  ← Step 1
              │   (Query Parser)       │
              │   app/decomposer.py    │
              └────────────┬───────────┘
                           │
              {
                "category": "bluetooth speaker",
                "price_max": 2000,
                "keywords": "waterproof bass portable",
                "attributes": ["waterproof", "bass"],
                "in_stock_only": false
              }
                           │
                           ▼
              ┌────────────────────────┐
              │   PostgreSQL           │  ← Step 2
              │   WHERE category ILIKE │
              │   AND price <= 2000    │
              │   AND search_vector @@ │
              │   to_tsquery(...)      │
              │   ORDER BY ts_rank     │
              │   app/retriever.py     │
              └────────────┬───────────┘
                           │
              [boAt Stone 1200 (₹2499, ⭐4.3),
               Zebronics Zeb-Bellow (₹899, ⭐3.8),
               ...]
                           │
                           ▼
              ┌────────────────────────┐
              │   LLM Generator        │  ← Step 3
              │   (Answer Writer)      │
              │   app/rag.py           │
              └────────────┬───────────┘
                           │
              "The boAt Stone 1200 (₹2499) is your best
               bet — IPX7 waterproof, powerful 40W bass,
               and long battery life. For a budget pick,
               the Zebronics Zeb-Bellow at just ₹899
               offers decent bass for indoor use."
                           │
                           ▼
              ┌────────────────────────┐
              │   Streamlit UI         │
              │   (3-tab layout)       │
              │   streamlit_app.py     │
              └────────────────────────┘
```

---

# 🛍️ ShopSense Setup Guide

**ShopSense** is the reference implementation of Vectorless RAG. It's a natural language product search app that lets users type queries like *"waterproof bluetooth speaker under ₹2000 with good bass"* and get intelligent, LLM-generated recommendations — powered entirely by PostgreSQL and your choice of LLM (Ollama, OpenAI, or Claude).

---

## 📋 Prerequisites

Before you begin, make sure you have:

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10+ | `python --version` to check |
| PostgreSQL | 13+ | Must be running locally |
| LLM provider | One of below | See options below |

**🤖 LLM Options (pick one):**

- 🦙 **Ollama** *(recommended for local use — free, no API key)*
  - Install from [ollama.ai](https://ollama.ai)
  - Pull a model: `ollama pull llama3`

- 🤖 **OpenAI** — Set `OPENAI_API_KEY` in `.env`. Uses `gpt-4o-mini` by default.

- 🧠 **Anthropic (Claude)** — Set `ANTHROPIC_API_KEY` in `.env`. Uses `claude-sonnet-4-20250514` by default.

---

## 🚀 Setup Steps

### 1. Clone the repository

```bash
git clone https://github.com/your-username/vectorlessrag.git
cd vectorlessrag/shopsense
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

Dependencies installed:
```
streamlit         # 🖥️  UI framework
psycopg2-binary   # 🐘  PostgreSQL driver
anthropic         # 🧠  Claude SDK (only used if LLM_PROVIDER=claude)
openai            # 🤖  OpenAI SDK (only used if LLM_PROVIDER=openai)
requests          # 🌐  HTTP client for Ollama's REST API
python-dotenv     # 🔑  Loads .env file into environment variables
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Then open `.env` and fill in your values:

```dotenv
# --- Database ---
DATABASE_URL=postgresql://postgres:password@localhost/shopsense

# --- LLM Provider ---
# Choose one: "ollama", "openai", or "claude"
LLM_PROVIDER=ollama

# --- Ollama settings (if LLM_PROVIDER=ollama) ---
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# --- OpenAI settings (if LLM_PROVIDER=openai) ---
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# --- Claude / Anthropic settings (if LLM_PROVIDER=claude) ---
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-20250514
```

### 4. Create the database

First, create the PostgreSQL database:

```bash
createdb shopsense
```

Then run the setup script to create the `products` table and indexes:

```bash
python db/setup.py
# ✅ Database setup complete.
```

This creates:
- 📋 `products` table with `id`, `name`, `brand`, `category`, `price`, `rating`, `in_stock`, `tags`, `description`, `search_vector`
- ⚡ `GIN` index on `search_vector` for fast full-text search
- 🔢 B-tree indexes on `category`, `price`, and `rating` for fast filtering

### 5. Seed the product catalog

```bash
python db/seed.py
# ✅ Seeded 10 products.
```

This inserts 10 sample products across 4 categories: 🔊 bluetooth speakers, 🎧 headphones, ⌨️ keyboard/mouse combos, and ⌚ fitness bands. The `search_vector` column is computed automatically using:

```sql
to_tsvector('english', name || ' ' || description || ' ' || array_to_string(tags, ' '))
```

### 6. Launch the app

```bash
streamlit run streamlit_app.py
```

The app opens at **http://localhost:8501** in your browser.

---

## 🦙 Ollama Quick Start

Ollama lets you run powerful LLMs locally — completely free, no API key needed.

```bash
# 1. Install Ollama
# Download from https://ollama.ai and run the installer

# 2. Pull a model (llama3 is recommended — good quality, reasonable speed)
ollama pull llama3

# 3. Verify it's running
ollama list
# NAME            ID              SIZE    MODIFIED
# llama3:latest   ...             4.7 GB  ...

# 4. Set in .env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3
```

Other model options:
```bash
ollama pull mistral        # ⚡ Faster, slightly less capable
ollama pull llama3:70b     # 💪 Much more capable, needs ~40GB RAM
ollama pull phi3           # 🪶 Very small and fast (3.8B params)
```

---

## 💬 Example Queries

Try these in the ShopSense search bar to see the Vectorless RAG pipeline in action:

| Query | What it tests |
|---|---|
| `waterproof bluetooth speaker under ₹2000 with good bass` | Price filter + attribute filter + FTS |
| `best noise-cancelling headphones` | Category + attribute, no price constraint |
| `budget wireless headphones under ₹1500` | Price filter + wireless attribute |
| `Sony headphones in stock` | Brand filter + in-stock filter |
| `fitness band with heart rate monitoring under ₹3000` | Cross-category + price + feature FTS |
| `portable speaker for outdoor use` | FTS-heavy, no price constraint |
| `premium headphones, best rated` | Rating-based retrieval |
| `JBL or boAt speaker` | Brand preference query |

---

## 🖥️ UI Overview — The Three Tabs

After a search, ShopSense shows results in three tabs:

### 💬 Answer Tab
The LLM's friendly recommendation — a brief direct answer, top 2–3 product picks with reasoning, and a buying tip if relevant. Also shows a metric: **"X products found"**.

### 🔎 Decomposed Query Tab
Shows the raw JSON that the LLM extracted from your natural language query:

```json
{
  "category": "bluetooth speaker",
  "keywords": "waterproof bass portable",
  "price_min": null,
  "price_max": 2000,
  "min_rating": null,
  "in_stock_only": false,
  "attributes": ["waterproof", "bass"]
}
```

An info box below explains what each field means in plain English. This is the **explainability** advantage of Vectorless RAG in action — you can always see exactly what the system understood.

### 📦 Products Tab
The raw product records retrieved from PostgreSQL — displayed as cards with:
- Product name, brand, category
- Price and rating in metric columns
- 🟢 In Stock / 🔴 Out of Stock badge
- Feature tags
- Full description

---

## 📁 Project Structure

```
shopsense/
├── 📄 README.md                  # This file
├── 📦 requirements.txt           # Python dependencies
├── 🔑 .env.example               # Template for environment variables
├── ⚙️  config.py                  # LLM provider selection + DB URL
├── db/
│   ├── 🏗️  setup.py               # Creates the products table and indexes
│   └── 🌱 seed.py                # Inserts 10 sample products into the catalog
├── app/
│   ├── 🤖 llm.py                 # Unified LLM caller (Ollama / OpenAI / Claude)
│   ├── 🧩 decomposer.py          # Step 1: parse user query → structured dict
│   ├── 🔍 retriever.py           # Step 2: run SQL query → list of products
│   └── ✍️  rag.py                 # Step 3: LLM generates answer from products
└── 🖥️  streamlit_app.py           # Streamlit UI — the main entry point
```

---

## 🗄️ Database Schema Reference

```sql
CREATE TABLE products (
    id             SERIAL PRIMARY KEY,
    name           TEXT NOT NULL,
    brand          TEXT,
    category       TEXT,
    price          NUMERIC,
    rating         NUMERIC,          -- 1.0 to 5.0
    in_stock       BOOLEAN DEFAULT true,
    tags           TEXT[],           -- e.g. ['waterproof', 'outdoor', 'bass']
    description    TEXT,
    search_vector  TSVECTOR          -- pre-built FTS index: name + description + tags
);

-- Indexes
CREATE INDEX idx_fts      ON products USING GIN(search_vector);  -- fast FTS
CREATE INDEX idx_category ON products(category);
CREATE INDEX idx_price    ON products(price);
CREATE INDEX idx_rating   ON products(rating);
```

The `search_vector` is built at insert time:
```sql
to_tsvector('english', name || ' ' || description || ' ' || array_to_string(tags, ' '))
```

The `'english'` configuration applies **🌿 stemming** (e.g. "running" → "run") and removes **🚫 stop words** ("the", "a", "with"), making FTS more robust.

---

## 🔧 Troubleshooting

**🐘 `psycopg2.OperationalError: could not connect to server`**
→ Make sure PostgreSQL is running: `brew services start postgresql` (macOS) or `sudo service postgresql start` (Linux)

**🦙 `ollama: command not found`**
→ Install from [ollama.ai](https://ollama.ai) and make sure it's in your PATH

**📦 `ModuleNotFoundError: No module named 'streamlit'`**
→ Run `pip install -r requirements.txt` inside your virtual environment

**🤖 LLM returns non-JSON / decomposer fails**
→ The decomposer catches JSON parse errors and returns a safe empty dict. The pipeline will still run with no filters applied (returns top-rated products).

**🔍 No products returned**
→ Try a broader query. Check that `python db/seed.py` ran successfully and that the DB has 10 rows: `psql shopsense -c "SELECT COUNT(*) FROM products;"`

---

## 📚 Further Reading

- 📖 [PostgreSQL Full-Text Search docs](https://www.postgresql.org/docs/current/textsearch.html)
- 🔠 [tsvector / tsquery reference](https://www.postgresql.org/docs/current/datatype-textsearch.html)
- 📊 [ts_rank ranking function](https://www.postgresql.org/docs/current/textsearch-controls.html#TEXTSEARCH-RANKING)
- 🦙 [Ollama model library](https://ollama.ai/library)
- 🧪 [Original RAG paper (Lewis et al., 2020)](https://arxiv.org/abs/2005.11401)

---

*Built with PostgreSQL, Streamlit, and the power of structured query decomposition. No vectors harmed in the making of this app. 🎉*
