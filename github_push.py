"""
GitHub Push Module
Pushes generated CI/CD YAML files to a GitHub repository via the GitHub REST API.
No external libraries needed beyond the standard library — uses urllib only.
"""

import base64
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional


GITHUB_API = "https://api.github.com"


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class PushConfig:
    token: str           # GitHub Personal Access Token (classic or fine-grained)
    repo: str            # "owner/repo"  e.g. "acme-corp/my-service"
    branch: str = "main"
    target_folder: str = ".azuredevops"
    commit_message: str = "chore: add auto-generated CI/CD pipelines"


@dataclass
class FilePushResult:
    filename: str
    success: bool
    url: str = ""        # HTML URL of the file on GitHub
    action: str = ""     # "created" | "updated"
    error: str = ""


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_repo(repo_input: str) -> Optional[str]:
    """
    Accept any of:
      - owner/repo
      - https://github.com/owner/repo
      - https://github.com/owner/repo.git
    Returns "owner/repo" or None if unparseable.
    """
    repo_input = repo_input.strip().rstrip("/").removesuffix(".git")
    # Full URL
    m = re.match(r"https?://github\.com/([^/]+/[^/]+)$", repo_input)
    if m:
        return m.group(1)
    # Plain owner/repo
    if re.match(r"^[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+$", repo_input):
        return repo_input
    return None


def _api_request(method: str, url: str, token: str, payload: dict = None) -> dict:
    """Make an authenticated GitHub API request. Returns parsed JSON."""
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "PipelineGeneratorTool/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"GitHub API {e.code}: {body}") from e


def _get_file_sha(token: str, repo: str, path: str, branch: str) -> Optional[str]:
    """Return the blob SHA of an existing file, or None if it doesn't exist."""
    url = f"{GITHUB_API}/repos/{repo}/contents/{path}?ref={branch}"
    try:
        result = _api_request("GET", url, token)
        return result.get("sha")
    except RuntimeError as e:
        if "404" in str(e):
            return None
        raise


def _ensure_branch_exists(token: str, repo: str, branch: str):
    """Create the branch from the default branch if it doesn't exist."""
    # Check if branch exists
    try:
        _api_request("GET", f"{GITHUB_API}/repos/{repo}/git/ref/heads/{branch}", token)
        return  # already exists
    except RuntimeError as e:
        if "404" not in str(e):
            raise

    # Get default branch SHA
    repo_info = _api_request("GET", f"{GITHUB_API}/repos/{repo}", token)
    default_branch = repo_info.get("default_branch", "main")
    ref_info = _api_request(
        "GET", f"{GITHUB_API}/repos/{repo}/git/ref/heads/{default_branch}", token
    )
    sha = ref_info["object"]["sha"]

    # Create new branch
    _api_request(
        "POST",
        f"{GITHUB_API}/repos/{repo}/git/refs",
        token,
        {"ref": f"refs/heads/{branch}", "sha": sha},
    )


def push_file(
    token: str,
    repo: str,
    file_path: str,
    content: str,
    branch: str,
    commit_message: str,
) -> FilePushResult:
    """
    Create or update a single file in a GitHub repo.
    Returns a FilePushResult with success status and file URL.
    """
    filename = file_path.split("/")[-1]
    try:
        encoded = base64.b64encode(content.encode()).decode()
        existing_sha = _get_file_sha(token, repo, file_path, branch)

        payload = {
            "message": commit_message,
            "content": encoded,
            "branch": branch,
        }
        if existing_sha:
            payload["sha"] = existing_sha

        result = _api_request(
            "PUT",
            f"{GITHUB_API}/repos/{repo}/contents/{file_path}",
            token,
            payload,
        )

        html_url = result.get("content", {}).get("html_url", "")
        action = "updated" if existing_sha else "created"
        return FilePushResult(filename=filename, success=True, url=html_url, action=action)

    except Exception as exc:
        return FilePushResult(filename=filename, success=False, error=str(exc))


# ─── Public interface ──────────────────────────────────────────────────────────

def push_pipelines(
    ci_yaml: str,
    cd_yaml: str,
    push_config: PushConfig,
) -> list[FilePushResult]:
    """
    Push ci.yml and cd.yml into the target repo folder on the specified branch.
    Returns a list of FilePushResult (one per file).
    """
    repo = _parse_repo(push_config.repo)
    if not repo:
        return [
            FilePushResult("ci.yml", False, error="Invalid repo format. Use 'owner/repo' or a full GitHub URL."),
            FilePushResult("cd.yml", False, error="Invalid repo format."),
        ]

    folder = push_config.target_folder.strip("/")

    # Auto-create branch if it doesn't exist
    try:
        _ensure_branch_exists(push_config.token, repo, push_config.branch)
    except Exception as exc:
        return [
            FilePushResult("ci.yml", False, error=f"Branch setup failed: {exc}"),
            FilePushResult("cd.yml", False, error=f"Branch setup failed: {exc}"),
        ]

    results = []
    for filename, content in [("ci.yml", ci_yaml), ("cd.yml", cd_yaml)]:
        file_path = f"{folder}/{filename}" if folder else filename
        result = push_file(
            token=push_config.token,
            repo=repo,
            file_path=file_path,
            content=content,
            branch=push_config.branch,
            commit_message=push_config.commit_message,
        )
        results.append(result)

    return results


def validate_token_format(token: str) -> Optional[str]:
    """Basic format check. Returns error string or None if OK."""
    token = token.strip()
    if not token:
        return "Token cannot be empty."
    if not (token.startswith("ghp_") or token.startswith("github_pat_") or len(token) >= 20):
        return "Token doesn't look like a valid GitHub PAT. It should start with 'ghp_' or 'github_pat_'."
    return None


def validate_repo_format(repo: str) -> Optional[str]:
    """Returns error string or None if OK."""
    if not _parse_repo(repo):
        return "Use 'owner/repo' format or a full GitHub URL (https://github.com/owner/repo)."
    return None
