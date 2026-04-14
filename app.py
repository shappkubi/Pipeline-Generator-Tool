"""
Pipeline Generator Tool – Complete Streamlit UI  (v1.3)
• Three dropdowns: App Type / Language / Deployment Type
• Auto-generates CI YAML + CD YAML  (9 CI combos × 4 CD targets)
• Output: Download ZIP / individual files  OR  Push to GitHub repository
"""

import streamlit as st
from generator import (
    PipelineConfig,
    generate_ci_yaml,
    generate_cd_yaml,
    build_zip,
    validate_app_name,
    detect_unreplaced_placeholders,
    APP_TYPES,
    LANGUAGES,
    DEPLOY_TYPES,
)
from github_push import (
    PushConfig,
    push_pipelines,
    validate_token_format,
    validate_repo_format,
)

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pipeline Generator Tool",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Global CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
.block-container { padding: 1.8rem 2.5rem 3rem; max-width: 1100px; }

/* ── Hero ── */
.hero {
    background: linear-gradient(135deg, #0078d4 0%, #003a70 100%);
    border-radius: 14px; padding: 2rem 2.4rem 1.8rem;
    margin-bottom: 2rem; display: flex; align-items: center; gap: 1.4rem;
}
.hero-icon { font-size: 2.8rem; line-height: 1; }
.hero-text h1 { color:#fff; font-size:1.75rem; margin:0 0 0.3rem; letter-spacing:-0.4px; }
.hero-text p  { color:#b8d9f5; font-size:0.88rem; margin:0; }

/* ── Step labels ── */
.step-label {
    font-size:0.7rem; font-weight:800; letter-spacing:0.1em;
    text-transform:uppercase; color:#0078d4;
    border-left:3px solid #0078d4; padding-left:0.5rem;
    margin:1.6rem 0 0.75rem;
}

/* ── Dropdown cards ── */
.dcard {
    background:#fff; border:1.5px solid #d0e6f7; border-radius:10px;
    padding:0.9rem 1rem 0.55rem; margin-bottom:0.3rem;
    box-shadow:0 1px 4px rgba(0,0,0,.05); transition:border-color .18s;
}
.dcard:hover { border-color:#0078d4; }
.dcard-title { font-size:0.68rem; font-weight:800; letter-spacing:0.09em;
    text-transform:uppercase; color:#0078d4; margin-bottom:0.22rem; }
.dcard-hint  { font-size:0.73rem; color:#777; margin-bottom:0.15rem; }

/* ── Deploy-type badges (shown in dcard) ── */
.badge {
    display:inline-block; font-size:0.65rem; font-weight:700;
    border-radius:10px; padding:1px 8px; margin:1px;
    background:#e3f2fd; color:#0078d4;
}
.badge-onprem  { background:#fff3e0; color:#e65100; }
.badge-cloud   { background:#e8f5e9; color:#2e7d32; }
.badge-k8s     { background:#ede7f6; color:#4a148c; }
.badge-ansible { background:#fce4ec; color:#880e4f; }

/* ── Generate button ── */
div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg,#0078d4,#005a9e) !important;
    color:#fff !important; border:none !important; border-radius:9px !important;
    padding:0.7rem 2rem !important; font-size:1.02rem !important;
    font-weight:700 !important; width:100%;
    box-shadow:0 2px 10px rgba(0,120,212,.28);
}
div[data-testid="stButton"] > button[kind="primary"]:hover { opacity:.87; }

/* ── YAML viewer ── */
.yaml-box {
    background:#1e1e1e; border-radius:9px; padding:1.1rem 1.3rem;
    font-family:'Consolas','Courier New',monospace; font-size:0.76rem;
    color:#d4d4d4; max-height:390px; overflow-y:auto;
    border:1px solid #333; white-space:pre; line-height:1.55;
    margin-bottom:0.5rem;
}

/* ── Result banner ── */
.result-banner {
    background:#e8f5e9; border:1.5px solid #66bb6a; border-radius:10px;
    padding:0.85rem 1.3rem; text-align:center;
    font-size:0.95rem; color:#2e7d32; font-weight:700; margin-bottom:1.2rem;
}

/* ── Push result rows ── */
.push-ok {
    background:#e8f5e9; border-radius:7px; border-left:4px solid #43a047;
    padding:0.7rem 1rem; margin-bottom:0.4rem; font-size:0.85rem; color:#1b5e20;
}
.push-ok a { color:#0078d4; text-decoration:none; font-weight:600; }
.push-fail {
    background:#ffebee; border-radius:7px; border-left:4px solid #e53935;
    padding:0.7rem 1rem; margin-bottom:0.4rem; font-size:0.85rem; color:#7f0000;
}

/* ── Info / warn / tip boxes ── */
.warn-box {
    background:#fff8e1; border-left:4px solid #ffa726;
    padding:0.7rem 1rem; border-radius:0 7px 7px 0;
    font-size:0.81rem; color:#6d4c00; margin-bottom:0.8rem;
}
.tip-box {
    background:#f0f7ff; border-left:4px solid #0078d4;
    padding:0.65rem 1rem; border-radius:0 7px 7px 0;
    font-size:0.82rem; color:#004578; margin-top:1rem;
}
.ansible-info {
    background:#fce4ec; border-left:4px solid #e91e63;
    padding:0.7rem 1rem; border-radius:0 7px 7px 0;
    font-size:0.8rem; color:#880e4f; margin-bottom:0.6rem;
}
.section-hr { border:none; border-top:1.5px solid #e5eef7; margin:1.6rem 0; }

/* ── Download area ── */
.dl-heading { font-size:0.82rem; font-weight:700; color:#333; margin:1rem 0 0.45rem; }

/* labels */
label { font-weight:600 !important; color:#1a1a1a !important; font-size:0.88rem !important; }
</style>
""", unsafe_allow_html=True)

# ─── Hero ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-icon">⚙️</div>
  <div class="hero-text">
    <h1>Pipeline Generator Tool</h1>
    <p>Select your stack → auto-generate CI + CD YAML → download or push straight to your GitHub repo.</p>
  </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 ── THREE CORE DROPDOWNS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="step-label">Step 1 — Choose your stack</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="dcard">
      <div class="dcard-title">🗂 Application Type</div>
      <div class="dcard-hint">What kind of app are you deploying?</div>
      <span class="badge">Frontend App</span>
      <span class="badge">Function App</span>
      <span class="badge">Web App / MVC</span>
    </div>
    """, unsafe_allow_html=True)
    app_type = st.selectbox(
        "Application Type",
        options=APP_TYPES,
        index=0,
        label_visibility="collapsed",
        key="app_type",
    )

with col2:
    st.markdown("""
    <div class="dcard">
      <div class="dcard-title">💻 Language</div>
      <div class="dcard-hint">Framework / runtime?</div>
      <span class="badge">.NET</span>
      <span class="badge">Python</span>
      <span class="badge">Node</span>
    </div>
    """, unsafe_allow_html=True)
    language = st.selectbox(
        "Language",
        options=LANGUAGES,
        index=0,
        label_visibility="collapsed",
        key="language",
    )

with col3:
    st.markdown("""
    <div class="dcard">
      <div class="dcard-title">🚀 Deployment Type</div>
      <div class="dcard-hint">Where does it deploy?</div>
      <span class="badge badge-onprem">IIS On-Prem</span>
      <span class="badge badge-k8s">AKS</span>
      <span class="badge badge-cloud">Azure</span>
      <span class="badge badge-ansible">Ansible On-Prem</span>
    </div>
    """, unsafe_allow_html=True)
    deploy_type = st.selectbox(
        "Deployment Type",
        options=DEPLOY_TYPES,
        index=0,
        label_visibility="collapsed",
        key="deploy_type",
    )

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 ── APP NAME + DEPLOYMENT-SPECIFIC DETAILS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="step-label">Step 2 — App &amp; environment details</div>',
            unsafe_allow_html=True)

left, right = st.columns(2)

with left:
    app_name = st.text_input(
        "Application Name",
        value="my-app",
        help="Used in artifact names, deployment targets, and commit messages.",
    )

# initialise all fields
resource_group = azure_service_conn = ""
iis_server = iis_site_name = ""
container_registry = aks_cluster_name = ""
ansible_inventory = ansible_playbook = ansible_user = ansible_hosts_group = ""

# ── IIS ──────────────────────────────────────────────────────────────────────
if deploy_type == "IIS (On-Prem)":
    with left:
        iis_server    = st.text_input("IIS Server Hostname", value="my-iis-server.corp.com")
    with right:
        iis_site_name = st.text_input("IIS Site Name", value=app_name or "Default Web Site")

# ── AKS ──────────────────────────────────────────────────────────────────────
elif deploy_type == "AKS (Kubernetes)":
    with left:
        resource_group   = st.text_input("Azure Resource Group", value="rg-myapp-dev")
        aks_cluster_name = st.text_input("AKS Cluster Name",     value="my-aks-cluster")
    with right:
        azure_service_conn = st.text_input("Azure Service Connection", value="AzureServiceConnection")
        container_registry = st.text_input("Container Registry (ACR)", value="myregistry.azurecr.io")

# ── Azure App Service ─────────────────────────────────────────────────────────
elif deploy_type == "Azure App Service":
    with left:
        resource_group     = st.text_input("Azure Resource Group",    value="rg-myapp-dev")
    with right:
        azure_service_conn = st.text_input("Azure Service Connection", value="AzureServiceConnection")

# ── Ansible (On-Prem) ─────────────────────────────────────────────────────────
elif deploy_type == "Ansible (On-Prem)":
    st.markdown("""
    <div class="ansible-info">
    🔴 <b>Ansible deployment</b> — the generated CD pipeline uses SSH keys stored as Azure DevOps
    secure files &amp; secret variables (<code>ANSIBLE_SSH_PUBLIC_KEY</code>,
    <code>ANSIBLE_KNOWN_HOSTS</code>). Store these in your pipeline's variable group before running.
    </div>
    """, unsafe_allow_html=True)
    with left:
        ansible_inventory    = st.text_input("Inventory File Path",   value="inventories/hosts.ini")
        ansible_user         = st.text_input("SSH Deploy User",        value="deploy")
    with right:
        ansible_playbook     = st.text_input("Playbook File Path",     value="playbooks/deploy.yml")
        ansible_hosts_group  = st.text_input("Hosts Group Name",       value="app-servers")

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 ── OUTPUT METHOD TOGGLE
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="step-label">Step 3 — Choose output method</div>',
            unsafe_allow_html=True)

output_mode = st.radio(
    "Output method",
    options=["⬇️  Download YAML files", "🔀  Push to GitHub Repository"],
    horizontal=True,
    label_visibility="collapsed",
    key="output_mode",
)

github_token = github_repo = github_branch = github_folder = github_message = ""

if output_mode == "🔀  Push to GitHub Repository":
    with st.container():
        st.markdown("""
        <div style="background:#f8fafd;border:1.5px solid #d0e6f7;border-radius:10px;
                    padding:1.1rem 1.3rem 0.5rem;margin-bottom:0.3rem;">
        """, unsafe_allow_html=True)
        gh1, gh2 = st.columns(2)
        with gh1:
            github_token = st.text_input(
                "🔑 GitHub Personal Access Token (PAT)",
                type="password",
                placeholder="ghp_xxxxxxxxxxxxxxxxxxxx",
                help="Needs 'Contents: write' on the target repo.",
            )
            github_repo = st.text_input(
                "📁 Repository",
                placeholder="owner/repo  or  https://github.com/owner/repo",
            )
        with gh2:
            github_branch = st.text_input(
                "🌿 Branch",
                value="main",
                help="Auto-created from the default branch if it doesn't exist.",
            )
            github_folder = st.text_input(
                "📂 Target Folder in Repo",
                value=".azuredevops",
            )
        github_message = st.text_input(
            "💬 Commit Message",
            value=f"chore: add auto-generated CI/CD pipelines for {app_name or 'app'}",
        )
        st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4 ── GENERATE BUTTON
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="step-label">Step 4 — Generate</div>', unsafe_allow_html=True)
generate_btn = st.button("⚡  Generate CI + CD Pipelines", type="primary")

# ═══════════════════════════════════════════════════════════════════════════════
# RESULTS
# ═══════════════════════════════════════════════════════════════════════════════
if generate_btn:

    # ── Validate app name ─────────────────────────────────────────────────────
    name_err = validate_app_name(app_name)
    if name_err:
        st.error(f"❌ {name_err}")
        st.stop()

    # ── Build config ──────────────────────────────────────────────────────────
    config = PipelineConfig(
        app_name=app_name.strip(),
        app_type=app_type,
        language=language,
        deploy_type=deploy_type,
        # IIS
        iis_server=iis_server         or "YOUR-IIS-SERVER",
        iis_site_name=iis_site_name   or app_name,
        # AKS / Azure
        container_registry=container_registry  or "yourregistry.azurecr.io",
        aks_cluster_name=aks_cluster_name       or "your-aks-cluster",
        resource_group=resource_group           or "your-resource-group",
        azure_service_connection=azure_service_conn or "your-azure-service-connection",
        # Ansible
        ansible_inventory=ansible_inventory   or "inventories/hosts.ini",
        ansible_playbook=ansible_playbook     or "playbooks/deploy.yml",
        ansible_user=ansible_user             or "deploy",
        ansible_hosts_group=ansible_hosts_group or "app-servers",
    )

    # ── Generate ──────────────────────────────────────────────────────────────
    with st.spinner("⚙️  Generating pipelines…"):
        try:
            ci_yaml = generate_ci_yaml(config)
            cd_yaml = generate_cd_yaml(config)
        except Exception as exc:
            st.error(f"❌ Generation failed: {exc}")
            st.stop()

    st.markdown("<hr class='section-hr'>", unsafe_allow_html=True)

    # ── Banner ────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="result-banner">
        ✅ &nbsp; Pipelines ready for <b>{app_name}</b>
        &nbsp;·&nbsp; {app_type}
        &nbsp;·&nbsp; {language}
        &nbsp;·&nbsp; {deploy_type}
    </div>
    """, unsafe_allow_html=True)

    # ── Unreplaced-placeholder warnings ───────────────────────────────────────
    remaining = list(set(
        detect_unreplaced_placeholders(ci_yaml) +
        detect_unreplaced_placeholders(cd_yaml)
    ))
    if remaining:
        tokens = " &nbsp;·&nbsp; ".join(f"<code>{p}</code>" for p in remaining)
        st.markdown(f"""
        <div class="warn-box">
        ⚠️ <b>Placeholders still needing values:</b> {tokens}<br>
        Fill these directly in the YAML, or re-run with Step 2 filled in.
        </div>
        """, unsafe_allow_html=True)

    # ── YAML preview tabs ─────────────────────────────────────────────────────
    tab_ci, tab_cd = st.tabs([
        "📄  ci.yml  —  Build · Test · Scan",
        "🚀  cd.yml  —  Deploy · Health Check",
    ])
    with tab_ci:
        st.caption(f"CI pipeline for **{language}** — restore ▸ build ▸ test ▸ security scan ▸ publish artifact")
        safe_ci = ci_yaml.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        st.markdown(f'<div class="yaml-box">{safe_ci}</div>', unsafe_allow_html=True)
    with tab_cd:
        label_cd = {
            "IIS (On-Prem)":     "IIS — stop pool ▸ MSDeploy ▸ start pool ▸ health check",
            "AKS (Kubernetes)":  "AKS — Docker build ▸ ACR push ▸ Helm upgrade ▸ rollout check",
            "Azure App Service": "Azure — staging slot ▸ health check ▸ slot swap ▸ prod verify",
            "Ansible (On-Prem)": "Ansible — syntax check ▸ run playbook ▸ health check ▸ auto-rollback on fail",
        }.get(deploy_type, deploy_type)
        st.caption(f"CD pipeline targeting **{deploy_type}** — {label_cd}")
        safe_cd = cd_yaml.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        st.markdown(f'<div class="yaml-box">{safe_cd}</div>', unsafe_allow_html=True)

    st.markdown("<hr class='section-hr'>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # OUTPUT A — DOWNLOAD
    # ═══════════════════════════════════════════════════════════════════════════
    if output_mode == "⬇️  Download YAML files":
        st.markdown('<div class="dl-heading">📥 Download your pipelines</div>',
                    unsafe_allow_html=True)

        zip_bytes = build_zip({"ci.yml": ci_yaml, "cd.yml": cd_yaml}, app_name)

        dl_zip, dl_ci, dl_cd = st.columns([3, 1.4, 1.4])
        with dl_zip:
            st.download_button(
                label=f"⬇️  Download ZIP  ({app_name}-pipelines.zip)",
                data=zip_bytes,
                file_name=f"{app_name}-pipelines.zip",
                mime="application/zip",
                type="primary",
                use_container_width=True,
            )
        with dl_ci:
            st.download_button(
                label="⬇️  ci.yml only",
                data=ci_yaml,
                file_name="ci.yml",
                mime="text/yaml",
                use_container_width=True,
            )
        with dl_cd:
            st.download_button(
                label="⬇️  cd.yml only",
                data=cd_yaml,
                file_name="cd.yml",
                mime="text/yaml",
                use_container_width=True,
            )

        next_step = {
            "IIS (On-Prem)":
                "Drop the files into <code>.azuredevops/</code> in your repo. "
                "The CD pipeline requires a <b>Windows self-hosted agent</b> with IIS + Web Deploy installed.",
            "AKS (Kubernetes)":
                "Drop into <code>.azuredevops/</code>. Ensure your Helm chart exists at "
                "<code>./helm/{app_name}/</code> and your ACR is linked to the AKS cluster.",
            "Azure App Service":
                "Drop into <code>.azuredevops/</code>. Create a <b>staging slot</b> on your App Service "
                "before the first CD run.",
            "Ansible (On-Prem)":
                "Drop into <code>.azuredevops/</code>. Add <code>ANSIBLE_SSH_PUBLIC_KEY</code> and "
                "<code>ANSIBLE_KNOWN_HOSTS</code> as secret pipeline variables before running.",
        }.get(deploy_type, "Drop the files into <code>.azuredevops/</code> in your repo.")

        st.markdown(f'<div class="tip-box">💡 <b>Next step:</b> {next_step}</div>',
                    unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # OUTPUT B — PUSH TO GITHUB
    # ═══════════════════════════════════════════════════════════════════════════
    else:
        st.markdown("### 🔀 Pushing to GitHub…")

        push_errors = []
        if err := validate_token_format(github_token):
            push_errors.append(f"**Token:** {err}")
        if err := validate_repo_format(github_repo):
            push_errors.append(f"**Repo:** {err}")
        if not github_branch.strip():
            push_errors.append("**Branch** cannot be empty.")

        if push_errors:
            for e in push_errors:
                st.error(e)
            st.stop()

        push_cfg = PushConfig(
            token=github_token.strip(),
            repo=github_repo.strip(),
            branch=github_branch.strip() or "main",
            target_folder=github_folder.strip() or ".azuredevops",
            commit_message=github_message.strip() or
                f"chore: add auto-generated CI/CD pipelines for {app_name}",
        )

        with st.spinner(f"Pushing to `{push_cfg.repo}` on branch `{push_cfg.branch}`…"):
            results = push_pipelines(ci_yaml, cd_yaml, push_cfg)

        all_ok = all(r.success for r in results)

        for res in results:
            if res.success:
                st.markdown(f"""
                <div class="push-ok">
                ✅ &nbsp; <b>{res.filename}</b> &nbsp;{res.action}
                &nbsp;→&nbsp; <a href="{res.url}" target="_blank">View on GitHub ↗</a>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="push-fail">
                ❌ &nbsp; <b>{res.filename}</b> failed: {res.error}
                </div>
                """, unsafe_allow_html=True)

        if all_ok:
            folder = push_cfg.target_folder.strip("/")
            st.markdown(f"""
            <div class="tip-box">
            🎉 Both files are live in <b>{push_cfg.repo}</b>
            under <code>{folder}/</code> on branch <code>{push_cfg.branch}</code>.<br>
            <b>Next:</b> In Azure DevOps, create two new pipelines pointing at
            <code>{folder}/ci.yml</code> and <code>{folder}/cd.yml</code>.
            </div>
            """, unsafe_allow_html=True)

            zip_bytes = build_zip({"ci.yml": ci_yaml, "cd.yml": cd_yaml}, app_name)
            st.download_button(
                label="⬇️  Also download ZIP as local backup",
                data=zip_bytes,
                file_name=f"{app_name}-pipelines.zip",
                mime="application/zip",
            )

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("<hr class='section-hr'>", unsafe_allow_html=True)

# Summary of all supported options
with st.expander("📋 Supported dropdown options", expanded=False):
    ec1, ec2, ec3 = st.columns(3)
    with ec1:
        st.markdown("**🗂 App Types**")
        for a in APP_TYPES:
            st.markdown(f"- {a}")
    with ec2:
        st.markdown("**💻 Languages**")
        for l in LANGUAGES:
            st.markdown(f"- {l}")
    with ec3:
        st.markdown("**🚀 Deployment Targets**")
        for d in DEPLOY_TYPES:
            st.markdown(f"- {d}")

st.markdown(
    "<small style='color:#aaa;'>Pipeline Generator Tool &nbsp;·&nbsp; v1.3 &nbsp;·&nbsp;"
    " Azure DevOps YAML &nbsp;·&nbsp; Built with Streamlit</small>",
    unsafe_allow_html=True,
)
