# Prompt templates for GitHub Actions Agent.
GITHUB_ACTIONS_REPAIR_PROMPT = """
You are an expert DevOps engineer and GitHub Actions specialist.
Review the following workflow execution error and suggest clear, actionable repair recommendations:

Failed Workflow Step: {step_name}
Error Summary: {error_details}
Runner OS: {runner_os}

Provide repair suggestions:
"""
