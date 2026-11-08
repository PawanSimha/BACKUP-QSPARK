import os
from pathlib import Path

# Point the broker at a throwaway database before src imports it.
_TEST_DB = Path(__file__).with_name(".test_parking_local.db")
os.environ["ORDS_SIMULATION_MODE"] = "true"
os.environ["QSPARK_DB_PATH"] = str(_TEST_DB)
_TEST_DB.unlink(missing_ok=True)
