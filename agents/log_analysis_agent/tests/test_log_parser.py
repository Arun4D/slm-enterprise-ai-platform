"""
Tests for log analysis agent.
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

# Import from agent package
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agents" / "log_analysis_agent"))

from tools.log_parser import LogParser, LogAnalyzer, LogSummarizer


@pytest.fixture
def sample_log_content():
    """Create sample log content."""
    return """[2024-01-15 10:00:00] INFO Application started
[2024-01-15 10:00:01] INFO Database connected
[2024-01-15 10:00:05] ERROR Failed to connect to service: Connection timeout
[2024-01-15 10:00:06] ERROR Connection refused on port 8080
[2024-01-15 10:00:10] WARNING Memory usage high: 85%
[2024-01-15 10:00:15] INFO Cache cleared successfully
[2024-01-15 10:00:20] ERROR Failed to connect to service: Connection timeout
"""


@pytest.fixture
def sample_json_log_content():
    """Create sample JSON log content."""
    return """{"timestamp": "2024-01-15T10:00:00Z", "level": "INFO", "message": "Started"}
{"timestamp": "2024-01-15T10:00:01Z", "level": "ERROR", "message": "Connection failed"}
{"timestamp": "2024-01-15T10:00:02Z", "level": "ERROR", "message": "Connection failed"}
"""


def test_log_parser_text_format(sample_log_content):
    """Test parsing plain text log format."""
    entries = LogParser.parse_text_log(sample_log_content)
    
    assert len(entries) > 0
    assert entries[0]["level"] in ["INFO", "ERROR", "WARNING"]
    assert entries[0]["message"] is not None


def test_log_parser_json_format(sample_json_log_content):
    """Test parsing JSON log format."""
    entries = LogParser.parse_json_log(sample_json_log_content)
    
    assert len(entries) == 3
    assert entries[0]["level"] == "INFO"


def test_log_analyzer_classification(sample_log_content):
    """Test log entry classification."""
    entries = LogParser.parse_text_log(sample_log_content)
    classified = LogAnalyzer.classify_entries(entries)
    
    assert "errors" in classified
    assert "warnings" in classified
    assert "info" in classified
    assert len(classified["errors"]) > 0


def test_log_analyzer_pattern_extraction(sample_log_content):
    """Test pattern extraction."""
    entries = LogParser.parse_text_log(sample_log_content)
    classified = LogAnalyzer.classify_entries(entries)
    patterns = LogAnalyzer.extract_patterns(classified["errors"])
    
    assert len(patterns) > 0
    assert patterns[0]["count"] >= 1


def test_log_analyzer_remediation():
    """Test remediation suggestion."""
    pattern = "Connection timeout to database"
    suggestion = LogAnalyzer.suggest_remediation(pattern)
    
    assert suggestion is not None
    assert len(suggestion) > 0


def test_log_summarizer(sample_log_content):
    """Test log summarization."""
    entries = LogParser.parse_text_log(sample_log_content)
    classified = LogAnalyzer.classify_entries(entries)
    patterns = LogAnalyzer.extract_patterns(classified["errors"])
    
    summary = LogSummarizer.summarize(classified, patterns, "test.log")
    
    assert "Overview" in summary
    assert "Error" in summary or "error" in summary.lower()
