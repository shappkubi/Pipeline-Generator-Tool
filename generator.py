"""
Pipeline Generator Engine
Reads parameterized YAML templates and replaces placeholders with user-supplied values.
"""

import os
import re
import zipfile
import io
from dataclasses import dataclass, field
from typing import Dict, Optional


# ─── Template directory paths ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
CI_DIR = os.path.join(TEMPLATES_DIR, "ci")
CD_DIR = os.path.join(TEMPLATES_DIR, "cd")

# ─── Supported options ────────────────────────────────────────────────────────
APP_TYPES = [
    "Frontend App",
    "Function App",
    "Web App / MVC",
]
LANGUAGES = [".NET", "Python", "Node"]
DEPLOY_TYPES = [
    "IIS (On-Prem)",
    "AKS (Kubernetes)",
    "Azure App Service",
    "Ansible (On-Prem)",
]

# Maps friendly names → template filenames
LANGUAGE_MAP = {
    ".NET":   "dotnet",
    "Python": "python",
    "Node":   "node",
}

DEPLOY_MAP = {
    "IIS (On-Prem)":     "iis",
    "AKS (Kubernetes)":  "aks",
    "Azure App Service": "azure",
    "Ansible (On-Prem)": "ansible",
}


@dataclass
class PipelineConfig:
    app_name: str
    app_type: str
    language: str
    deploy_type: str
    # IIS fields
    iis_server: str = "YOUR-IIS-SERVER"
    iis_site_name: str = ""
    # AKS / Azure fields
    container_registry: str = "yourregistry.azurecr.io"
    aks_cluster_name: str = "your-aks-cluster"
    resource_group: str = "your-resource-group"
    azure_service_connection: str = "your-azure-service-connection"
    # Ansible fields
    ansible_inventory: str = "inventories/hosts.ini"
    ansible_playbook: str = "playbooks/deploy.yml"
    ansible_user: str = "deploy"
    ansible_hosts_group: str = "app-servers"

    def __post_init__(self):
        if not self.iis_site_name:
            self.iis_site_name = self.app_name

    def to_placeholder_map(self) -> Dict[str, str]:
        return {
            "{{APP_NAME}}":                self.app_name,
            "{{APP_TYPE}}":                self.app_type,
            "{{LANGUAGE}}":                self.language,
            "{{DEPLOY_TYPE}}":             self.deploy_type,
            # IIS
            "{{IIS_SERVER}}":              self.iis_server,
            "{{IIS_SITE_NAME}}":           self.iis_site_name,
            # AKS / Azure
            "{{CONTAINER_REGISTRY}}":      self.container_registry,
            "{{AKS_CLUSTER_NAME}}":        self.aks_cluster_name,
            "{{RESOURCE_GROUP}}":          self.resource_group,
            "{{AZURE_SERVICE_CONNECTION}}": self.azure_service_connection,
            # Ansible
            "{{ANSIBLE_INVENTORY}}":       self.ansible_inventory,
            "{{ANSIBLE_PLAYBOOK}}":        self.ansible_playbook,
            "{{ANSIBLE_USER}}":            self.ansible_user,
            "{{ANSIBLE_HOSTS_GROUP}}":     self.ansible_hosts_group,
        }


def load_template(path: str) -> str:
    """Load a YAML template file and return its contents."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def apply_placeholders(template: str, placeholder_map: Dict[str, str]) -> str:
    """Replace all {{PLACEHOLDER}} tokens in the template with real values."""
    result = template
    for placeholder, value in placeholder_map.items():
        result = result.replace(placeholder, value)
    return result


def detect_unreplaced_placeholders(yaml_text: str):
    """
    Return a list of any {{PLACEHOLDER}} tokens still present after substitution.
    Ignores Azure DevOps runtime expressions like ${{ parameters.xxx }} or
    ${{ variables.xxx }} which are valid YAML pipeline syntax (not our tokens).
    """
    # Match {{ ... }} but only when NOT preceded by $ (Azure DevOps expression syntax)
    raw = re.findall(r"(?<!\$)\{\{([^}]+)\}\}", yaml_text)
    # Our placeholders are UPPERCASE with underscores; filter out lowercase ADO expressions
    return [f"{{{{{token}}}}}" for token in raw if re.match(r"^[A-Z_]+$", token.strip())]


def generate_ci_yaml(config: PipelineConfig) -> str:
    """Generate the CI pipeline YAML for the selected language."""
    lang_key = LANGUAGE_MAP.get(config.language)
    if not lang_key:
        raise ValueError(f"Unsupported language: {config.language}")

    template_path = os.path.join(CI_DIR, f"{lang_key}.yml")
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"CI template not found: {template_path}")

    template = load_template(template_path)
    return apply_placeholders(template, config.to_placeholder_map())


def generate_cd_yaml(config: PipelineConfig) -> str:
    """Generate the CD pipeline YAML for the selected deployment target."""
    deploy_key = DEPLOY_MAP.get(config.deploy_type)
    if not deploy_key:
        raise ValueError(f"Unsupported deployment type: {config.deploy_type}")

    template_path = os.path.join(CD_DIR, f"{deploy_key}.yml")
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"CD template not found: {template_path}")

    template = load_template(template_path)
    return apply_placeholders(template, config.to_placeholder_map())


def generate_both(config: PipelineConfig) -> Dict[str, str]:
    """Generate both CI and CD YAML files and return them as a dict."""
    return {
        "ci.yml": generate_ci_yaml(config),
        "cd.yml": generate_cd_yaml(config),
    }


def build_zip(files: Dict[str, str], app_name: str) -> bytes:
    """
    Pack multiple YAML strings into an in-memory ZIP archive.
    Returns raw bytes suitable for Streamlit's download_button.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files.items():
            # Place files inside a named folder in the zip
            arcname = f"{app_name}-pipelines/{filename}"
            zf.writestr(arcname, content)
    buffer.seek(0)
    return buffer.read()


def validate_app_name(name: str) -> Optional[str]:
    """
    Validate the application name.
    Returns an error message string, or None if valid.
    """
    if not name or not name.strip():
        return "Application name cannot be empty."
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9\-_]{1,62}$", name.strip()):
        return (
            "App name must start with a letter, contain only letters/numbers/hyphens/underscores, "
            "and be 2–63 characters long."
        )
    return None


# ─── CLI quick-test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    cfg = PipelineConfig(
        app_name="my-app",
        app_type="Frontend App",
        language=".NET",
        deploy_type="Azure App Service",
        resource_group="rg-myapp-dev",
        azure_service_connection="AzureDevServiceConnection",
    )

    files = generate_both(cfg)
    for fname, content in files.items():
        print(f"\n{'='*60}")
        print(f"  {fname}")
        print('='*60)
        print(content[:800], "...[truncated]" if len(content) > 800 else "")

    # Check for unreplaced tokens
    for fname, content in files.items():
        remaining = detect_unreplaced_placeholders(content)
        if remaining:
            print(f"\n⚠  Unreplaced placeholders in {fname}: {remaining}")
        else:
            print(f"\n✅  {fname}: all placeholders resolved.")
