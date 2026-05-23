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


def test_spring_boot_error_mapping_is_info():
    """Spring Boot /error route mappings are INFO startup logs, not failures."""
    content = """2017-08-08 17:12:32.420  INFO 19866 --- [           main] s.w.s.m.m.a.RequestMappingHandlerMapping : Mapped "{[/error]}" onto public org.springframework.http.ResponseEntity<java.util.Map<java.lang.String, java.lang.Object>> org.springframework.boot.autoconfigure.web.servlet.error.BasicErrorController.error(jakarta.servlet.http.HttpServletRequest)
2017-08-08 17:12:32.421  INFO 19866 --- [           main] s.w.s.m.m.a.RequestMappingHandlerMapping : Mapped "{[/error],produces=[text/html]}" onto public org.springframework.web.servlet.ModelAndView org.springframework.boot.autoconfigure.web.servlet.error.BasicErrorController.errorHtml(jakarta.servlet.http.HttpServletRequest,jakarta.servlet.http.HttpServletResponse)
"""
    entries = LogParser.parse_text_log(content)
    classified = LogAnalyzer.classify_entries(entries)

    assert len(classified["errors"]) == 0
    assert len(classified["warnings"]) == 0
    assert len(classified["info"]) == 2


def test_unstructured_error_text_is_still_error():
    """Lines without explicit level should still use error keywords."""
    entries = LogParser.parse_text_log("Unhandled exception while connecting to database")
    classified = LogAnalyzer.classify_entries(entries)

    assert len(classified["errors"]) == 1


def test_spring_boot_application_started_detection():
    """Detect Spring Boot startup completion without treating /error mapping as failure."""
    content = """2017-08-08 17:12:30.910  INFO 19866 --- [           main] s.f.SampleWebFreeMarkerApplication       : Starting SampleWebFreeMarkerApplication with PID 19866
2017-08-08 17:12:31.878  INFO 19866 --- [           main] o.s.b.w.embedded.tomcat.TomcatWebServer  : Tomcat initialized with port 8080 (http)
2017-08-08 17:12:32.420  INFO 19866 --- [           main] s.w.s.m.m.a.RequestMappingHandlerMapping : Mapped "{[/error]}" onto public org.springframework.boot.autoconfigure.web.servlet.error.BasicErrorController.error(jakarta.servlet.http.HttpServletRequest)
2017-08-08 17:12:32.744  INFO 19866 --- [           main] o.s.b.w.embedded.tomcat.TomcatWebServer  : Tomcat started on port 8080 (http)
2017-08-08 17:12:32.750  INFO 19866 --- [           main] s.f.SampleWebFreeMarkerApplication       : Started SampleWebFreeMarkerApplication in 2.172 seconds (JVM running for 2.479)
"""
    entries = LogParser.parse_text_log(content)
    classified = LogAnalyzer.classify_entries(entries)
    status = LogAnalyzer.detect_application_lifecycle(entries)

    assert len(classified["errors"]) == 0
    assert status["application_started"] is True
    assert status["application_name"] == "SampleWebFreeMarkerApplication"
    assert status["pid"] == 19866
    assert status["port"] == 8080
    assert status["startup_seconds"] == 2.172


def test_spring_boot_modern_startup_detection():
    """Detect Spring Boot 3 style startup and port(s) messages."""
    content = """2026-05-17 19:05:01.123  INFO 28432 --- [main] c.e.demo.DemoApplication                : Starting DemoApplication using Java 17.0.10 on My-Laptop with PID 28432
2026-05-17 19:05:02.542  INFO 28432 --- [main] o.s.b.w.embedded.tomcat.TomcatWebServer  : Tomcat initialized with port(s): 8080 (http)
2026-05-17 19:05:03.211  INFO 28432 --- [main] o.s.b.w.embedded.tomcat.TomcatWebServer  : Tomcat started on port(s): 9080 (http) with context path ''
2026-05-17 19:05:03.225  INFO 28432 --- [main] c.e.demo.DemoApplication                : Started DemoApplication in 2.654 seconds (JVM running for 3.12)
"""
    entries = LogParser.parse_text_log(content)
    status = LogAnalyzer.detect_application_lifecycle(entries)

    assert status["application_started"] is True
    assert status["application_name"] == "DemoApplication"
    assert status["pid"] == 28432
    assert status["port"] == 9080
    assert status["startup_seconds"] == 2.654


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


def test_log_parser_datetime_parsing():
    """Test parse_datetime utility."""
    parsed_1 = LogParser.parse_datetime("2026-05-17 19:05:01.123")
    assert parsed_1 is not None
    assert parsed_1.year == 2026
    assert parsed_1.month == 5
    assert parsed_1.day == 17
    assert parsed_1.hour == 19
    assert parsed_1.minute == 5
    assert parsed_1.second == 1

    parsed_2 = LogParser.parse_datetime("[2026-05-17T19:05:01Z]")
    assert parsed_2 is not None
    assert parsed_2.second == 1


def test_log_parser_datetime_filtering():
    """Test filter_entries_by_datetime utility."""
    entries = [
        {"timestamp": "2026-05-17 19:05:00", "message": "Log 1", "level": "INFO"},
        {"timestamp": "2026-05-17 19:06:00", "message": "Log 2", "level": "WARN"},
        {"timestamp": "2026-05-17 19:07:00", "message": "Log 3", "level": "ERROR"},
    ]
    
    # Range check
    filtered_1 = LogParser.filter_entries_by_datetime(entries, "2026-05-17 19:05:30", "2026-05-17 19:06:30")
    assert len(filtered_1) == 1
    assert filtered_1[0]["message"] == "Log 2"

    # Start-only check
    filtered_2 = LogParser.filter_entries_by_datetime(entries, "2026-05-17 19:06:00", None)
    assert len(filtered_2) == 2
    assert filtered_2[0]["message"] == "Log 2"
    assert filtered_2[1]["message"] == "Log 3"


def test_log_analyzer_warning_remediation():
    """Test SRE warning suggestions are returned successfully."""
    deprecated_suggestion = LogAnalyzer.suggest_remediation("Warning: basic-auth is deprecated.")
    assert "deprecation" in deprecated_suggestion.lower()

    retry_suggestion = LogAnalyzer.suggest_remediation("WARN --- Couchbase connection lost, retrying...")
    assert "transient" in retry_suggestion.lower() or "downstream" in retry_suggestion.lower()


def test_agent_query_datetime_extraction():
    """Test natural language datetime boundary extraction in LogAnalysisAgent."""
    from main import LogAnalysisAgent
    
    # 1. Test "before YYYY-MM-DD HH:MM"
    start, end = LogAnalysisAgent._extract_datetime_range("check warning logs before 2026-05-17 16:05")
    assert start is None
    assert end == "2026-05-17 16:05:59"

    # 2. Test "after YYYY-MM-DD HH:MM:SS"
    start, end = LogAnalysisAgent._extract_datetime_range("find errors after 2026-05-17 19:05:00")
    assert start == "2026-05-17 19:05:00"
    assert end is None


