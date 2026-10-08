import argparse
import json
import statistics
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.audit.log import get_db_connection, init_db
from app.config import settings
from app.models import RequestContext, Segment
from app.pipeline import run_pipeline


def load_jsonl(file_path: Path) -> list[dict]:
    if not file_path.exists():
        return []
    items = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except Exception:
                    pass
    return items


def build_context_from_item(item: dict, req_prefix: str) -> RequestContext:
    req_id = f"{req_prefix}_{item.get('id', uuid.uuid4().hex[:8])}"
    session_id = f"sess_eval_{uuid.uuid4().hex[:8]}"
    segments = []

    msg = item.get("message", "")
    if msg:
        segments.append(
            Segment(
                id=f"seg_{uuid.uuid4().hex[:8]}",
                source="user",
                trust="trusted",
                text=msg,
                origin="user_message",
            )
        )

    for att in item.get("attachments", []):
        att_path = BASE_DIR / att
        if att_path.exists() and att_path.is_file():
            raw_bytes = att_path.read_bytes()
            ext = att_path.suffix.lower()
            source = "email" if ext == ".eml" else "document"
            text_val = (
                raw_bytes.decode("utf-8", errors="ignore")
                if ext != ".pdf"
                else raw_bytes.decode("latin-1")
            )
            segments.append(
                Segment(
                    id=f"seg_{uuid.uuid4().hex[:8]}",
                    source=source,
                    trust="untrusted",
                    text=text_val,
                    origin=att_path.name,
                )
            )

    return RequestContext(
        request_id=req_id,
        session_id=session_id,
        profile="customer_support",
        segments=segments,
    )


def save_eval_run_to_db(eval_id: str, run_at: str, config: dict, metrics: dict):
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO eval_runs (id, ts, config_json, results_json)
        VALUES (?, ?, ?, ?)
    """,
        (
            eval_id,
            run_at,
            json.dumps(config, ensure_ascii=False),
            json.dumps(metrics, ensure_ascii=False),
        ),
    )
    conn.commit()
    conn.close()


def run_eval(scan_only: bool = True):
    attacks_file = BASE_DIR / "tests" / "data" / "attacks.jsonl"
    normal_file = BASE_DIR / "tests" / "data" / "normal.jsonl"

    attacks = load_jsonl(attacks_file)
    normals = load_jsonl(normal_file)

    print(f"Loaded {len(attacks)} attacks and {len(normals)} normal items.")

    group_stats = {}
    gateway_times = []
    llm_times = []

    total_attacks_caught = 0

    # 1. Process Attacks
    for item in attacks:
        grp = item.get("group", "unknown")
        if grp not in group_stats:
            group_stats[grp] = {"total": 0, "caught": 0}
        group_stats[grp]["total"] += 1

        ctx = build_context_from_item(item, "eval_atk")
        ctx = run_pipeline(ctx, is_scan_mode=scan_only)

        gateway_ms = ctx.timings.get("guard_a_ms", 0.0) + ctx.timings.get(
            "guard_b_ms", 0.0
        )
        gateway_times.append(gateway_ms)
        llm_times.append(ctx.timings.get("llm_ms", 0.0))

        # Check if attack was caught by Guard A / policy
        is_caught = ctx.decision in ("FLAGGED", "CLEANED", "BLOCKED")
        expected_decisions = item.get("expect", {}).get("decision_in", [])
        if expected_decisions and ctx.decision in expected_decisions:
            is_caught = True

        if is_caught:
            group_stats[grp]["caught"] += 1
            total_attacks_caught += 1

    # 2. Process Normal Prompts
    normal_wrongly_blocked = 0
    for item in normals:
        ctx = build_context_from_item(item, "eval_norm")
        ctx = run_pipeline(ctx, is_scan_mode=scan_only)

        gateway_ms = ctx.timings.get("guard_a_ms", 0.0) + ctx.timings.get(
            "guard_b_ms", 0.0
        )
        gateway_times.append(gateway_ms)
        llm_times.append(ctx.timings.get("llm_ms", 0.0))

        if ctx.decision == "BLOCKED":
            normal_wrongly_blocked += 1

    # Calculate Summaries
    med_gateway = statistics.median(gateway_times) if gateway_times else 0.0
    med_llm = statistics.median(llm_times) if llm_times else 0.0

    by_group = {}
    for grp, stat in group_stats.items():
        tot = stat["total"]
        cgt = stat["caught"]
        rate = (cgt / tot) if tot > 0 else 0.0
        by_group[grp] = {"total": tot, "caught": cgt, "rate": round(rate, 3)}

    now_iso = datetime.now(timezone.utc).isoformat()
    eval_id = f"eval_{uuid.uuid4().hex[:12]}"

    metrics = {
        "measured": True,
        "run_at": now_iso,
        "mode": "scan_only" if scan_only else "full",
        "attacks_caught": total_attacks_caught,
        "attacks_total": len(attacks),
        "contained": total_attacks_caught,
        "normal_wrongly_blocked": normal_wrongly_blocked,
        "normal_total": len(normals),
        "gateway_ms_median": round(med_gateway, 1),
        "llm_ms_median": round(med_llm, 2),
        "by_group": by_group,
    }

    config = {
        "scan_only": scan_only,
        "classifier_model": settings.CLASSIFIER_MODEL,
        "backend": settings.LLM_BACKEND,
    }

    save_eval_run_to_db(eval_id, now_iso, config, metrics)

    # Display Results Table
    print("\n=============================================================")
    print("                LLM GATEWAY EVALUATION REPORT                ")
    print("=============================================================")
    print(f"Mode: {'Scan-Only (No LLM)' if scan_only else 'Full Pipeline'}")
    print(f"Evaluated At: {now_iso}")
    print(f"Classifier Model: {settings.CLASSIFIER_MODEL}")
    print("-------------------------------------------------------------")
    print(f"{'Attack Group':<18} | {'Total':<6} | {'Caught':<6} | {'Detection Rate':<14}")
    print("-------------------------------------------------------------")

    for grp, stat in sorted(by_group.items()):
        rate_pct = f"{stat['rate'] * 100:.1f}%"
        print(f"{grp:<18} | {stat['total']:<6} | {stat['caught']:<6} | {rate_pct:<14}")

    print("-------------------------------------------------------------")
    atk_pct = (
        f"{(total_attacks_caught / len(attacks)) * 100:.1f}%"
        if attacks
        else "0%"
    )
    fp_pct = (
        f"{(normal_wrongly_blocked / len(normals)) * 100:.1f}%"
        if normals
        else "0%"
    )

    print(f"Overall Attacks Caught       : {total_attacks_caught} / {len(attacks)} ({atk_pct})")
    print(f"Normal Messages Wrongly Blocked: {normal_wrongly_blocked} / {len(normals)} ({fp_pct})")
    print(f"Median Gateway Latency       : {med_gateway:.1f} ms")
    print(f"Median LLM Latency           : {med_llm:.2f} s")
    print("=============================================================\n")

    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Gateway Evaluation")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full pipeline including LLM calls",
    )
    args = parser.parse_args()
    scan_mode = not args.full
    run_eval(scan_only=scan_mode)
