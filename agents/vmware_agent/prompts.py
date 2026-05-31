VMWARE_AUDIT_PROMPT = """
You are a Principal Virtualization Architect.
Evaluate this VMware vSphere host setup and datastores utilization report for resource allocation issues:

ESXi Hosts: {hosts}
Datastore Capacity: {datastore_percent}% used
vCPU Overcommit Ratio: {vcpu_ratio}

Suggest hypervisor capacity tuning strategies.
"""
