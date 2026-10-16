# Remediation Plan

## Fixed in this submission

| Finding | Fix | Where |
|---|---|---|
| F-01 Hardcoded secrets | Secrets read from a mounted file (Kubernetes / AWS Secrets Manager) or env var; app refuses to start without them | `app/config.py`, `helm/` |
| F-02 SQL injection | Bound parameters; results limited to the caller's scans | `app/database.py` |
| F-03 IDOR | Ownership check on every single-scan route | `app/main.py` |
| F-07 Vulnerable dependencies | Upgraded Python and Node.js packages; `python-jose` replaced with `PyJWT` | `requirements.txt`, `notify/package*.json` |
| F-08 Passwords in logs | Only the username is logged | `app/main.py` |
| F-09 JWT `none` algorithm | Only `HS256` accepted; `exp` and `sub` required | `app/auth.py` |
| F-10 Stack traces (API) | Generic error to client, details to server log | `app/main.py` |
| F-11 CORS | Allowlist via `ALLOWED_ORIGINS` | `app/main.py` |
| F-13 Share secrets in logs (new feature) | Token and query string redacted from access logs; password accepted in a header | `app/main.py`, `app/share.py` |
| F-14 Share password brute force (new feature) | Lock after 5 wrong passwords | `app/share.py` |
| F-17 Packaging tools in image | Removed pip, setuptools and wheel from the runtime image | `Dockerfile` |

Each fix has a regression test in `tests/test_security.py` or `tests/test_share.py`, and CI blocks merges that reintroduce High/Critical dependency or code issues.

## Not fixed: residual risk, effort and compensating controls

### F-04, F-05, F-06, F-15: Notification service security (webhook auth, SSRF, hardcoded key)

**Why not fixed:** the brief states the notify service needs no changes, and fixing it properly is a design change (an auth model for webhook owners), not a one-line patch. I upgraded its vulnerable libraries (F-07) because that was low-risk and covered by its tests.

**Residual risk: High.** Anyone who can reach the notify service can register a webhook, receive every scan event and the internal service key, and make the service send requests to internal addresses.

**Effort: about 2–3 days.**
1. Authenticate the API → notify call with an HMAC signature or mutual TLS (½ day).
2. Require authentication on `/webhooks` and tie each webhook to its owner, so users only receive their own events (1 day).
3. Validate webhook URLs: HTTPS only; resolve DNS and block private, loopback and link-local ranges (incl. `169.254.169.254`); no redirects (½ day).
4. Move `SERVICE_KEY` to the secrets manager, sign payloads instead of sending the raw key, and remove the stack trace from error responses (½ day).

**Compensating controls:**
- *In place:* the Helm chart creates no Ingress for notify, and the API's NetworkPolicy only allows it to talk to notify on port 3001.
- *Recommended before production:* a NetworkPolicy for notify allowing ingress **only from the API pods**, and egress only through an allowlisting proxy; on AWS, enforce IMDSv2 with hop limit 1 so SSRF cannot reach instance credentials.

### F-16: Old secrets in git history

**Residual risk: High until rotated.** The original JWT key, database password and API key are still visible in the first commit.

**Effort: about 1 hour.**
1. Generate a new JWT key in AWS Secrets Manager (`vulntracker/prod/jwt-secret-key`). The code can no longer use the old one, and all tokens signed with it become invalid.
2. Rotate the database password and admin API key anywhere they were used.
3. Optionally rewrite history with `git filter-repo`. Rotation is what matters, because clones and forks keep the old history.

**Compensating controls:** the code now reads secrets only from the secrets manager or environment; the leaked values are not used by any part of the current code.

### F-12: No login rate limiting or password policy

**Residual risk: Medium.** Password guessing and credential stuffing against `/auth/login`; weak passwords are accepted at registration.

**Effort: about ½ day.** Per-IP and per-username rate limits (e.g. `slowapi`, or the ingress controller's `limit-rps` annotation), temporary lockout after repeated failures, and a minimum password length with a breached-password check. Existing tests that use short passwords would need updating.

**Compensating controls:** bcrypt makes each guess slow; failed logins are logged (without passwords) so they can be alerted on.

### F-10 (notify part): Stack traces from the notify service

Covered by the notify work above. **Residual risk: Low–Medium**, since notify is not exposed externally in the chart.

### F-19: SQLite, single replica, no audit log

**Residual risk: Medium (availability and forensics).** Data lives on the pod's local disk (`emptyDir`), so it is lost when the pod is rescheduled; only one replica can run; there is no record of who viewed which report.

**Effort: about 2–3 days.** Move to a managed PostgreSQL (e.g. Amazon RDS) with encryption at rest, automated backups and least-privilege credentials from the secrets manager; add an audit log for share-link creation and access.

**Compensating controls:** the Deployment uses `replicas: 1` and the `Recreate` strategy so two writers never run at once; the data volume is size-limited.

### F-13 (residual): Share password still accepted in the URL

**Residual risk: Low.** The brief requires the `password` query parameter. We remove it from the app's own logs, but it can still appear in browser history or in logs of proxies in front of the app.

**Effort: small.** In a later version, accept the password only in the `X-Share-Password` header or a POST body, and configure the ingress not to log query strings.

### F-18: Debian base image CVEs with no fix available (accepted)

**Residual risk: Low.** 44 High findings in OS packages the app does not use; Debian has not published fixes yet.

**Effort:** ongoing. Rebuild on new base image digests automatically (Dependabot or Renovate); consider a distroless or minimal base image to remove these packages entirely.

**Compensating controls (in place):** non-root user, read-only root filesystem, all Linux capabilities dropped, no privilege escalation, seccomp `RuntimeDefault`. CI fails if any High/Critical CVE **with a fix** appears.

### F-20: Checkov CKV_K8S_21 (false positive)

Templates use `.Release.Namespace`; Checkov renders the chart without a namespace and therefore sees `default`. The chart is installed with `-n vulntracker`. The check is skipped in CI with this justification noted in the workflow.

## Further hardening recommended for production

- Pin GitHub Actions and the scanner images to exact SHAs or digests.
- Add a dedicated secret scanner (e.g. Gitleaks) to CI and as a pre-commit hook. Semgrep did not detect F-01.
- Sign images and generate an SBOM at build time; enforce signature checks at deploy.
- Build and push the image in CI to a registry, then deploy by that digest (the chart's digest is currently a placeholder).