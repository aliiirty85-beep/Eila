from pathlib import Path
from app.security import SecurityManager
ROOT=Path(__file__).resolve().parent
print(SecurityManager(ROOT/'data').token)
