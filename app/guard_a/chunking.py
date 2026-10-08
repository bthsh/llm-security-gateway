import re
import uuid
from app.models import Chunk, Segment, RequestContext


def split_text_into_chunks(
    text: str, max_chars: int = 1500
) -> list[str]:
    if not text or not text.strip():
        return []
    if len(text) <= max_chars:
        return [text]

    # Sentence boundary splitting
    sentences = re.split(r"(?<=[.!?\n])\s+", text)
    chunks = []
    current_chunk = []
    current_len = 0

    for sentence in sentences:
        if current_len + len(sentence) > max_chars and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = [sentence]
            current_len = len(sentence)
        else:
            current_chunk.append(sentence)
            current_len += len(sentence)

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def build_chunks_for_context(ctx: RequestContext) -> list[Chunk]:
    chunks = []
    for seg in ctx.segments:
        # Visible / main text chunks
        main_text = seg.visible_text if seg.visible_text is not None else seg.text
        for text_part in split_text_into_chunks(main_text):
            chunks.append(
                Chunk(
                    id=f"chk_{uuid.uuid4().hex[:8]}",
                    segment_id=seg.id,
                    text=text_part,
                    is_hidden=False,
                )
            )

        # Hidden text chunks (if extractors produced hidden text)
        if seg.hidden_text and seg.hidden_text.strip():
            for hidden_part in split_text_into_chunks(seg.hidden_text):
                chunks.append(
                    Chunk(
                        id=f"chk_{uuid.uuid4().hex[:8]}",
                        segment_id=seg.id,
                        text=hidden_part,
                        is_hidden=True,
                    )
                )

    ctx.chunks = chunks
    return chunks
