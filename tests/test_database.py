from pathlib import Path
import sqlite3
from src.database.schema import create_database
from src.database.executor import execute_sql
def test_database_integrity_and_execution(tmp_path):
    db=tmp_path/"test.db"
    counts=create_database(db,seed=7)
    assert counts["customers"] == 1200
    assert counts["orders"] == 6500
    assert counts["order_items"] > counts["orders"]
    con=sqlite3.connect(db)
    assert con.execute("PRAGMA foreign_key_check").fetchall() == []
    con.close()
    df=execute_sql("SELECT COUNT(*) AS n FROM customers",db)
    assert int(df.iloc[0,0]) == 1200
