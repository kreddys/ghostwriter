# Fetch and Store Ghost Posts

## Overview
This script postgres_vector_ghost_posts_summary.py fetches blog posts from a **Ghost CMS** instance, summarizes the content, generates vector embeddings, and stores them in a **PostgreSQL** database. It supports updating specific posts by ID and provides an option to skip HTML extraction.

## Features
- Fetches posts from **Ghost CMS** Admin API.
- Summarizes post content using **OpenAI**.
- Generates **vector embeddings** for storing in PostgreSQL.
- Supports **updating specific posts** using their IDs.
- Allows skipping **HTML extraction** to use existing summaries.
- Maintains `created_at` and `updated_at` timestamps.

## Prerequisites
Before running the script, ensure you have the following:

- **Python 3.8+**
- **PostgreSQL 14+** with `vector` extension
- **Ghost CMS** with admin API access
- **OpenAI API** (or compatible alternative for embeddings)
- **Required Python packages:**
  ```bash
  pip install requests psycopg2-binary beautifulsoup4 openai jwt
  ```

## Environment Variables
Configure the following environment variables before running the script:

```env
# Ghost API
GHOST_ADMIN_API_KEY="your_admin_api_key"
GHOST_APP_URL="https://your-ghost-instance.com"

# PostgreSQL Database
POSTGRES_HOST="your_db_host"
POSTGRES_DB="your_db_name"
POSTGRES_USER="your_db_user"
POSTGRES_PASSWORD="your_db_password"
POSTGRES_PORT="5432"

# OpenAI API (or alternative)
OPENAI_API_BASE="your_openai_api_base"
OPENAI_API_KEY="your_openai_api_key"
OPENAI_MODEL="your_openai_model"

# Pinecone API (for embeddings, optional)
PINECONE_API_KEY="your_pinecone_api_key"
```

## Database Setup
Ensure the PostgreSQL database schema is ready. The script will create the required table automatically:

```sql
CREATE TABLE IF NOT EXISTS public.post_embeddings (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    published_at TIMESTAMP,
    url TEXT NOT NULL,
    summary TEXT NOT NULL,
    vector vector(1024),
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## Usage

### Fetch All Posts
To fetch and store all posts:
```bash
python postgres_vector_ghost_posts_summary.py
```

### Fetch Specific Posts by ID
To update only specific posts, provide their IDs:
```bash
python postgres_vector_ghost_posts_summary.py --ids post123 post456
```

### Skip HTML Extraction
To skip extracting text from HTML and use existing summaries:
```bash
python postgres_vector_ghost_posts_summary.py --skip-html-extraction
```

### Combine Options
Fetch specific posts and skip HTML extraction:
```bash
python postgres_vector_ghost_posts_summary.py --ids post123 post456 --skip-html-extraction
```

## Logging
The script logs status messages, warnings, and errors:
- **INFO:** Successful operations (e.g., fetched posts, stored in DB)
- **WARNING:** Skipped posts due to missing content
- **ERROR:** API or database issues

## Notes
- Ensure **Ghost Admin API** permissions allow fetching posts.
- If using **alternative embedding services**, modify `generate_embeddings()`.
- The script **updates existing posts** in the database using `ON CONFLICT (id) DO UPDATE`.

## License
This script is open-source and can be modified as needed.

---

For any issues or improvements, feel free to contribute!

