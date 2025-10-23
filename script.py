import psycopg2

# Database connection details (from docker-compose.yml)

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

