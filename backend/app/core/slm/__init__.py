"""
SLM (Small Language Model) abstraction layer.

Provides model loading, inference, and high-level services
for agent consumption. Supports GGUF models via llama-cpp-python.
"""

from app.core.slm.engine import SLMEngine
from app.core.slm.service import SLMService

__all__ = ["SLMEngine", "SLMService"]