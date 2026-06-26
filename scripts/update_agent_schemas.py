import os
import json
import sys
import urllib.request

# Add agent folders to sys.path to enable imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../agents"))

from ansible_agent.tools import AnsibleValidator
from terraform_agent.tools import TerraformAuditor

def load_registry():
    path = os.path.join(os.path.dirname(__file__), "agent_resource_registry.json")
    with open(path, "r") as f:
        return json.load(f)

def update_ansible_schemas(registry):
    print("Updating Ansible agent schemas...")
    collections = registry.get("ansible", {}).get("collections", {})
    for collection, info in collections.items():
        for module in info.get("modules", []):
            module_name = f"{collection}.{module}"
            print(f"Refreshing schema for Ansible module: {module_name}")
            schema = AnsibleValidator._fetch_and_parse_module_schema(module_name)
            if schema:
                AnsibleValidator._save_cached_module_schema(module_name, schema)
                print(f"  ✓ Successfully updated {module_name}")
            else:
                # Keep existing cache if update fails
                if AnsibleValidator._get_cached_module_schema(module_name):
                    print(f"  ⚠ Failed to fetch {module_name}, retaining current cache")
                else:
                    print(f"  ✗ Failed to fetch {module_name} (no cache exists)")

def update_terraform_schemas(registry):
    print("Updating Terraform agent schemas...")
    providers = registry.get("terraform", {}).get("providers", {})
    for provider, info in providers.items():
        for resource in info.get("resources", []):
            # Strip provider prefix if resource is fully qualified (e.g. aws_instance -> instance)
            res_type = resource
            if res_type.startswith(f"{provider}_"):
                res_type = res_type[len(provider)+1:]
                
            print(f"Refreshing schema for Terraform resource: {provider}_{res_type}")
            schema = TerraformAuditor._fetch_and_parse_schema(provider, res_type)
            if schema:
                TerraformAuditor._save_cached_schema(provider, res_type, schema)
                print(f"  ✓ Successfully updated {provider}_{res_type}")
            else:
                # Retain current cache if update fails
                if TerraformAuditor._get_cached_schema(provider, res_type):
                    print(f"  ⚠ Failed to fetch {provider}_{res_type}, retaining current cache")
                else:
                    print(f"  ✗ Failed to fetch {provider}_{res_type} (no cache exists)")

def update_github_actions_schemas(registry):
    print("Updating GitHub Actions agent schemas...")
    schemas = registry.get("github_actions", {}).get("schemas", {})
    cache_dir = os.path.join(os.path.dirname(__file__), "../agents/github_actions_agent/.schema_cache")
    os.makedirs(cache_dir, exist_ok=True)
    
    for schema_name, info in schemas.items():
        url = info.get("url")
        if url:
            print(f"Downloading JSON schema from: {url}")
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'AntigravityAgent/1.0'})
                with urllib.request.urlopen(req, timeout=10) as res:
                    data = json.loads(res.read().decode('utf-8'))
                    
                cache_path = os.path.join(cache_dir, f"{schema_name}.json")
                with open(cache_path, "w") as f:
                    json.dump(data, f, indent=2)
                print(f"  ✓ Successfully updated {schema_name}.json")
            except Exception as e:
                print(f"  ✗ Failed to update {schema_name}.json: {e}")

if __name__ == "__main__":
    registry = load_registry()
    update_ansible_schemas(registry)
    update_terraform_schemas(registry)
    update_github_actions_schemas(registry)
    print("Agent schema updates complete.")
