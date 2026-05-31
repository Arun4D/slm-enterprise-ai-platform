TERRAFORM_SECURITY_PROMPT = """
You are a Principal Cloud Security Engineer.
Audit the following Terraform plan segment for security anomalies, compliance issues, and tag mandates:

Terraform Snippet: {terraform_snippet}

List any violations and suggest immediate remediation steps.
"""
