import time
import uuid
from typing import Any
from app.assistant import prompts, tools as tool_impl
from app.config import settings
from app.guard_b import policy
from app.llm import get_llm_backend, LLMBackend
from app.models import RequestContext, Segment, ToolCall, PendingAction


def run_assistant_loop(
    ctx: RequestContext, backend: LLMBackend | None = None
) -> RequestContext:
    if backend is None:
        backend = get_llm_backend()

    system_prompt = prompts.build_system_prompt(ctx)
    offered_tool_defs = [
        t
        for t in tool_impl.get_tool_definitions(ctx.profile)
        if t["name"] in ctx.offered_tools
    ]

    # Build initial message history
    messages: list[dict[str, Any]] = []
    for seg in ctx.segments:
        if seg.trust == "trusted" and seg.source == "user":
            messages.append({"role": "user", "content": seg.text})

    # Add any spotlighted untrusted text to conversation as user/context data
    untrusted_parts = [
        s.text for s in ctx.segments if s.trust == "untrusted" and s.text
    ]
    if untrusted_parts:
        context_block = "\n".join(untrusted_parts)
        messages.append(
            {
                "role": "user",
                "content": f"[Attached Data]\n{context_block}",
            }
        )

    turn = 0
    while turn < settings.MAX_AGENT_TURNS:
        turn += 1

        llm_result = backend.generate(
            system=system_prompt,
            messages=messages,
            tools=offered_tool_defs,
        )

        if llm_result.tool_calls:
            for tc in llm_result.tool_calls:
                tool_call_obj = ToolCall(
                    tool=tc.name, args=tc.args, status="EXECUTED", reason=""
                )

                # Evaluate Policy Engine (Step 8)
                pol_status, pol_reason = policy.evaluate_tool_call(
                    ctx, tc.name, tc.args
                )

                if pol_status == "BLOCKED":
                    tool_call_obj.status = "BLOCKED"
                    tool_call_obj.reason = pol_reason
                    ctx.tool_calls.append(tool_call_obj)
                    messages.append(
                        {
                            "role": "user",
                            "content": f"Action blocked: {pol_reason}",
                        }
                    )

                elif pol_status == "NEEDS_APPROVAL":
                    tool_call_obj.status = "PENDING_APPROVAL"
                    tool_call_obj.reason = pol_reason
                    ctx.tool_calls.append(tool_call_obj)
                    ctx.pending_action = PendingAction(
                        id=f"pa_{uuid.uuid4().hex[:8]}",
                        tool=tc.name,
                        args=tc.args,
                        reason=pol_reason,
                    )
                    ctx.decision = "NEEDS_APPROVAL"
                    ctx.decision_reason = f"Tool '{tc.name}' requires user approval: {pol_reason}"
                    return ctx

                else:
                    # Allowed -> Execute Tool
                    tool_call_obj.status = "EXECUTED"
                    tool_call_obj.reason = pol_reason
                    ctx.tool_calls.append(tool_call_obj)

                    tool_output = ""
                    if tc.name == "lookup_record":
                        rec_id = tc.args.get("record_id", "")
                        tool_output = tool_impl.execute_lookup_record(
                            ctx.profile, rec_id
                        )
                    elif tc.name == "read_document":
                        doc_name = tc.args.get("name", "")
                        tool_output = tool_impl.execute_read_document(
                            ctx.profile, doc_name
                        )
                    elif tc.name == "send_email":
                        to_addr = tc.args.get("to", "")
                        subj = tc.args.get("subject", "")
                        body = tc.args.get("body", "")
                        tool_output = tool_impl.execute_send_email(
                            ctx.session_id, to_addr, subj, body
                        )

                    # Wrap tool output as untrusted tool_result segment
                    tool_seg = Segment(
                        id=f"seg_{uuid.uuid4().hex[:8]}",
                        source="tool_result",
                        trust="untrusted",
                        text=tool_output,
                        origin=tc.name,
                    )
                    ctx.segments.append(tool_seg)

                    messages.append(
                        {
                            "role": "user",
                            "content": f"[Tool Output for {tc.name}]: {tool_output}",
                        }
                    )

        elif llm_result.text:
            ctx.reply = llm_result.text
            break
        else:
            break

    if not ctx.reply:
        ctx.reply = "No response generated by assistant."

    return ctx
