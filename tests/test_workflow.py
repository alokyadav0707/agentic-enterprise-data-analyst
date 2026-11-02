from pathlib import Path
from src.database.schema import create_database
from src.agent.workflow import AnalystAgent
def test_mock_agent_runs(tmp_path):
    db=tmp_path/"test.db"
    create_database(db)
    agent=AnalystAgent(db_path=db, mode="mock")
    result=agent.ask("What are net sales?")
    assert result["success"]
    assert result["sql"]
    assert result["columns"]
