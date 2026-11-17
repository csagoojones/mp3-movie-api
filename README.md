This class project is an extension of the mp2 API. It is a FastAPI with a SQLite database and a cache that uses SQL to store, retrieve, filter and update movie records and uses fakeredis to cache repeated requests. POST/upload takes in a CSV file only with columns title, release_year, rating and genre, and replaces the stores collection so that the data is saved even after the API restarts. GET/movies/search uses filters the movies by minimum ratings, sorts them by ratings, and returns only the requested columns of the data. POST/movies/process parses the stores movies, validates, and cleans them using the modules from data_pipeline/. That result is when saved back to SQLite. The code for the database is found in src/database.py and src/storage.py, the request models and the response models are found in src/models, and request logging with request IDs are in src/middleware.py. The responses from the GET/movies are cashed using fakeredis for 90 seconds in src/cache.py , that way any repeated requests with the same limit skip the database. Successful uploads or processing requests clear the cache, meaning that the next request gets updated data from SQLite. tests/ houses tests that use a temporary database in order to check for persistence, cache invalidation and cache hits. 

How to run the REST API: Use command line `python -m uvicorn main:app --reload` in the terminal, then open 'http://127.0.0.1:8000/docs' on a web browser.

How to run the tests: Use command line `python -m pytest tests -v`in the terminal.


Example Processing Request:
Upload fixtures/sample_movies.csv and send this to POST/movies/process: 
{"validation": {
    "required_columns": ["title", "release_year", "rating", "genre"],
    "numeric_columns": ["release_year", "rating"]
  },
  "processing": {
    "remove_duplicates": true,
    "missing": {"enabled": true, "axis": "rows"},
    "outliers": {"enabled": true, "columns": ["rating"], "method": "iqr", "threshold": 1.5}
  }
}

Result: 
{"validation_rows_removed": 0,
  "cleaning_report": {
    "rows_before": 20,
    "rows_after": 16,
    "rows_removed": 4,
    "columns_before": 4,
    "columns_after": 4,
    "columns_removed": 0
  }
}