import hashlib
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddedText:
    vector: list[float]
    embedding_hash: str


class DeterministicTextEmbedder:
    provider_code = "local"
    model_name = "deterministic-hash-v1"
    dimension = 8

    def embed(self, text: str) -> EmbeddedText:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        for index in range(self.dimension):
            start = index * 4
            value = int.from_bytes(digest[start : start + 4], byteorder="big", signed=False)
            values.append((value / 2**31) - 1.0)

        magnitude = math.sqrt(sum(value * value for value in values)) or 1.0
        vector = [round(value / magnitude, 8) for value in values]
        embedding_hash = hashlib.sha256(
            f"{self.provider_code}:{self.model_name}:{text}".encode()
        ).hexdigest()
        return EmbeddedText(vector=vector, embedding_hash=embedding_hash)
