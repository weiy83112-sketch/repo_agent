from typing import Protocol

from .models import RetrievedChunk


NO_RETRIEVAL_CONTEXT = "No relevant indexed code was found."
NO_BUDGET_CONTEXT = "Relevant code was found but did not fit the context budget."


class TokenEstimator(Protocol):
    def estimate(self, text: str) -> int: ...


class ApproximateTokenEstimator:
    def estimate(self, text: str) -> int:
        if not text:
            return 0
        return max(1, (len(text) + 3) // 4)


class ContextBuilder:
    def __init__(
        self,
        token_budget: int = 12_000,
        token_estimator: TokenEstimator | None = None,
    ) -> None:
        if token_budget < 1:
            raise ValueError("token_budget must be positive")
        self._token_budget = token_budget
        self._token_estimator = token_estimator or ApproximateTokenEstimator()

    def build(self, retrieved_chunks: list[RetrievedChunk]) -> str:
        if not retrieved_chunks:
            return NO_RETRIEVAL_CONTEXT

        blocks: list[str] = []
        used_tokens = 0
        seen_evidence: set[tuple[str, int, int, str]] = set()

        for retrieved in retrieved_chunks:
            chunk = retrieved.chunk
            evidence_key = (
                chunk.file_path,
                chunk.start_line,
                chunk.end_line,
                chunk.content_hash,
            )
            if evidence_key in seen_evidence:
                continue

            block = _format_evidence(retrieved)
            block_tokens = self._token_estimator.estimate(block)
            if used_tokens + block_tokens > self._token_budget:
                continue

            blocks.append(block)
            seen_evidence.add(evidence_key)
            used_tokens += block_tokens

        if not blocks:
            return NO_BUDGET_CONTEXT
        return "\n\n".join(blocks)


def _format_evidence(retrieved: RetrievedChunk) -> str:
    chunk = retrieved.chunk
    sources = ", ".join(retrieved.sources)
    return "\n".join(
        [
            f"[file: {chunk.file_path}]",
            f"[symbol: {chunk.symbol_name}]",
            f"[lines: {chunk.start_line}-{chunk.end_line}]",
            f"[source: {sources}]",
            f"[score: {retrieved.score:.6f}]",
            "```python",
            chunk.code,
            "```",
        ]
    )
