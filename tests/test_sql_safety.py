import pytest
from src.agent.validation import validate_sql, SQLValidationError
def test_select_allowed():
    assert "SELECT" in validate_sql("SELECT 1")
def test_write_statement_blocked():
    with pytest.raises(SQLValidationError):
        validate_sql("DROP TABLE customers")
def test_multiple_statements_blocked():
    with pytest.raises(SQLValidationError):
        validate_sql("SELECT 1; SELECT 2")
def test_unknown_table_blocked():
    with pytest.raises(SQLValidationError):
        validate_sql("SELECT * FROM secrets", {"customers","orders"})
