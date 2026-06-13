#!/usr/bin/env python3
import os, json, sqlite3, hashlib, subprocess, shutil
from pathlib import Path

BASE=Path("v0_2_failure_fixture")
SOURCE=BASE/"fixture.jsonl"
INDEX=BASE/"fixture.index.sqlite"
INDEXER="./velune_trace_indexer_v0_2_incremental.py"

def h(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def write_event(f, seq, prev_hash, event_type="BASE"):
    e={
        "trace_id":"fixture",
        "event_id":f"event-{seq}",
        "sequence_index":seq,
        "ros_time":float(seq),
        "wall_time_utc":"2026-06-13T00:00:00Z",
        "clock_domain":"ROS_TIME",
        "time_source":"/clock",
        "event_type":event_type,
        "source_topic":"/fixture",
        "source_node":"fixture_node",
        "prev_event_hash":prev_hash,
        "artifact_fingerprint":"fixture"
    }
    e["event_hash"]=h(e)
    line=json.dumps(e,separators=(",",":"))+"\n"
    off=f.tell()
    f.write(line.encode())
    return e, off, len(line.encode())

def setup_fixture():
    if BASE.exists():
        shutil.rmtree(BASE)
    BASE.mkdir()

    prev="0"*64
    offsets=[]
    events=[]
    with open(SOURCE,"wb") as f:
        for seq in range(3):
            e, off, size = write_event(f, seq, prev)
            events.append(e)
            offsets.append((off,size))
            prev=e["event_hash"]

    con=sqlite3.connect(INDEX)
    cur=con.cursor()
    cur.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
    cur.execute("""CREATE TABLE events(
        event_id TEXT,
        sequence_index INTEGER,
        byte_offset INTEGER NOT NULL,
        trace_id TEXT,
        ros_time REAL,
        wall_time_utc TEXT,
        clock_domain TEXT,
        time_source TEXT,
        event_type TEXT,
        source_topic TEXT,
        source_node TEXT,
        event_hash TEXT,
        prev_event_hash TEXT,
        artifact_fingerprint TEXT
    )""")
    cur.execute("CREATE INDEX idx_event_id ON events(event_id)")
    cur.execute("CREATE INDEX idx_sequence_index ON events(sequence_index)")
    cur.execute("CREATE INDEX idx_ros_time ON events(ros_time)")
    cur.execute("CREATE INDEX idx_event_type ON events(event_type)")
    cur.execute("CREATE INDEX idx_topic ON events(source_topic)")
    cur.execute("CREATE TABLE sequence_gaps(prev_sequence INTEGER,next_sequence INTEGER,gap_size INTEGER)")
    cur.execute("CREATE TABLE summary_counts(category TEXT,name TEXT,count INTEGER,PRIMARY KEY(category,name))")

    for e,(off,size) in zip(events,offsets):
        cur.execute("""INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(
            e["event_id"],e["sequence_index"],off,e["trace_id"],e["ros_time"],
            e["wall_time_utc"],e["clock_domain"],e["time_source"],e["event_type"],
            e["source_topic"],e["source_node"],e["event_hash"],e["prev_event_hash"],
            e["artifact_fingerprint"]
        ))

    source_size=os.path.getsize(SOURCE)
    prefix_sha=hashlib.sha256(open(SOURCE,"rb").read(min(1024*1024,source_size))).hexdigest()

    meta={
        "schema_version":"VELUNE_TRACE_INDEX_SQLITE_v0.2_INCREMENTAL_BOOTSTRAPPED",
        "incremental_indexing":"SUPPORTED_IN_V0_2",
        "incremental_mode":"APPEND_ONLY",
        "last_indexed_seq":2,
        "last_indexed_end_offset":source_size,
        "last_event_hash":events[-1]["event_hash"],
        "last_event_id":events[-1]["event_id"],
        "prefix_probe_offset":source_size,
        "prefix_probe_sha256":prefix_sha,
    }
    for k,v in meta.items():
        cur.execute("INSERT INTO metadata VALUES(?,?)",(k,str(v)))
    con.commit()
    con.close()
    return events[-1]["event_hash"]

def run_indexer(expect_pass):
    p=subprocess.run(
        [INDEXER,"--source",str(SOURCE),"--index",str(INDEX),"--report",str(BASE/"report.txt")],
        text=True,capture_output=True
    )
    ok=(p.returncode==0)
    return ok,p.stdout,p.stderr

def count_events():
    con=sqlite3.connect(INDEX)
    cur=con.cursor()
    n=cur.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    last=cur.execute("SELECT value FROM metadata WHERE key='last_indexed_seq'").fetchone()[0]
    con.close()
    return n,last

def append_bad_sequence(last_hash):
    with open(SOURCE,"ab") as f:
        write_event(f, 99, last_hash, "BAD_SEQUENCE_TEST")

def append_bad_hash():
    with open(SOURCE,"ab") as f:
        write_event(f, 3, "f"*64, "BAD_HASH_TEST")

def mutate_prefix():
    with open(SOURCE,"r+b") as f:
        f.seek(0)
        f.write(b"X")

def case_bad_sequence():
    last_hash=setup_fixture()
    append_bad_sequence(last_hash)
    before=count_events()
    ok,out,err=run_indexer(False)
    after=count_events()
    print("BAD_SEQUENCE_EXPECT_FAIL", "PASS" if (not ok and before==after) else "FAIL")
    print("DB_ROLLBACK_UNCHANGED", before==after)
    print((out+err).strip().splitlines()[-1])

def case_bad_hash():
    setup_fixture()
    append_bad_hash()
    before=count_events()
    ok,out,err=run_indexer(False)
    after=count_events()
    print("BAD_HASH_EXPECT_FAIL", "PASS" if (not ok and before==after) else "FAIL")
    print("DB_ROLLBACK_UNCHANGED", before==after)
    print((out+err).strip().splitlines()[-1])

def case_prefix_mutation():
    setup_fixture()
    mutate_prefix()
    before=count_events()
    ok,out,err=run_indexer(False)
    after=count_events()
    print("PREFIX_MUTATION_EXPECT_FAIL", "PASS" if (not ok and before==after) else "FAIL")
    print("DB_ROLLBACK_UNCHANGED", before==after)
    print((out+err).strip().splitlines()[-1])

if __name__=="__main__":
    case_bad_sequence()
    case_bad_hash()
    case_prefix_mutation()
