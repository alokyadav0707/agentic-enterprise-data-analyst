"""Presentation helpers for agent results."""
def format_answer(result: dict) -> str:
    return result.get("answer", "No answer was produced.")
