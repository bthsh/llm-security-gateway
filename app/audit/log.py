import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from app.config import settings
from app.models import RequestContext


def get_db_connection() -> sqlite3.Connection:
    db_path = Path(settings.DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS requests (
        id TEXT PRIMARY KEY,
        ts TEXT,
        session_id TEXT,
        profile TEXT,
        decision TEXT,
        decision_reason TEXT,
        total_ms REAL,
        guard_a_ms REAL,
        llm_ms REAL,
        guard_b_ms REAL
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT,
        step TEXT,
        name TEXT,
        guard TEXT,
        status TEXT,
        reason TEXT,
        ms REAL,
        findings_json TEXT,
        FOREIGN KEY(request_id) REFERENCES requests(id)
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS tool_calls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT,
        tool TEXT,
        args_json_masked TEXT,
        status TEXT,
        reason TEXT,
        FOREIGN KEY(request_id) REFERENCES requests(id)
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS eval_runs (
        id TEXT PRIMARY KEY,
        ts TEXT,
        config_json TEXT,
        results_json TEXT
    )
    """
    )

    conn.commit()
    conn.close()


def log_request(ctx: RequestContext):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()

        cursor.execute(
            """
            INSERT OR REPLACE INTO requests 
            (id, ts, session_id, profile, decision, decision_reason, total_ms, guard_a_ms, llm_ms, guard_b_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                ctx.request_id,
                now_iso,
                ctx.session_id,
                ctx.profile,
                ctx.decision,
                ctx.decision_reason,
                ctx.timings.get("total_ms", 0.0),
                ctx.timings.get("guard_a_ms", 0.0),
                ctx.timings.get("llm_ms", 0.0),
                ctx.timings.get("guard_b_ms", 0.0),
            ),
        )

        for step in ctx.trace:
            findings_json = json.dumps(
                [f.model_dump() for f in step.findings], ensure_ascii=False
            )
            cursor.execute(
                """
                INSERT INTO steps (request_id, step, name, guard, status, reason, ms, findings_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    ctx.request_id,
                    str(step.step),
                    step.name,
                    step.guard,
                    step.status,
                    step.reason,
                    step.ms,
                    findings_json,
                ),
            )

        for tc in ctx.tool_calls:
            # Mask API key/secrets in logged args if present
            masked_args = {
                k: ("[SECRET]" if "key" in k.lower() or "secret" in k.lower() else v)
                for k, v in tc.args.items()
            }
            cursor.execute(
                """
                INSERT INTO tool_calls (request_id, tool, args_json_masked, status, reason)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    ctx.request_id,
                    tc.tool,
                    json.dumps(masked_args, ensure_ascii=False),
                    tc.status,
                    tc.reason,
                ),
            )

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error writing to audit log: {e}")


def get_recent_requests(limit: int = 50) -> list[dict]:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, ts, session_id, profile, decision, total_ms
            FROM requests ORDER BY ts DESC LIMIT ?
        """,
            (limit,),
        )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []


def get_latest_metrics() -> dict:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT results_json, ts FROM eval_runs ORDER BY ts DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            res = json.loads(row["results_json"])
            res["measured"] = True
            res["run_at"] = row["ts"]
            return res
    except Exception:
        pass
    return {"measured": False}

