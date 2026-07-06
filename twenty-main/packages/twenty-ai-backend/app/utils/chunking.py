"""Document chunking utilities."""

import re


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    separator: str = "\n\n",
) -> list[str]:
    """Split text into overlapping chunks, respecting paragraph boundaries where possible."""
    if not text.strip():
        return []

    chunks: list[str] = []
    paragraphs = text.split(separator)
    current_chunk = ""
    current_size = 0

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        para_size = len(paragraph)

        if current_size + para_size <= chunk_size:
            current_chunk = (
                current_chunk + ("\n\n" if current_chunk else "") + paragraph
            )
            current_size = len(current_chunk)
        else:
            # Save current chunk if non-empty
            if current_chunk.strip():
                chunks.append(current_chunk.strip())

            # If a single paragraph exceeds chunk_size, split by sentences
            if para_size > chunk_size:
                sentences = re.split(r"(?<=[。.!?！？])\s*", paragraph)
                current_chunk = ""
                current_size = 0
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    sent_size = len(sentence)
                    if current_size + sent_size <= chunk_size:
                        current_chunk = (
                            current_chunk + (" " if current_chunk else "") + sentence
                        )
                        current_size = len(current_chunk)
                    else:
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        # If single sentence exceeds chunk_size, force split
                        if sent_size > chunk_size:
                            for i in range(0, sent_size, chunk_size - chunk_overlap):
                                sub = sentence[i : i + chunk_size]
                                if sub.strip():
                                    chunks.append(sub.strip())
                            current_chunk = ""
                            current_size = 0
                        else:
                            current_chunk = sentence
                            current_size = sent_size
            else:
                current_chunk = paragraph
                current_size = para_size

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def estimate_token_count(text: str) -> int:
    """Rough estimate of token count (4 chars ≈ 1 token for English/Chinese mixed)."""
    # Simple heuristic: ~4 characters per token for English, ~1.5 for CJK
    cjk_chars = len(re.findall(r"[一-鿿㐀-䶿]", text))
    other_chars = len(text) - cjk_chars
    estimated = (other_chars / 4) + (cjk_chars / 1.5)
    return max(1, int(estimated))
