"""
Prompt templates for the Log Analysis Agent.
"""

SYSTEM_PROMPT = """You are an expert log analysis assistant. Your role is to:
1. Analyze system logs for errors and anomalies
2. Identify patterns and root causes
3. Suggest remediation steps
4. Classify issues by severity

Always be thorough, provide specific examples, and focus on actionable insights.
"""

ANALYSIS_PROMPT = """Analyze the following log data:

File: {file_name}
Total Entries: {total_entries}
Errors: {error_count}
Warnings: {warning_count}

Top Error Patterns:
{patterns}

Classified Entries:
{classified}

Provide:
1. Root cause analysis
2. Affected systems
3. Recommended actions
4. Prevention measures
"""

REMEDIATION_PROMPT = """Based on the log analysis results:

Issue: {issue}
Pattern: {pattern}
Occurrence Count: {count}

Provide specific remediation steps and prevention measures.
"""
