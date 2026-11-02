"""Read-only database connection helpers."""
from pathlib import Path
import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

def make_engine(path: str | Path, readonly: bool = True) -> Engine:
    """Return a SQLAlchemy engine. SQLite URI mode enforces read-only access."""
    p = Path(path).resolve()
    if readonly:
        return create_engine(f"sqlite:///file:{p.as_posix()}?mode=ro&uri=true", future=True)
    return create_engine(f"sqlite:///{p.as_posix()}", future=True)

def connect_readonly(path: str | Path) -> sqlite3.Connection:
    """Open SQLite in read-only URI mode and return rows by column name."""
    p = Path(path).resolve()
    con = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only=ON")
    return con
