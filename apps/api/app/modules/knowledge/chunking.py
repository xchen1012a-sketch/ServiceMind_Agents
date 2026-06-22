from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedChunk:
    chunk_index: int
    chunk_text: str
    token_count: int
    heading_path: str | None
    source_anchor: str
    metadata_json: dict


class PlainTextChunker:
    parser_name = "plain_text_chunker"
    parser_version = "1"

    def __init__(self, max_chars: int = 900) -> None:
        self.max_chars = max_chars

    def split(self, content_text: str) -> list[ParsedChunk]:
        paragraphs = [part.strip() for part in content_text.replace("\r\n", "\n").split("\n\n")]
        paragraphs = [part for part in paragraphs if part]
        if not paragraphs:
            paragraphs = [content_text.strip()]

        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if not current:
                current = paragraph
                continue
            candidate = f"{current}\n\n{paragraph}"
            if len(candidate) <= self.max_chars:
                current = candidate
                continue
            chunks.extend(self._split_long_text(current))
            current = paragraph
        if current:
            chunks.extend(self._split_long_text(current))

        parsed: list[ParsedChunk] = []
        for index, chunk_text in enumerate(chunks):
            parsed.append(
                ParsedChunk(
                    chunk_index=index,
                    chunk_text=chunk_text,
                    token_count=len(chunk_text.split()),
                    heading_path=self._heading_for(chunk_text),
                    source_anchor=f"chunk:{index}",
                    metadata_json={
                        "char_count": len(chunk_text),
                        "parser": self.parser_name,
                    },
                )
            )
        return parsed

    def _split_long_text(self, text: str) -> list[str]:
        if len(text) <= self.max_chars:
            return [text]
        chunks = []
        start = 0
        while start < len(text):
            chunks.append(text[start : start + self.max_chars].strip())
            start += self.max_chars
        return [chunk for chunk in chunks if chunk]

    def _heading_for(self, text: str) -> str | None:
        first_line = text.splitlines()[0].strip()
        if first_line.startswith("#"):
            return first_line.lstrip("#").strip() or None
        return None
