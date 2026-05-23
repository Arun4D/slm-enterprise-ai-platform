"""
SLM Service — high-level API consumed by agents.

Provides: intent classification, remediation generation,
analysis summarization, and natural-language Q&A.

Every method degrades gracefully: returns None or a safe
fallback when the SLM engine is unavailable.
"""

import logging
from typing import Any

from app.core.slm.engine import SLMEngine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates — kept inline so the service is self-contained.
# Agents bring their own domain templates via prompts.py.
# ---------------------------------------------------------------------------

INTENT_CLASSIFICATION_PROMPT = """<|system|>
You are an intent classifier for an enterprise AI platform. 
Given a user query, classify it into EXACTLY ONE of these categories:
{agent_list}
Respond with ONLY the category name, nothing else.
<|end|>
<|user|>
{query}
<|end|>
<|assistant|>"""

REMEDIATION_PROMPT = """<|system|>
You are a senior SRE analyzing a log error pattern.
Given the error pattern and context, provide:
1. Root cause analysis (1-2 sentences)
2. Remediation steps (2-3 actionable items)
3. Prevention measures (1-2 suggestions)

Keep the total response under 200 words.
<|end|>
<|user|>
Error Pattern: {pattern}
Occurrence Count: {count}
Severity Level: {level}
Context: {context}
<|end|>
<|assistant|>"""

ANALYSIS_SUMMARY_PROMPT = """<|system|>
You are an expert log analyst. Summarize the following log analysis
results in a clear, actionable report. Include:
- Overall health assessment
- Top issues ranked by severity
- Recommended actions

Keep under 300 words.
<|end|>
<|user|>
Files Analyzed: {files_analyzed}
Total Entries: {total_entries}
Errors: {error_count}
Warnings: {warning_count}
Top Patterns: {patterns}
Application Status: {app_status}
<|end|>
<|assistant|>"""

QA_PROMPT = """<|system|>
You are an AI assistant answering questions about log analysis results.
Answer the user's question concisely using the provided context.
If the context doesn't contain the answer, say "I could not find that
information in the analyzed logs."

Keep the answer under 100 words.
<|end|>
<|user|>
Context: {context}
Question: {question}
<|end|>
<|assistant|>"""


class SLMService:
    """
    High-level SLM service for agent consumption.

    Wraps SLMEngine and exposes domain-specific methods:
    - classify_intent()
    - generate_remediation()
    - summarize_analysis()
    - answer_question()

    Every method degrades gracefully when the engine is unavailable:
    classify_intent returns None, and the text-generation methods
    return empty strings. Callers should always check for these
    sentinel values and fall back to deterministic logic.
    """

    def __init__(self, engine: SLMEngine):
        self._engine = engine

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        """Whether the SLM service can generate responses."""
        return self._engine.available

    def classify_intent_sync(
        self,
        query: str,
        agent_labels: list[tuple[str, str]],
    ) -> str | None:
        """
        Synchronous intent classification for use in non-async contexts
        (e.g., agent.can_handle() which is called from mixed sync/async code).

        Args:
            query: User's natural-language query.
            agent_labels: List of (agent_id, description) tuples.

        Returns:
            Agent id string if classified, None if unavailable/uncertain.
        """
        if not self.available or not query.strip():
            return None

        agent_list = "\n".join(
            f"- {aid}: {desc}" for aid, desc in agent_labels
        )
        prompt = INTENT_CLASSIFICATION_PROMPT.format(
            agent_list=agent_list,
            query=query.strip(),
        )
        result = self._engine.generate(
            prompt,
            max_tokens=32,
            temperature=0.0,
            stop=["<|end|>", "\n"],
        )

        if not result:
            return None

        result_clean = result.strip().lower()
        for aid, _desc in agent_labels:
            if aid.lower() in result_clean:
                return aid
        return None

    async def classify_intent(
        self,
        query: str,
        agent_labels: list[tuple[str, str]],
    ) -> str | None:
        """
        Classify a user query into one of the available agent categories.

        Args:
            query: User's natural-language query.
            agent_labels: List of (agent_id, description) tuples.

        Returns:
            Agent id string if classified, None if unavailable/uncertain.
        """
        if not self.available or not query.strip():
            return None

        agent_list = "\n".join(
            f"- {aid}: {desc}" for aid, desc in agent_labels
        )
        prompt = INTENT_CLASSIFICATION_PROMPT.format(
            agent_list=agent_list,
            query=query.strip(),
        )
        result = await self._engine.generate_async(
            prompt,
            max_tokens=32,
            temperature=0.0,
            stop=["<|end|>", "\n"],
        )

        if not result:
            return None

        # The model should return just the agent id; extract it
        result_clean = result.strip().lower()
        for aid, _desc in agent_labels:
            if aid.lower() in result_clean:
                return aid
        return None

    async def generate_remediation(
        self,
        pattern: str,
        count: int = 1,
        level: str = "ERROR",
        context: str = "",
    ) -> str:
        """
        Generate remediation suggestions for an error pattern.

        Args:
            pattern: The error pattern text.
            count: How many times it occurred.
            level: Severity level (ERROR, WARNING, etc.).
            context: Additional context from surrounding logs.

        Returns:
            Remediation text, or empty string if unavailable.
        """
        if not self.available:
            return ""

        prompt = REMEDIATION_PROMPT.format(
            pattern=pattern[:500],
            count=count,
            level=level,
            context=context[:300] or "No additional context available.",
        )
        return await self._engine.generate_async(
            prompt,
            max_tokens=256,
            temperature=0.3,
            stop=["<|end|>"],
        )

    async def summarize_analysis(self, analysis_data: dict[str, Any]) -> str:
        """
        Generate a natural-language summary of log analysis results.

        Args:
            analysis_data: Dict with keys matching ANALYSIS_SUMMARY_PROMPT
                           placeholders.

        Returns:
            Summary text, or empty string if unavailable.
        """
        if not self.available:
            return ""

        classified = analysis_data.get("classified_entries", {})
        patterns = analysis_data.get("patterns", [])
        pattern_str = "\n".join(
            f"- [{p.get('level', '?')}] {p.get('pattern', '')[:120]} "
            f"(×{p.get('count', 1)})"
            for p in patterns[:5]
        ) or "No patterns detected"

        app_status = analysis_data.get("application_status", {})
        app_str = (
            f"{app_status.get('application_name', 'Unknown')} "
            f"{'started' if app_status.get('application_started') else 'did not start'}"
        )

        prompt = ANALYSIS_SUMMARY_PROMPT.format(
            files_analyzed=analysis_data.get("files_analyzed", 0),
            total_entries=analysis_data.get("total_entries", 0),
            error_count=len(classified.get("errors", [])),
            warning_count=len(classified.get("warnings", [])),
            patterns=pattern_str,
            app_status=app_str,
        )
        return await self._engine.generate_async(
            prompt,
            max_tokens=384,
            temperature=0.3,
            stop=["<|end|>"],
        )

    async def answer_question(
        self,
        question: str,
        context: dict[str, Any],
    ) -> str:
        """
        Answer a natural-language question about log analysis results.

        Args:
            question: User's question.
            context: Analysis result context dict.

        Returns:
            Answer text, or empty string if unavailable.
        """
        if not self.available:
            return ""

        # Build compact context string
        app_status = context.get("application_status", {})
        context_parts = [
            f"Application: {app_status.get('application_name', 'unknown')}",
            f"Started: {app_status.get('application_started', False)}",
            f"Port: {app_status.get('port', 'unknown')}",
            f"PID: {app_status.get('pid', 'unknown')}",
            f"Startup time: {app_status.get('startup_seconds', 'unknown')}s",
            f"Files analyzed: {context.get('files_analyzed', 0)}",
            f"Total entries: {context.get('total_entries', 0)}",
        ]
        classified = context.get("classified_entries", {})
        context_parts.append(f"Errors: {len(classified.get('errors', []))}")
        context_parts.append(f"Warnings: {len(classified.get('warnings', []))}")

        prompt = QA_PROMPT.format(
            context="\n".join(context_parts),
            question=question.strip(),
        )
        return await self._engine.generate_async(
            prompt,
            max_tokens=128,
            temperature=0.1,
            stop=["<|end|>"],
        )

    def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.3,
        stop: list[str] | None = None,
    ):
        """Generic generator to stream raw tokens from the underlying model."""
        return self._engine.generate_stream(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop or ["<|end|>"],
        )

    def answer_question_stream(
        self,
        question: str,
        context_data: dict[str, Any],
    ):
        """Stream conversational answers to questions about analysis results."""
        if not self.available:
            yield "Local SLM model is offline. Fallback mode is active."
            return

        app_status = context_data.get("application_status", {})
        context_parts = [
            f"Application: {app_status.get('application_name', 'unknown')}",
            f"Started: {app_status.get('application_started', False)}",
            f"Port: {app_status.get('port', 'unknown')}",
            f"PID: {app_status.get('pid', 'unknown')}",
            f"Startup time: {app_status.get('startup_seconds', 'unknown')}s",
            f"Files analyzed: {context_data.get('files_analyzed', 0)}",
            f"Total entries: {context_data.get('total_entries', 0)}",
        ]
        classified = context_data.get("classified_entries", {})
        context_parts.append(f"Errors: {len(classified.get('errors', []))}")
        context_parts.append(f"Warnings: {len(classified.get('warnings', []))}")

        prompt = QA_PROMPT.format(
            context="\n".join(context_parts),
            question=question.strip(),
        )
        yield from self._engine.generate_stream(
            prompt,
            max_tokens=256,
            temperature=0.2,
            stop=["<|end|>"],
        )