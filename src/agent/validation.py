"""SQL safety validation using SQLGlot when available."""
import re

try:
    import sqlglot
    from sqlglot import exp
except ImportError:
    sqlglot = None
    exp = None


class SQLValidationError(ValueError):
    pass


FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|"
    r"pragma|vacuum|replace|reindex|grant|revoke)\b",
    re.I,
)


def validate_sql(sql: str, allowed_tables: set[str] | None = None) -> str:
    """Accept one read-only SELECT/CTE query with approved tables."""

    if not sql or not sql.strip():
        raise SQLValidationError("SQL is empty")

    cleaned = sql.strip()

    if ";" in cleaned.rstrip(";"):
        raise SQLValidationError("Multiple statements are not allowed")

    if FORBIDDEN.search(cleaned):
        raise SQLValidationError("Forbidden SQL operation detected")

    if sqlglot is None:
        raise SQLValidationError("SQLGlot is required for SQL validation")

    try:
        parsed = sqlglot.parse(cleaned, read="sqlite")
    except Exception as exc:
        raise SQLValidationError(f"SQL parse failed: {exc}") from exc

    if len(parsed) != 1 or parsed[0] is None:
        raise SQLValidationError("Exactly one SQL statement is required")

    tree = parsed[0]

    if not isinstance(tree, (exp.Select, exp.Subquery)) and not tree.find(exp.Select):
        raise SQLValidationError("Only SELECT queries are allowed")

    for node in tree.walk():
        if isinstance(
            node,
            (exp.Insert, exp.Update, exp.Delete, exp.Drop,
             exp.Create, exp.Command),
        ):
            raise SQLValidationError("Write or command statement is not allowed")

    if allowed_tables:
        allowed = {name.lower() for name in allowed_tables}

        # Collect CTE names defined by WITH clauses.
        cte_names = {
            cte.alias_or_name.lower()
            for cte in tree.find_all(exp.CTE)
        }

        # Ignore CTE references, but validate real database tables.
        found = {
            table.name.lower()
            for table in tree.find_all(exp.Table)
            if table.name.lower() not in cte_names
        }

        unknown = found - allowed

        if unknown:
            raise SQLValidationError(
                f"Unknown table(s): {', '.join(sorted(unknown))}"
            )

    return cleaned.rstrip(";")