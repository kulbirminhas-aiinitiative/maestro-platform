#!/usr/bin/env python3
import os
import subprocess
import sys

class JiraConfig:
    CONFIG_FILE = "/home/ec2-user/projects/maestro-frontend-production/.jira-config"
    def __init__(self):
        self.config_values = {}
        if os.path.exists(self.CONFIG_FILE):
            with open(self.CONFIG_FILE, 'r') as f:
                for line in f:
                    if '=' in line:
                        k, v = line.strip().split('=', 1)
                        self.config_values[k.strip()] = v.strip()
        self.base_url = os.environ.get('JIRA_BASE_URL', self.config_values.get('JIRA_BASE_URL', 'https://fifth9.atlassian.net'))
        self.email = os.environ.get('JIRA_EMAIL', self.config_values.get('JIRA_EMAIL', ''))
        self.api_token = os.environ.get('JIRA_API_TOKEN', self.config_values.get('JIRA_API_TOKEN', ''))
        self.project_key = os.environ.get('JIRA_PROJECT_KEY', self.config_values.get('JIRA_PROJECT_KEY', 'MD'))

c = JiraConfig()

epic_key = "MD-2845"

print(f"Resuming gap_to_jira.py for scope 'core' linked to {epic_key}...")

cmd = [
    "python3",
    "src/maestro_hive/core/self_reflection/gap_to_jira.py",
    "--scope", "core",
    "--parent-epic", epic_key
]

env = os.environ.copy()
env['JIRA_BASE_URL'] = c.base_url
env['JIRA_EMAIL'] = c.email
env['JIRA_API_TOKEN'] = c.api_token
env['JIRA_PROJECT_KEY'] = c.project_key

# Run without capturing output so we can see progress and it doesn't buffer
result = subprocess.run(cmd, env=env)

if result.returncode != 0:
    print("gap_to_jira.py failed!")
    sys.exit(result.returncode)

print("Done.")
