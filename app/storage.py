from __future__ import annotations
from pathlib import Path
import sqlite3,time,json,shutil

SCHEMA_VERSION=6

class Storage:
    def __init__(self,path:Path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)

    def connect(self):
        c=sqlite3.connect(self.path,check_same_thread=False,timeout=15);c.row_factory=sqlite3.Row
        c.execute("pragma journal_mode=WAL");c.execute("pragma synchronous=NORMAL");c.execute("pragma foreign_keys=ON");c.execute("pragma busy_timeout=10000")
        return c

    @staticmethod
    def _columns(c,table):return {r["name"] for r in c.execute(f"pragma table_info({table})").fetchall()}
    def _column(self,c,table,name,ddl):
        if name not in self._columns(c,table):c.execute(f"alter table {table} add column {name} {ddl}")

    def init(self):
        c=self.connect()
        c.executescript("""
        create table if not exists meta(key text primary key,value text not null);
        create table if not exists sessions(id integer primary key autoincrement,started_at integer not null,ended_at integer,goal text default '',plan text default '',summary text default '');
        create table if not exists microgoals(id integer primary key autoincrement,session_id integer,created_at integer not null,deadline_at integer not null,kind text not null,instruction text not null,question text default '',expected text default '',source text default 'manual',status text default 'waiting',answer text default '',result_note text default '',engagement_style text default '',display_instruction text default '',salience text default '',context_ref text default '');
        create table if not exists learning_evidence(id integer primary key autoincrement,ts integer not null,session_id integer,microgoal_id integer,kind text not null,passed integer not null,confidence real default 0,latency_ms integer default 0,topic text default '',error_type text default '',metadata text default '{}');
        create table if not exists attention_samples(id integer primary key autoincrement,ts integer not null,session_id integer,device_id text default '',score real,zone text default '',study_ratio real,away_streak real,fixation real,jump_rate real,risk text default '',metadata text default '{}');
        create table if not exists interventions(id integer primary key autoincrement,ts integer not null,session_id integer,kind text not null,style text default '',pre_score real,post_score real,outcome real,metadata text default '{}');
        create table if not exists engagement_trials(id integer primary key autoincrement,ts integer not null,style text not null,passed integer not null,latency_ms integer default 0,attention_before real,attention_after real);
        create table if not exists return_contracts(id integer primary key autoincrement,created_at integer not null,due_at integer not null,text text not null,status text not null default 'pending',last_stage integer not null default -1,acknowledged_at integer);
        create table if not exists device_commands(id integer primary key autoincrement,created_at integer not null,expires_at integer,target_device text not null default '*',kind text not null,payload text not null default '{}');
        create table if not exists command_acks(command_id integer not null,device_id text not null,acked_at integer not null,primary key(command_id,device_id));
        create table if not exists devices(device_id text primary key,kind text default 'unknown',name text default '',last_seen integer not null,capabilities text default '{}',state text default '{}');
        create table if not exists memory_items(id integer primary key autoincrement,created_at integer not null,updated_at integer not null,category text not null,key text not null,value text not null,confidence real default 0.5,source text default '',active integer default 1,unique(category,key));
        create table if not exists context_sources(id integer primary key autoincrement,created_at integer not null,updated_at integer not null,kind text not null,title text default '',content text default '',ref text default '',active integer default 1);
        create table if not exists research_items(id integer primary key autoincrement,created_at integer not null,source text not null,title text default '',url text default '',published_at text default '',summary text default '',relevance real default 0,adopted integer default 0,unique(source,url,title));
        create table if not exists rival_rounds(id integer primary key autoincrement,session_id integer,round_index integer,started_at integer not null,ended_at integer,user_score real default 0,rival_score real default 0,result text default 'open');
        create table if not exists later_inbox(id integer primary key autoincrement,created_at integer not null,text text not null,reason text default '',status text default 'pending');
        create table if not exists device_snapshots(device_id text primary key,received_at integer not null,snapshot text not null);
        create table if not exists context_claims(
          id integer primary key autoincrement,created_at integer not null,activity text not null,
          claimed_until integer,source text default 'user',status text default 'active',
          confidence real default 0,verdict text default 'unverified',details text default '{}'
        );
        create table if not exists context_evidence(
          id integer primary key autoincrement,ts integer not null,device_id text default '',
          kind text not null,payload text default '{}'
        );
        create table if not exists maintenance_events(
          id integer primary key autoincrement,ts integer not null,kind text not null,
          severity text default 'info',detail text default '',repaired integer default 0
        );
        create table if not exists maintenance_proposals(
          id integer primary key autoincrement,created_at integer not null,title text not null,
          rationale text default '',status text default 'proposed',evidence text default '{}'
        );
        create table if not exists stimulus_events(
          id integer primary key autoincrement,ts integer not null,source text not null,
          event text not null,payload text default '{}'
        );
        create table if not exists spine_state(
          key text primary key,revision integer not null default 1,updated_at integer not null,
          source_device text not null default 'core',value text not null
        );
        create table if not exists spine_conflicts(
          id integer primary key autoincrement,created_at integer not null,key text not null,
          local_revision integer not null,remote_revision integer not null,
          local_source text default '',remote_source text default '',
          local_value text not null,remote_value text not null,
          status text not null default 'open',resolved_at integer,resolution text default ''
        );
        create table if not exists events(
          seq integer primary key autoincrement,event_id text not null unique,created_at integer not null,
          source_device text not null,kind text not null,entity_id text default '',
          entity_version integer default 0,payload text not null default '{}'
        );
        create table if not exists event_acks(
          event_id text not null,device_id text not null,acked_at integer not null,
          primary key(event_id,device_id)
        );
        create table if not exists behavior_policies(
          policy_id text primary key,created_at integer not null,updated_at integer not null,
          scope text not null,trigger_json text not null default '{}',action_json text not null default '{}',
          priority integer not null default 50,enabled integer not null default 1,version integer not null default 1,
          source text default 'user',rationale text default '',supersedes text default ''
        );
        create table if not exists behavior_policy_history(
          policy_id text not null,version integer not null,recorded_at integer not null,
          scope text not null,trigger_json text not null default '{}',action_json text not null default '{}',
          priority integer not null default 50,enabled integer not null default 1,
          source text default 'user',rationale text default '',supersedes text default '',
          primary key(policy_id,version)
        );
        create table if not exists capability_registry(
          capability_id text not null,provider_device text not null,status text not null default 'unknown',
          metadata text not null default '{}',last_verified integer not null,
          primary key(capability_id,provider_device)
        );
        create table if not exists capability_requests(
          request_id text primary key,created_at integer not null,request_text text not null,
          spec text not null default '{}',status text not null default 'proposed',source text default 'user'
        );
        create table if not exists review_queue(
          id integer primary key autoincrement,topic text not null,due_at integer not null,
          reason text default '',strength real default 0,attempts integer default 0,status text default 'pending'
        );
        create table if not exists student_topics(
          topic text primary key,updated_at integer not null,attempts integer default 0,
          correct integer default 0,mastery real default 0,last_error text default '',next_due integer
        );
        create table if not exists error_genome(
          error_type text primary key,updated_at integer not null,count integer default 0,
          recent_count integer default 0,last_topic text default '',last_seen integer
        );
        create table if not exists behavior_model(
          key text primary key,updated_at integer not null,value text not null,
          confidence real default .5,evidence_count integer default 0
        );
        """)
        self._column(c,"sessions","summary","text default ''")
        for name,ddl in (("answer","text default ''"),("context_ref","text default ''"),("engagement_style","text default ''"),("display_instruction","text default ''"),("salience","text default ''")):
            self._column(c,"microgoals",name,ddl)
        for name,ddl in (
            ("joined_at","integer default 0"),("status","text default 'active'"),
            ("retired_at","integer"),("hardware_fingerprint","text default ''"),
            ("calibration_generation","integer default 0"),("device_revision","integer default 1")
        ):
            self._column(c,"devices",name,ddl)
        c.execute("insert or replace into meta(key,value) values('schema_version',?)",(str(SCHEMA_VERSION),));c.commit();c.close()

    def integrity(self):
        try:
            c=self.connect();r=c.execute("pragma integrity_check").fetchone();c.close();v=r[0] if r else "unknown";return {"ok":v=="ok","detail":v}
        except Exception as e:return {"ok":False,"detail":f"{type(e).__name__}: {e}"}

    def backup(self,backup_dir:Path,keep:int=14):
        backup_dir=Path(backup_dir);backup_dir.mkdir(parents=True,exist_ok=True);dest=backup_dir/f"eila-{time.strftime('%Y%m%d-%H%M%S')}.db"
        src=self.connect();out=sqlite3.connect(dest);src.backup(out);out.close();src.close()
        files=sorted(backup_dir.glob("eila-*.db"),key=lambda p:p.stat().st_mtime,reverse=True)
        for old in files[max(1,int(keep)):]:
            try:old.unlink()
            except OSError:pass
        return str(dest)

    def recover_latest_backup(self,backup_dir:Path):
        if self.integrity().get("ok"):return {"ok":True,"recovered":False}
        files=sorted(Path(backup_dir).glob("eila-*.db"),key=lambda p:p.stat().st_mtime,reverse=True)
        if not files:return {"ok":False,"reason":"no-backup"}
        stamp=time.strftime("%Y%m%d-%H%M%S");corrupt=self.path.with_name(f"{self.path.stem}.corrupt-{stamp}{self.path.suffix}")
        try:
            if self.path.exists():self.path.replace(corrupt)
            for suffix in ("-wal","-shm"):
                p=Path(str(self.path)+suffix)
                if p.exists():p.unlink()
            shutil.copy2(files[0],self.path);self.init()
            return {"ok":self.integrity().get("ok",False),"recovered":True,"from":str(files[0]),"corrupt_copy":str(corrupt)}
        except Exception as e:return {"ok":False,"reason":f"{type(e).__name__}: {e}"}

    def set_meta(self,key,value):
        c=self.connect();c.execute("insert or replace into meta(key,value) values(?,?)",(key,json.dumps(value,ensure_ascii=False)));c.commit();c.close()
    def get_meta(self,key,default=None):
        c=self.connect();r=c.execute("select value from meta where key=?",(key,)).fetchone();c.close()
        if not r:return default
        try:return json.loads(r[0])
        except Exception:return r[0]
