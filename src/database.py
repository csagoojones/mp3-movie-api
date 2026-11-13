import sqlite3
from pathlib import Path


def get_connection(db_path):
    """Return a fresh connection with rows accessible by column name."""
    path = Path(db_path)
    # Create data/ if it doesn't exist yet (sqlite3 won't create folders)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    # Lets us read a row by column name: row["title"] instead of row[1]
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(db_path):
    """Create the movie table if it does not exist."""
    connection = get_connection(db_path)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY,
                title TEXT,
                release_year INTEGER,
                rating REAL,
                genre TEXT
            )
            """
        )
        connection.commit()
    finally:
        connection.close()