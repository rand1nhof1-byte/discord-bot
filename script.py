import psycopg2

# Database connection details (from docker-compose.yml)
DB_HOST = "40.67.225.187"   # If running on same machine; use server IP if remote
DB_PORT = "5432"
DB_NAME = "discordbot"
DB_USER = "rand1nho"
DB_PASS = "rand1nho_admin"

try:
    # Connect to PostgreSQL
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

    # Create a cursor
    cur = conn.cursor()

    # Run a simple query
    cur.execute("SELECT * from public.test;")

    # Fetch result
    db_version = cur.fetchone()
    print("Connected to:", db_version)

    # Close communication
    cur.close()
    conn.close()

except Exception as e:
    print("Error:", e)
