import logging
import sqlite3

import pandas as pd

from .database import get_connection, initialize_database

logger = logging.getLogger(__name__)

MOVIE_COLUMNS = ["title", "release_year", "rating", "genre"]


class MovieStorage:
    def __init__(self, db_path="data/movies.db"):
        self.db_path = db_path
        initialize_database(self.db_path)

    def save(self, df):
        """Replace all movie rows in one transaction."""
        # reindex keeps the four table columns in order; a column dropped during
        # processing (axis="columns") is filled with missing values.
        # Missing values (NaN) become Python None, which SQLite stores as NULL.
        # astype(object) also turns NumPy numbers into plain Python numbers.
        clean_df = df.reindex(columns=MOVIE_COLUMNS).astype(object)
        clean_df = clean_df.where(pd.notna(clean_df), None)
        rows = list(clean_df.itertuples(index=False, name=None))

        connection = get_connection(self.db_path)
        try:
            connection.execute("DELETE FROM movies")
            sql_statement = """
            INSERT INTO movies (title, release_year, rating, genre)
            VALUES (?, ?, ?, ?)
            """
            connection.executemany(sql_statement, rows)
            # Commit only after the DELETE and every INSERT succeeded
            connection.commit()
            logger.debug(f"Stored movies in SQLite: rows={len(rows)}")
        except sqlite3.Error:
            # Undo the DELETE too, so the old collection is kept
            connection.rollback()
            raise
        finally:
            connection.close()

    def get(self):
        """Return the four movie columns as a DataFrame, ordered by id."""
        connection = get_connection(self.db_path)
        try:
            sql_statement = "SELECT title, release_year, rating, genre FROM movies ORDER BY id"
            rows = connection.execute(sql_statement).fetchall()
            df = pd.DataFrame([dict(row) for row in rows], columns=MOVIE_COLUMNS)
            logger.debug(f"Retrieved movies from SQLite: rows={len(df)}")
            return df
        finally:
            connection.close()

    def select_columns(self, columns, limit=5):
        """Return id plus the requested movie columns, ordered by id."""
        if not columns:
            logger.error("Select at least one column")
            raise ValueError("Select at least one column")
        for column in columns:
            if column not in MOVIE_COLUMNS:
                logger.error(f"Unsupported column: {column}")
                raise ValueError(f"Unsupported column: {column}")

        selected_columns = ", ".join(["id"] + columns)
        connection = get_connection(self.db_path)
        try:
            # Column names can't be ? placeholders, so they go in the f-string.
            # This is safe because every column was checked against MOVIE_COLUMNS.
            sql_statement = f"SELECT {selected_columns} FROM movies ORDER BY id LIMIT ?"
            rows = connection.execute(sql_statement, (limit,)).fetchall()
            movies = [dict(row) for row in rows]
            logger.debug(f"Selected movies: columns={columns}, rows={len(movies)}")
            return movies
        finally:
            connection.close()

    def count_movies(self):
        """Return the number of stored movies using SQL COUNT(*)."""
        connection = get_connection(self.db_path)
        try:
            sql_statement = "SELECT COUNT(*) AS total FROM movies"
            row = connection.execute(sql_statement).fetchone()
            logger.debug(f"Counted movies: total={row['total']}")
            return row["total"]
        finally:
            connection.close()

    def query_movies(self, columns, min_rating, limit):
        """Return selected fields from matching movies using SQL."""
        if not columns:
            logger.error("Select at least one column")
            raise ValueError("Select at least one column")
        for column in columns:
            if column not in MOVIE_COLUMNS:
                logger.error(f"Unsupported column: {column}")
                raise ValueError(f"Unsupported column: {column}")

        selected_columns = ", ".join(["id"] + columns)
        connection = get_connection(self.db_path)
        try:
            sql_statement = f"""
            SELECT {selected_columns} FROM movies
            WHERE rating >= ?
            ORDER BY rating DESC, id ASC
            LIMIT ?
            """
            rows = connection.execute(sql_statement, (min_rating, limit)).fetchall()
            movies = [dict(row) for row in rows]
            logger.debug(f"Queried movies: columns={columns}, rows={len(movies)}")
            return movies
        finally:
            connection.close()