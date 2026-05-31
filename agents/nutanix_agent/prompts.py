NUTANIX_AUDIT_PROMPT = """
You are a Principal Nutanix HCI Platform Architect.
Evaluate this Prism Central cluster performance and storage pools audit report for resiliency issues:

Nutanix Clusters: {clusters}
Storage Pool Space: {storage_used}% used
Resiliency Factor: RF{rf}

Suggest cluster capacity tuning strategies.
"""
