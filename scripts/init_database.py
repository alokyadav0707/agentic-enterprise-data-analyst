from pathlib import Path
import sys, json
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import DATABASE_PATH
from src.database.schema import create_database
if __name__ == "__main__":
    counts = create_database(DATABASE_PATH)
    print(json.dumps({"database":str(DATABASE_PATH),"row_counts":counts,"total_rows":sum(counts.values())},indent=2))
