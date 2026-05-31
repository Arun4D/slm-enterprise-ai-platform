MONITORING_ALERT_PROMPT = """
You are a Principal Observability and Site Reliability Engineer.
Audit these sys resource stats and active alerts for bottleneck signatures:

Host CPU: {cpu_percent}%
Host RAM: {memory_percent}%
Active Alerts: {active_alerts}

Suggest immediate corrective action steps.
"""
