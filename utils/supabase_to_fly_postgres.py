import psycopg2
from supabase import create_client, Client
import os

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Local PostgreSQL configuration
LOCAL_PG_HOST = os.getenv("POSTGRES_HOST")
LOCAL_PG_DB = os.getenv("POSTGRES_DB")
LOCAL_PG_USER = os.getenv("POSTGRES_USER")
LOCAL_PG_PASSWORD = os.getenv("POSTGRES_PASSWORD")
LOCAL_PG_PORT = os.getenv("POSTGRES_PORT")

def fetch_data_from_supabase():
    """Fetch data from the article_sources table in Supabase."""
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    response = supabase.table('article_sources').select('*').execute()
    return response.data

def insert_data_into_local_pg(data):
    """Insert data into the post_sources table in local PostgreSQL."""
    try:
        # Connect to your local PostgreSQL instance
        connection = psycopg2.connect(
            host=LOCAL_PG_HOST,
            database=LOCAL_PG_DB,
            user=LOCAL_PG_USER,
            password=LOCAL_PG_PASSWORD,
            port=LOCAL_PG_PORT
        )
        cursor = connection.cursor()

        # Insert data into post_sources
        for row in data:
            title = row['article_title']
            source_url = row['source_url']
            cursor.execute(
                "INSERT INTO public.post_sources (title, source_url) VALUES (%s, %s)",
                (title, source_url)
            )

        # Commit the changes and close the connection
        connection.commit()
        cursor.close()
        connection.close()
        print(f"{len(data)} rows inserted into post_sources.")

    except Exception as error:
        print(f"Error inserting data into local PostgreSQL: {error}")

if __name__ == "__main__":
    # Fetch data from Supabase
    data = fetch_data_from_supabase()
    
    # Insert data into local PostgreSQL
    if data:
        insert_data_into_local_pg(data)
    else:
        print("No data fetched from Supabase.")
