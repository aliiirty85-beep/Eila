from __future__ import annotations
from pathlib import Path
import sqlite3, time

SCHEMA_VERSION = 1

class Storage:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self):
        c = sqlite3.connect(self.path, check_same_thread=False, timeout=15)
        c.row_factory = sqlite3.Row
        c.execute("pragma journal_mode=WAL")
        c.execute("pragma synchronous=NORMAL")
        c.execute("pragma foreign_keys=ON")
        c.execute("pragma busy_timeout=10000")
        return c

    def init(self):
        c = self.connect()
        c.executescript("""
        create table if not exists meta(key text primary key, value text not null);
        create table if not exists sessions(
          id integer primary key autoincrement,
          started_at integer not null,
          ended_at integer,
          goal text,
          plan text
        );
        create table if not exists microgoals(
          id integer primary key autoincrement,
          session_id integer,
          created_at integer not null,
          deadline_at integer not null,
          kind text not null,
          instruction text not null,
          question text default '',
          expected text default '',
          source text default 'manual',
          status text default 'waiting',
          answer text default '',
          result_note text default '',
          engagement_style text default '',
          display_instruction text default '',
          salience text default ''
        );
        create table if not exists return_contracts(
          id integer primary key autoincrement,
          created_at integer not null,
          due_at integer not null,
          text text not null,
          status text not null default 'pending',
          last_stage integer not null default -1,
          acknowledged_at integer
        );
        create table if not exists device_commands(
          id integer primary key autoincrement,
          created_at integer not null,
          expires_at integer,
          target_device text not null default '*',
          kind text not null,
          payload text not null default '{}'
        );
        create table if not exists command_acks(
          command_id integer not null,
          device_id text not null,
          acked_at integer not null,
          primary key(command_id, device_id)
        );
        """)
        c.execute("insert or replace into meta(key,value) values('schema_version',?)",(str(SCHEMA_VERSION),))
        c.commit(); c.close()

    def integrity(self):
        try:
            c=self.connect(); r=c.execute("pragma integrity_check").fetchone(); c.close()
            value=r[0] if r else "unknown"
            return {"ok":value=="ok","detail":value}
        except Exception as e:
            return {"ok":False,"detail":f"{type(e).__name__}: {e}"}

    def backup(self, backup_dir: Path, keep:int=14):
        backup_dir=Path(backup_dir); backup_dir.mkdir(parents=True,exist_ok=True)
        dest=backup_dir/f"eila-{time.strftime('%Y%m%d-%H%M%S')}.db"
        src=self.connect(); out=sqlite3.connect(dest)
        src.backup(out); out.close(); src.close()
        files=sorted(backup_dir.glob("eila-*.db"),key=lambda p:p.stat().st_mtime,reverse=True)
        for old in files[max(1,int(keep)):]:
            try: old.unlink()
            except OSError: pass
        return str(dest)
