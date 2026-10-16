# Security Automation Engineer — Take-Home Assignment

Welcome. This assignment is designed to reflect the real work of a Lead Security Automation Engineer: extending an existing service, identifying and assessing security risks, remediating them with code, and deploying it securely. There are no trick questions — we are evaluating your depth of knowledge, your judgment under constraints, and your ability to communicate risk.

**Estimated time: 4–6 hours.** We respect your time. If you find yourself going significantly over, scope down rather than rushing.

---

## Background

**VulnTracker** is a two-service system for managing vulnerability scan results:

- **`app/`** — Python/FastAPI REST API. Security teams use it to log findings, track remediation, and share reports with stakeholders.
- **`notify/`** — Node.js/Express notification service. Intended to dispatch webhook events to registered endpoints when scan records are created or updated.

Both services are working but imperfect internal prototypes. Neither has gone through a formal security review. The Python API calls the notification service in the background whenever a scan is created or updated — start both services to see the full flow.

---

## Getting Started

**Create your own repository for this assignment.** Do not fork — your solution must be in a fresh repo. You may use the starter code as a base, but your work must be in your own repo.

```bash
# 1. Clone the assignment repo locally
git clone https://github.com/cloudtriquetra/asa-assignment.git
cd asa-assignment

# 2. Point it at your own new GitHub repo (create one first at github.com)
git remote set-url origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

From here, work on your own repo and share its URL when you submit.

**Requirements:** Python 3.11 (exactly — see CI), Node.js 20+, Docker

**Python API (`app/`)**

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

The API must be started from inside the `app/` directory — the modules use bare imports and won't resolve from the repo root:

```bash
cd app
uvicorn main:app --reload
```

Available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

Run the Python test suite from the **repo root**:

```bash
pytest tests/ -v
```

**Notification Service (`notify/`)**

```bash
cd notify
npm install
npm start
```

Available at `http://localhost:3001`.

Run the Node.js test suite (stop the notify service first if it is running — the test suite starts its own server on the same port):

```bash
cd notify
npm test
```

---

## Your Tasks

### Task 1 — Extend the App _(~1–1.5 hrs)_

Implement the **"Shared Report Link"** feature:

> As a VulnTracker user, I want to share a specific scan result with an external stakeholder (e.g. a customer or auditor) via a unique link. The link must expire after **24 hours** and must support **optional password protection**.

Add the following endpoints to the app:

| Method | Path                     | Auth          | Description                                                                                                              |
| ------ | ------------------------ | ------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `POST` | `/scans/{scan_id}/share` | Bearer token  | Generate a share token for a scan. Accepts optional `password` in the request body. Returns `{ "share_url": "..." }`     |
| `GET`  | `/share/{token}`         | None (public) | Return the scan data if the token is valid and not expired. If password-protected, require a `password` query parameter. |

Implementation choices are yours. We will read and evaluate the code you write here — including the security properties of your implementation. For the `share_url` value, use the incoming request's host, or hard-code `http://localhost:8000` for the prototype — document whichever you choose.

---

### Task 2 — Security Analysis _(~1.5 hrs)_

#### 2a. Run the required scans

You must run **all four** of the following scan categories. Select an appropriate open-source or free-tier tool for each — your tool choices are part of the evaluation.

| Scan type                                      | What it covers                                                                         |
| ---------------------------------------------- | -------------------------------------------------------------------------------------- |
| **Static Application Security Testing (SAST)** | Source code — identify insecure coding patterns, injection risks, hardcoded secrets    |
| **Dependency / SCA vulnerability scan**        | Third-party packages — known CVEs in pinned dependencies                               |
| **Container image scan**                       | The Docker image you build — OS packages, installed libraries, misconfigurations       |
| **Infrastructure-as-Code (IaC) security scan** | Your Helm chart or Terraform — misconfigurations, insecure defaults, policy violations. Complete Task 4 first, then run this scan. |

Save the raw JSON output of each tool to the `reports/` directory, named clearly by scan type:

```
reports/
├── sast.<tool>.json
├── sca.<tool>.json
├── container.<tool>.json
└── iac.<tool>.json
```

#### 2b. Prioritised findings

Write a `docs/findings.md` with a table of security findings, sourced from your scans and your own manual review. For each finding:

- Tool and scan type that detected it (or "manual")
- Severity (your assessment — justify it)
- Business impact in the context of _this specific application_
- Whether it is in the starter code or in your new feature

**Do not copy-paste tool output.** We are evaluating your ability to interpret findings and apply business context to prioritisation — not your ability to run a command.

---

### Task 3 — Remediate _(~1 hr)_

- Fix **at least 3 critical or high severity findings** in code. Show the changes clearly (they will be visible in your git diff / PR).
- At least one fix must be in the code you wrote in Task 1.
- For findings you do not fix, document why in `docs/remediation-plan.md`: what is the residual risk, what effort would remediation require, and what compensating controls (if any) exist?

---

### Task 4 — Containerisation and Deployment Artifacts _(~30–45 min)_

#### Dockerfile (mandatory)

Write a production-grade `Dockerfile` for the **Python FastAPI service** (`app/`). It must:

- Use a minimal, pinned base image
- Run as a non-root user
- Include a `HEALTHCHECK`
- Not embed secrets or credentials

The container image must build successfully and the app must be reachable via `docker run`. Include build and run instructions in your README.

#### Infrastructure

Add either a `terraform/` or `helm/` directory (your choice) that could deploy this service to a Kubernetes cluster or cloud environment. Your deployment must:

- Source secrets from a secrets manager (not hardcoded in manifests or env vars)
- Restrict network ingress to only what is required
- Define resource limits and security contexts

---

### Task 5 — Executive Summary _(~30 min)_

Write `docs/executive-summary.md` as if you are presenting to a CISO who has 5 minutes.

Cover:

1. The overall security posture of the application before and after your work
2. The top 3 residual risks and the reason they were not fully remediated
3. Your recommended next steps if this were a real production service

No jargon. No tool names in the first paragraph. Your audience cares about business risk, not CVE numbers.

---

## Submission

Push your completed solution to your own GitHub repository and share the URL with us. Your repository must contain:

```
/
├── app/                        # extended Python API code
├── notify/                     # Node.js notification service (no changes required)
├── Dockerfile                  # mandatory (may cover one or both services)
├── reports/
│   ├── sast.<tool>.json
│   ├── sca.<tool>.json
│   ├── container.<tool>.json
│   └── iac.<tool>.json
├── terraform/  OR  helm/
├── docs/
│   ├── findings.md
│   ├── remediation-plan.md
│   └── executive-summary.md
├── tests/                      # updated if you added Python tests
└── README.md                   # update with Docker build/run instructions
```

CI must pass (green) on your repo before submission.

---

## What We Are Looking For

We are not grading on volume. We are grading on judgment.

- **Security depth**: Did you find the real issues? Did you prioritise them correctly for this application?
- **Implementation security**: Does your new feature introduce, or avoid, new vulnerabilities?
- **Remediation quality**: Are your fixes correct and complete? Are your deferral reasons honest?
- **Deployment security**: Does your container and infrastructure configuration reflect real-world security practices?
- **Communication**: Would a non-technical executive understand your summary?

Good luck. If anything in the brief is ambiguous, document your assumption and proceed.


---

# Submission notes

Everything below describes my changes to the starter project.

| Deliverable | Location |
|---|---|
| Shared Report Link feature (Task 1) | `app/share.py`, `app/models.py` (`ShareLink`), tests in `tests/test_share.py` |
| Scan reports (Task 2a) | `reports/` (after) and `reports/baseline/` (original starter code, for comparison) |
| Findings (Task 2b) | `docs/findings.md` |
| Fixes and regression tests (Task 3) | Git history; tests in `tests/test_security.py` |
| Remediation plan (Task 3) | `docs/remediation-plan.md` |
| Dockerfile and Helm chart (Task 4) | `Dockerfile`, `helm/vulntracker/` |
| Executive summary (Task 5) | `docs/executive-summary.md` |
| CI security gates | `.github/workflows/ci.yml` (SAST, SCA, container and IaC jobs) |

## Running locally (changed)

The API no longer contains any secrets, so it needs a JWT signing key at startup (at least 32 characters). It refuses to start without one.

```bash
# Linux / macOS
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
cd app && uvicorn main:app --reload
```
```powershell
# Windows PowerShell
$env:JWT_SECRET_KEY = python -c "import secrets; print(secrets.token_urlsafe(48))"
cd app; uvicorn main:app --reload
```

Tests need the dev requirements (adds `pytest`):

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

### Configuration

| Variable | Default | Purpose |
|---|---|---|
| `JWT_SECRET_KEY` | none (required) | JWT signing key. Read from `$SECRETS_DIR/jwt_secret_key` if that file exists, otherwise from the env var |
| `SECRETS_DIR` | `/run/secrets/vulntracker` | Where Kubernetes mounts secrets |
| `SHARE_BASE_URL` | `http://localhost:8000` | Base of generated share links |
| `ALLOWED_ORIGINS` | empty | Comma-separated browser origins allowed by CORS |
| `DATABASE_URL` | `sqlite:///./vulntracker.db` | Database location (`/data` inside the container) |
| `NOTIFY_SERVICE_URL` | `http://localhost:3001` | Notification service |

## Shared Report Link

```bash
# Create a link (password optional, 8-72 characters)
curl -X POST http://localhost:8000/scans/1/share \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"password": "correct-horse"}'

# Open it (public). Password via header (preferred) or ?password= (required by the brief)
curl http://localhost:8000/share/<token> -H "X-Share-Password: correct-horse"
```

**`share_url` choice:** links are built from `SHARE_BASE_URL` (default `http://localhost:8000`), not from the request's Host header, which an attacker could control (host-header injection).

## Docker

```bash
docker build -t vulntracker-api:local .
docker run -d --name vt -p 8000:8000 -e JWT_SECRET_KEY=<random-32+-char-value> vulntracker-api:local
docker ps          # STATUS shows "(healthy)" after ~30s
docker exec vt id  # uid=10001(app) - not root
```

The image uses a digest-pinned `python:3.11-slim` base, a multi-stage build, runs as a non-root user, has a `HEALTHCHECK`, and contains no secrets or packaging tools. For a production-like run, mount the secret as a file instead of an env var:
`-v /path/to/jwt_secret_key:/run/secrets/vulntracker/jwt_secret_key:ro`

## Kubernetes (Helm)

Prerequisites: the External Secrets Operator with a `ClusterSecretStore` named `aws-secrets-manager`, the secret `vulntracker/prod/jwt-secret-key` in AWS Secrets Manager, and the ingress-nginx controller.

```bash
helm lint helm/vulntracker
helm install vt helm/vulntracker -n vulntracker --create-namespace \
  --set image.digest=sha256:<pushed-image-digest>
```

The chart pulls the secret from AWS Secrets Manager and mounts it read-only as a file; a NetworkPolicy allows ingress only from the ingress controller and egress only to DNS and the notify service; the pod runs non-root with a read-only filesystem, all capabilities dropped, seccomp, resource limits and no service-account token.

## Assumptions

- The notify service is internal-only and was not changed apart from upgrading vulnerable dependencies (see `docs/remediation-plan.md`).
- SQLite is kept for the prototype, so the chart runs one replica.
- The image digest in `values.yaml` is a placeholder; a real pipeline would push the image and deploy by its digest.