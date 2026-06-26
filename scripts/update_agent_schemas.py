import os
import json
import sys

# Add agent folders to sys.path to enable imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../agents"))

from ansible_agent.tools import AnsibleValidator
from terraform_agent.tools import TerraformAuditor

def update_ansible_schemas():
    print("Updating Ansible agent schemas...")
    cache_dir = os.path.join(os.path.dirname(__file__), "../agents/ansible_agent/.schema_cache")
    if not os.path.exists(cache_dir):
        print("Ansible schema cache directory not found.")
        return
        
    for filename in os.listdir(cache_dir):
        if filename.endswith(".json") and not filename.startswith("_"):
            module_name = filename[:-5]
            print(f"Refreshing schema for Ansible module: {module_name}")
            schema = AnsibleValidator._fetch_and_parse_module_schema(module_name)
            if schema:
                AnsibleValidator._save_cached_module_schema(module_name, schema)
                print(f"  ✓ Successfully updated {module_name}")
            else:
                print(f"  ✗ Failed to update {module_name}")

def update_terraform_schemas():
    print("Updating Terraform agent schemas...")
    cache_dir = os.path.join(os.path.dirname(__file__), "../agents/terraform_agent/.schema_cache")
    if not os.path.exists(cache_dir):
        print("Terraform schema cache directory not found.")
        return
        
    for filename in os.listdir(cache_dir):
        if filename.endswith(".json") and not filename.startswith("_"):
            # Format: {provider}_{resource_type}.json
            parts = filename[:-5].split("_", 1)
            if len(parts) == 2:
                provider, resource_type = parts
                print(f"Refreshing schema for Terraform resource: {provider}_{resource_type}")
                schema = TerraformAuditor._fetch_and_parse_schema(provider, resource_type)
                if schema:
                    TerraformAuditor._save_cached_schema(provider, resource_type, schema)
                    print(f"  ✓ Successfully updated {provider}_{resource_type}")
                else:
                    print(f"  ✗ Failed to update {provider}_{resource_type}")

if __name__ == "__main__":
    update_ansible_schemas()
    update_terraform_schemas()
    print("Agent schema updates complete.")
