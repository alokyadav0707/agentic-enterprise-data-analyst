"""Guarded SQL execution."""
from pathlib import Path
import pandas as pd
from src.database.connection import connect_readonly
from src.config import MAX_RESULT_ROWS

class QueryExecutionError(RuntimeError):
    """Raised when a read-only query cannot be executed."""

def execute_sql(sql: str, db_path: str | Path, max_rows: int = MAX_RESULT_ROWS) -> pd.DataFrame:
    """Execute one validated query and enforce a result-row cap."""
    con = connect_readonly(db_path)
    try:
        # SQL has already been parsed; cap results even if the model omitted LIMIT.
        query = sql.strip().rstrip(";")
        df = pd.read_sql_query(f"SELECT * FROM ({query}) AS _limited_result LIMIT {int(max_rows)}", con)
        return df
    except Exception as exc:
        raise QueryExecutionError(str(exc)) from exc
    finally:
        con.close()
