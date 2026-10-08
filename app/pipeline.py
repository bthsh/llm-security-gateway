import time
from app.audit import log
from app.guard_a import (
    canary_tools,
    chunking,
    decide,
    detect,
    extract,
    normalize,
    provenance,
    spotlight,
)
from app.guard_b import output_firewall, policy
from app.models import RequestContext, StageResult


def run_guard_a(ctx: RequestContext) -> RequestContext:
    guard_a_start = time.perf_counter()

    # Step 1: Normalize
    res1 = normalize.run(ctx)
    ctx.trace.append(res1)

    # Step 2: Extract
    res2 = extract.run(ctx)
    ctx.trace.append(res2)

    # Step 3: Provenance
    res3 = provenance.run(ctx)
    ctx.trace.append(res3)

    # Chunking
    chunking.build_chunks_for_context(ctx)

    # Step 4: Detect
    res4 = detect.run(ctx)
    ctx.trace.append(res4)

    # Step 5: Decide
    res5 = decide.run(ctx)
    ctx.trace.append(res5)

    guard_a_ms = (time.perf_counter() - guard_a_start) * 1000.0
    ctx.timings["guard_a_ms"] = guard_a_ms

    if ctx.decision == "BLOCKED":
        # Early Exit: Skip steps 6-9 and LLM
        skipped_steps = [
            (6, "spotlight", "A"),
            (7, "canary_tools", "A"),
            ("llm", "llm", "-"),
            (8, "policy", "B"),
            (9, "output_firewall", "B"),
        ]
        for s_num, s_name, s_guard in skipped_steps:
            ctx.trace.append(
                StageResult(
                    step=s_num,
                    name=s_name,
                    guard=s_guard,
                    status="SKIPPED",
                    reason="request blocked at step 5",
                    ms=0.0,
                )
            )

        # Audit log (Step 10)
        log_res = StageResult(
            step=10,
            name="audit",
            guard="-",
            status="LOGGED",
            reason="Logged to SQLite",
            ms=0.0,
        )
        ctx.trace.append(log_res)
        log.log_request(ctx)
        return ctx

    # Step 6: Spotlight
    res6 = spotlight.run(ctx)
    ctx.trace.append(res6)

    # Step 7: Canary + Tool scoping
    res7 = canary_tools.run(ctx)
    ctx.trace.append(res7)

    return ctx


def run_guard_b(ctx: RequestContext) -> RequestContext:
    guard_b_start = time.perf_counter()

    # Step 8: Policy Engine
    res8 = policy.run(ctx)
    ctx.trace.append(res8)

    # Step 9: Output Firewall
    res9 = output_firewall.run(ctx)
    ctx.trace.append(res9)

    guard_b_ms = (time.perf_counter() - guard_b_start) * 1000.0
    ctx.timings["guard_b_ms"] = guard_b_ms

    # Step 10: Audit Log
    log_res = StageResult(
        step=10,
        name="audit",
        guard="-",
        status="LOGGED",
        reason="Logged to SQLite",
        ms=0.0,
    )
    ctx.trace.append(log_res)

    guard_a_ms = ctx.timings.get("guard_a_ms", 0.0)
    llm_ms = ctx.timings.get("llm_ms", 0.0)
    ctx.timings["total_ms"] = guard_a_ms + llm_ms + guard_b_ms

    log.log_request(ctx)
    return ctx


def run_pipeline(
    ctx: RequestContext, is_scan_mode: bool = False
) -> RequestContext:
    total_start = time.perf_counter()

    ctx = run_guard_a(ctx)

    if is_scan_mode:
        if ctx.decision != "BLOCKED":
            scan_skipped = [
                (6, "spotlight", "A"),
                (7, "canary_tools", "A"),
                ("llm", "llm", "-"),
                (8, "policy", "B"),
                (9, "output_firewall", "B"),
            ]
            for s_num, s_name, s_guard in scan_skipped:
                if not any(t.name == s_name for t in ctx.trace):
                    ctx.trace.append(
                        StageResult(
                            step=s_num,
                            name=s_name,
                            guard=s_guard,
                            status="SKIPPED",
                            reason="scan mode (no LLM)",
                            ms=0.0,
                        )
                    )

            log_res = StageResult(
                step=10,
                name="audit",
                guard="-",
                status="LOGGED",
                reason="Logged to SQLite",
                ms=0.0,
            )
            ctx.trace.append(log_res)

        total_ms = (time.perf_counter() - total_start) * 1000.0
        ctx.timings["llm_ms"] = 0.0
        ctx.timings["guard_b_ms"] = 0.0
        ctx.timings["total_ms"] = total_ms

        log.log_request(ctx)
        return ctx

    if ctx.decision == "BLOCKED":
        total_ms = (time.perf_counter() - total_start) * 1000.0
        ctx.timings["llm_ms"] = 0.0
        ctx.timings["guard_b_ms"] = 0.0
        ctx.timings["total_ms"] = total_ms
        return ctx

    return run_guard_b(ctx)
