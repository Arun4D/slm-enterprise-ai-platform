"""
SLM inference engine for local model execution.

Wraps llama-cpp-python for GGUF model inference with async support.
"""

import asyncio
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model availability detection
# ---------------------------------------------------------------------------
_LLAMA_AVAILABLE = False
try:
    from llama_cpp import Llama

    _LLAMA_AVAILABLE = True
except ImportError:  # pragma: no cover
    logger.warning("llama-cpp-python not installed; SLM inference disabled")


class SLMEngine:
    """
    Low-level inference engine wrapping a local GGUF model.

    Features:
    - Lazy loading (model loaded on first use)
    - Async generation via thread pool
    - Graceful degradation when model is unavailable
    - Thread-safe inference queue
    """

    # Limit concurrent generations to avoid memory spikes with small models
    _INFERENCE_SEMAPHORE = threading.BoundedSemaphore(1)

    def __init__(
        self,
        model_path: str,
        context_size: int = 2048,
        threads: int = 4,
        gpu_layers: int = 0,
    ):
        """
        Initialize the SLM engine.

        Args:
            model_path: Path to GGUF model file.
            context_size: Maximum context window in tokens.
            threads: CPU threads for inference.
            gpu_layers: Number of layers to offload to GPU (0 = CPU only).
        """
        self._model_path = model_path
        self._context_size = context_size
        self._threads = threads
        self._gpu_layers = gpu_layers
        self._model: Any = None
        self._model_loaded = False
        self._load_failed = False
        self._load_error: str | None = None
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="slm-")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        """Whether the engine can perform inference."""
        if not _LLAMA_AVAILABLE:
            return False
        if self._load_failed:
            return False
        if self._model_loaded:
            return True
        # Model not loaded yet — try lazy load
        return self._try_lazy_load()

    @property
    def model_loaded(self) -> bool:
        """Whether the model has been loaded into memory."""
        return self._model_loaded

    @property
    def load_error(self) -> str | None:
        """Error message if model loading failed."""
        return self._load_error

    def generate(
        self,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.1,
        stop: list[str] | None = None,
        top_p: float = 0.9,
    ) -> str:
        """
        Synchronous text generation.

        Args:
            prompt: Input prompt text.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature (0.0 = deterministic).
            stop: Stop sequences that end generation.
            top_p: Nucleus sampling parameter.

        Returns:
            Generated text, or empty string if unavailable.
        """
        if not self.available:
            return ""

        stop_sequences = stop or []
        try:
            with SLMEngine._INFERENCE_SEMAPHORE:
                result: dict = self._model.create_completion(  # type: ignore[union-attr]
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    stop=stop_sequences,
                    echo=False,
                )
            choices: list[dict] = result.get("choices", [])
            if not choices:
                return ""
            return choices[0].get("text", "").strip()

        except Exception as exc:
            logger.error(f"SLM generation error: {exc}")
            return ""

    async def generate_async(
        self,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.1,
        stop: list[str] | None = None,
        top_p: float = 0.9,
    ) -> str:
        """
        Asynchronous text generation.

        Offloads model inference to a thread pool so the async
        event loop is not blocked.

        Args:
            prompt: Input prompt text.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.
            stop: Stop sequences.
            top_p: Nucleus sampling parameter.

        Returns:
            Generated text, or empty string if unavailable.
        """
        if not self.available:
            return ""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            self.generate,
            prompt,
            max_tokens,
            temperature,
            stop,
            top_p,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _try_lazy_load(self) -> bool:
        """Attempt lazy model loading. Returns True on success."""
        if self._model_loaded:
            return True
        if not _LLAMA_AVAILABLE:
            self._load_failed = True
            self._load_error = "llama-cpp-python not installed"
            return False

        model_path = Path(self._model_path)
        if not model_path.exists():
            self._load_failed = True
            self._load_error = f"Model not found: {self._model_path}"
            logger.warning(self._load_error)
            return False

        try:
            logger.info(
                f"Loading SLM model: {self._model_path} "
                f"(ctx={self._context_size}, threads={self._threads})"
            )
            self._model = Llama(
                model_path=str(model_path),
                n_ctx=self._context_size,
                n_threads=self._threads,
                n_gpu_layers=self._gpu_layers,
                verbose=False,
            )
            self._model_loaded = True
            logger.info("SLM model loaded successfully")
            return True

        except Exception as exc:
            self._load_failed = True
            self._load_error = str(exc)
            logger.error(f"Failed to load SLM model: {exc}")
            return False

    def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.1,
        stop: list[str] | None = None,
        top_p: float = 0.9,
    ):
        """
        Stream tokens from llama-cpp completion.
        Yields generated text fragments in real-time.
        """
        if not self.available:
            yield ""
            return

        stop_sequences = stop or []
        try:
            with SLMEngine._INFERENCE_SEMAPHORE:
                response_stream = self._model.create_completion(  # type: ignore[union-attr]
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    stop=stop_sequences,
                    echo=False,
                    stream=True,
                )
                for chunk in response_stream:
                    choices = chunk.get("choices", [])
                    if choices:
                        text = choices[0].get("text", "")
                        if text:
                            yield text
        except Exception as exc:
            logger.error(f"SLM streaming completion error: {exc}")
            yield ""

    def shutdown(self) -> None:
        """Release model resources and thread pool."""
        self._executor.shutdown(wait=True)
        if self._model is not None:
            del self._model
            self._model = None
            self._model_loaded = False
        logger.info("SLM engine shut down")