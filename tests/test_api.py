import pandas as pd
import pytest

from src import MovieStorage
import main

MOVIE_COLUMNS = ["title", "release_year", "rating", "genre"]


# ---------- Required tests ----------

def test_movies_persist(client, test_storage, uploaded_movies):
    # A second MovieStorage object reading the same database file
    reopened = MovieStorage(test_storage.db_path)

    df = reopened.get()
    assert reopened.count_movies() == 20
    assert len(df) == 20
    assert list(df.columns) == MOVIE_COLUMNS

    # Same title order as the original CSV (fillna so missing titles compare equally)
    original = pd.read_csv("fixtures/sample_movies.csv")
    assert df["title"].fillna("").tolist() == original["title"].fillna("").tolist()

    # IDs 1-20 in row order, both from storage directly and through the API
    stored_ids = [movie["id"] for movie in reopened.select_columns(["title"], limit=100)]
    response = client.get("/movies", params={"limit": 100})
    assert response.status_code == 200
    api_ids = [movie["id"] for movie in response.json()["data"]]

    assert stored_ids == list(range(1, 21))
    assert api_ids == list(range(1, 21))


def test_cache_and_processing(client, uploaded_movies, processing_body):
    # TODO 1: two different limits create two cache entries
    first_100 = client.get("/movies", params={"limit": 100})
    first_1 = client.get("/movies", params={"limit": 1})
    assert first_100.status_code == 200
    assert first_1.status_code == 200
    assert main.cache.get(100) == first_100.json()
    assert main.cache.get(1) == first_1.json()

    # TODO 2: repeating limit=100 returns the same response
    second_100 = client.get("/movies", params={"limit": 100})
    assert second_100.status_code == 200
    assert second_100.json() == first_100.json()

    # TODO 3: processing succeeds and clears the cache
    response = client.post("/movies/process", json=processing_body)
    assert response.status_code == 200
    body = response.json()
    assert body["validation_rows_removed"] == 0
    assert body["cleaning_report"]["rows_before"] == 20
    assert body["cleaning_report"]["rows_after"] == 16
    assert main.cache.get(100) is None
    assert main.cache.get(1) is None

    # TODO 4: the next retrieval reads the updated data from SQLite
    response = client.get("/movies", params={"limit": 100})
    assert response.status_code == 200
    body = response.json()
    assert body["total_rows"] == 16

    titles = [movie["title"] for movie in body["data"]]
    assert titles == [f"Movie {letter}" for letter in "ABCDEFGHIJKLMNOP"]

    ids = [movie["id"] for movie in body["data"]]
    assert ids == list(range(1, 17))

    assert main.cache.get(100) == body


def test_cache_hit_skips_database(client, uploaded_movies, monkeypatch):
    # TODO 1: the first request fills the cache
    first = client.get("/movies", params={"limit": 100})
    assert first.status_code == 200

    # TODO 2: any database call from now on fails the test
    def fail_if_called(*args, **kwargs):
        pytest.fail("A cache hit should not query the database")

    monkeypatch.setattr(main.storage, "select_columns", fail_if_called)
    monkeypatch.setattr(main.storage, "count_movies", fail_if_called)

    # TODO 3: the same request is answered from the cache
    second = client.get("/movies", params={"limit": 100})
    assert second.status_code == 200
    assert second.json() == first.json()


# ---------- Optional tests ----------

def test_upload_replaces_and_clears_cache(client, uploaded_movies, sample_csv_bytes):
    client.get("/movies", params={"limit": 100})
    assert main.cache.get(100) is not None

    response = client.post(
        "/upload",
        files={"file": ("sample_movies.csv", sample_csv_bytes, "text/csv")},
    )
    assert response.status_code == 200
    assert main.cache.get(100) is None

    response = client.get("/movies", params={"limit": 100})
    assert response.json()["total_rows"] == 20  # replaced, not 40


def test_search_with_unsupported_column(client, uploaded_movies):
    response = client.get("/movies/search", params={"columns": ["unknown"]})
    assert response.status_code == 400


def test_failed_processing_keeps_database_and_cache(client, uploaded_movies, processing_body):
    first = client.get("/movies", params={"limit": 100})

    processing_body["processing"]["outliers"]["method"] = "unknown"
    response = client.post("/movies/process", json=processing_body)
    assert response.status_code == 400

    assert main.cache.get(100) == first.json()
    assert main.storage.count_movies() == 20