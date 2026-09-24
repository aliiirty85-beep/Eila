from __future__ import annotations
from pathlib import Path
import os, secrets

class SecurityManager:
    def __init__(self,data_dir:Path):
        self.path=Path(data_dir)/"pairing_token.txt"
        env=os.getenv("EILA_PAIRING_TOKEN","").strip()
        if env:
            self.token=env
        elif self.path.exists():
            self.token=self.path.read_text(encoding="utf-8").strip()
        else:
            self.token=secrets.token_urlsafe(32)
            self.path.parent.mkdir(parents=True,exist_ok=True)
            self.path.write_text(self.token,encoding="utf-8")

    def valid(self,token:str|None):
        return bool(token) and secrets.compare_digest(token,self.token)
