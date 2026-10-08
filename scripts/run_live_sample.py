import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.audit.log import init_db
from app.guard_a.classifier import classifier
from app.models import RequestContext, Segment
from app.pipeline import run_guard_a, run_pipeline
from app.assistant import loop as assistant_loop

init_db()
classifier.warmup()

BASE_DIR = Path(__file__).resolve().parent.parent
eml_sample = BASE_DIR / "data" / "samples" / "poisoned_email.eml"

with open(eml_sample, "r", encoding="utf-8") as f:
    eml_text = f.read()

ctx = RequestContext(
    request_id="req_live_demo",
    session_id="sess_live_demo",
    profile="customer_support",
    segments=[
        Segment(
            id="seg_user",
            source="user",
            trust="trusted",
            text="Summarize my latest email.",
            origin="user_message",
        ),
        Segment(
            id="seg_eml",
            source="email",
            trust="untrusted",
            text=eml_text,
            origin="poisoned_email.eml",
        ),
    ],
)

# Run Guard A
ctx = run_guard_a(ctx)

# Run Assistant Loop with Gemini (live model from .env)
ctx = assistant_loop.run_assistant_loop(ctx)

# Complete pipeline
ctx = run_pipeline(ctx, is_scan_mode=False)

print("=" * 60)
print("LIVE GEMINI PIPELINE RESULT FOR POISONED EMAIL")
print("=" * 60)
print(f"Request ID: {ctx.request_id}")
print(f"Decision: {ctx.decision}")
print(f"Decision Reason: {ctx.decision_reason}")
print("-" * 60)
print("TRACE:")
for t in ctx.trace:
    print(f"  Step {t.step:2} ({t.name:15} | Guard {t.guard}): {t.status:7} - {t.reason} ({t.ms:.1f}ms)")
print("-" * 60)
print("BEFORE / AFTER:")
for ba in ctx.before_after:
    print(f"  Origin: {ba.origin}, Source: {ba.source}")
    print(f"  Kept Text: {ba.kept_text[:120]}...")
    for r in ba.removed:
        print(f"  Removed: {r['text']} (Reason: {r['reason']})")
print("-" * 60)
print(f"Offered Tools: {ctx.offered_tools}")
print(f"Hidden Tools: {ctx.hidden_tools}")
print("-" * 60)
print(f"GEMINI REPLY:\n{ctx.reply}")
print("=" * 60)
