from __future__ import annotations
from pathlib import Path
import sqlite3, time, json

SCHEMA_VERSION = 2

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
          started_at integer not null, ended_at integer,
          goal text default '', plan text default '',
          summary text default ''
        );
        create table if not exists microgoals(
          id integer primary key autoincrement,
          session_id integer, created_at integer not null, deadline_at integer not null,
          kind text not null, instruction text not null, question text default '', expected text default '',
          source text default 'manual', status text default 'waiting', answer text default '', result_note text default '',
          engagement_style text default '', display_instruction text default '', salience text default '',
          context_ref text default ''
        );
        create table if not exists learning_evidence(
          id integer primary key autoincrement, ts integer not null, session_id integer,
          microgoal_id integer, kind text not null, passed integer not null,
          confidence real default 0, latency_ms integer default 0,
          topic text default '', error_type text default '', metadata text default '{}'
        );
        create table if not exists attention_samples(
          id integer primary key autoincrement, ts integer not null, session_id integer,
          device_id text default '', score real, zone text default '', study_ratio real,
          away_streak real, fixation real, jump_rate real, risk text default '', metadata text default '{}'
        );
        create table if not exists interventions(
          id integer primary key autoincrement, ts integer not null, session_id integer,
          kind text not null, style text default '', pre_score real, post_score real,
          outcome real, metadata text default '{}'
        );
        create table if not exists engagement_trials(
          id integer primary key autoincrement, ts integer not null, style text not null,
          passed integer not null, latency_ms integer default 0,
          attention_before real, attention_after real
        );
        create table if not exists return_contracts(
          id integer primary key autoincrement, created_at integer not null, due_at integer not null,
          text text not null, status text not null default 'pending', last_stage integer not null default -1,
          acknowledged_at integer
        );
        create table if not exists device_commands(
          id integer primary key autoincrement, created_at integer not null, expires_at integer,
          target_device text not null default '*', kind text not null, payload text not null default '{}'
        );
        create table if not exists command_acks(
          command_id integer not null, device_id text not null, acked_at integer not null,
          primary key(command_id, device_id)
        );
        create table if not exists devices(
          device_id text primary key, kind text default 'unknown', name text default '',
          last_seen integer not null, capabilities text default '{}', state text default '{}'
        );
        create table if not exists memory_items(
          id integer primary key autoincrement, created_at integer not null, updated_at integer not null,
          category text not null, key text not null, value text not null,
          confidence real default 0.5, source text default '', active integer default 1,
          unique(category,key)
        );
        create table if not exists context_sources(
          id integer primary key autoincrement, created_at integer not null, updated_at integer not null,
          kind text not null, title text default '', content text default '',
          ref text default '', active integer default 1
        );
        create table if not exists research_items(
          id integer primary key autoincrement, created_at integer not null,
          source text not null, title text default '', url text default '',
          published_at text default '', summary text default '', relevance real default 0,
          adopted integer default 0, unique(source,url,title)
        );
        create table if not exists rival_rounds(
          id integer primary key autoincrement, session_id integer, round_index integer,
          started_at integer not null, ended_at integer, user_score real default 0,
          rival_score real default 0, result text default 'open'
        );
        """)
        c.execute("insert or replace into meta(key,value) values('schema_version',?)",(str(SCHEMA_VERSION),))
        c.commit(); c.close()

    def integrity(self):
        try:
            c=self.connect(); row=c.execute("pragma integrity_check").fetchone(); c.close()
            value=row[0] if row else "unknown"
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

    def set_meta(self,key:str,value):
        c=self.connect(); c.execute("insert or replace into meta(key,value) values(?,?)",(key,json.dumps(value,ensure_ascii=False))); c.commit(); c.close()

    def get_meta(self,key:str,default=None):
        c=self.connect(); row=c.execute("select value from meta where key=?",(key,)).fetchone(); c.close()
        if not row: return default
        try: return json.loads(row[0])
        except Exception: return row[0]
