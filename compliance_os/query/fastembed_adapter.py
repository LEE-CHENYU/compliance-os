"""LlamaIndex BaseEmbedding adapter for fastembed.

fastembed (from Qdrant) wraps ONNX-quantized embedding models with a tiny
runtime (~50 MB on disk) — no torch, no transformers. We use it as the
local-fallback engine when no OPENAI_API_KEY is set so the no-cloud
install footprint stays under ~200 MB instead of ~2 GB.

LlamaIndex doesn't ship a first-party fastembed integration, so this
file provides a minimal BaseEmbedding subclass that proxies to
fastembed.TextEmbedding. Only the four hook methods the index ever
calls are implemented; the rest of the BaseEmbedding contract is
inherited.
"""

from __future__ import annotations

from typing import Any, ClassVar

from llama_index.core.base.embeddings.base import BaseEmbedding


class FastEmbedEmbedding(BaseEmbedding):
    """LlamaIndex wrapper around fastembed.TextEmbedding.

    Construction loads the ONNX weights (first call downloads them from
    HuggingFace Hub into ~/.cache/fastembed). Subsequent constructions
    reuse the on-disk cache.
    """

    # Pydantic v2 (which llama-index uses) requires field declarations
    # rather than ad-hoc instance attributes. We treat the underlying
    # fastembed model handle as opaque.
    model_name: str
    _model: Any = None  # set in __init__

    DEFAULT_MODEL_NAME: ClassVar[str] = "BAAI/bge-small-en-v1.5"

    def __init__(self, model_name: str | None = None, **kwargs: Any) -> None:
        # BaseEmbedding sets up callback_manager etc. via super().__init__;
        # we have to pass model_name through so the field validates.
        super().__init__(model_name=model_name or self.DEFAULT_MODEL_NAME, **kwargs)
        from fastembed import TextEmbedding  # lazy: avoids cost at import
        # Use object.__setattr__ to bypass pydantic field validation for
        # the opaque model handle. The class declares _model with default
        # None, so the runtime handle has to skip the model_validator.
        object.__setattr__(self, "_model", TextEmbedding(model_name=self.model_name))

    @classmethod
    def class_name(cls) -> str:
        return "FastEmbedEmbedding"

    # ── Embedding hooks ─────────────────────────────────────────────

    def _get_query_embedding(self, query: str) -> list[float]:
        return list(next(iter(self._model.embed([query]))))

    async def _aget_query_embedding(self, query: str) -> list[float]:
        # fastembed is synchronous; defer to the sync path.
        return self._get_query_embedding(query)

    def _get_text_embedding(self, text: str) -> list[float]:
        return list(next(iter(self._model.embed([text]))))

    def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
        # Batch path — fastembed yields one vector per input in order.
        return [list(v) for v in self._model.embed(texts)]
