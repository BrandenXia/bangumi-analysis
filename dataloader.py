import duckdb

from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
SUBJECT_JSONL = DATA_DIR / "subject.jsonlines"

if not DATA_DIR.exists():
    raise FileNotFoundError(
        f"Data directory '{DATA_DIR}' does not exist. Please run ./fetch-data to fetch the required data."
    )


def load_subjects():
    cols = {
        "id": "UINTEGER",
        "type": "UTINYINT",
        "name": "VARCHAR",
        "name_cn": "VARCHAR",
        "platform": "UINTEGER",
        "nsfw": "BOOLEAN",
        "date": "VARCHAR",
        "favorite": "struct(wish UINTEGER, done UINTEGER, doing UINTEGER, on_hold UINTEGER, dropped UINTEGER)",
        "series": "BOOLEAN",
        "tags": "struct(name VARCHAR, count UINTEGER)[]",
        "meta_tags": "VARCHAR[]",
        "score": "DECIMAL(3, 1)",
        "score_details": "map(UTINYINT, UINTEGER)",
        "rank": "UINTEGER",
    }
    subjects = duckdb.read_json(SUBJECT_JSONL, columns=cols)
    # cast date column to date type or null if invalid
    subjects = duckdb.sql(
        "SELECT try_cast(date AS DATE) AS date, * EXCLUDE(date) FROM subjects"
    )
    # cast rank to NULL if it is 0
    subjects = duckdb.sql(
        "SELECT CASE WHEN rank = 0 THEN NULL ELSE rank END AS rank, * EXCLUDE(rank) FROM subjects"
    )
    return subjects
