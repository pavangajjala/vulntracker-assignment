# Security Findings

## How the review was done

1. **Manual code review** of both services: mapped every endpoint, who can call it, and traced user input to where it ends up (SQL, logs, outbound HTTP, responses). Checked against the OWASP API Security Top 10.
2. **Automated scans** to confirm and to catch what manual review misses. Raw output is in `reports/`; scans of the original starter code are in `reports/baseline/` for before/after comparison.
3. **Exploitability check** before rating: for example, the JWT `"none"` issue was tested against the original library and found *not* exploitable today, so it is rated Medium, not Critical.

### Tools and why

| Scan | Tool | Why this tool |
|---|---|---|
| SAST | Semgrep (`p/python`, `p/javascript`, `p/secrets`) | Free, covers both Python and JavaScript, maintained security rule packs |
| SCA | Trivy (filesystem) | One tool reads both `requirements.txt` and `package-lock.json` |
| Container | Trivy (image) | Same tool also checks OS packages, Python packages and Dockerfile misconfigurations |
| IaC | Checkov (Helm) | Large library of Kubernetes policies, understands Helm directly |

### Scan results before and after

| Scan | Starter code | After this work |
|---|---|---|
| SAST | 4 findings | 0 |
| SCA | 66 CVEs (3 Critical, 25 High) | 0 |
| Container | 52 High (8 fixable Python, 44 Debian with no fix) | 44 High, all Debian with no fix available |
| IaC | n/a (no chart existed) | 92 passed, 4 failed (one false positive, see F-20) |

Semgrep found 4 of the issues below. The highest-impact ones (hardcoded signing key, IDOR, unauthenticated webhooks) were found only by manual review, because they are logic and context problems that pattern-matching tools cannot see.

## Severity scale

- **Critical**: an outsider or any registered user can read or take over other customers' data.
- **High**: serious data exposure or account compromise, but needs extra access or conditions.
- **Medium**: makes other attacks easier, or limited exposure.
- **Low**: defence-in-depth or very limited impact.

## Findings

| ID | Finding | Detected by | Severity and why | Business impact | Origin | Status |
|---|---|---|---|---|---|---|
| F-01 | JWT signing key, DB password and admin API key hardcoded in `app/config.py` | Manual (Semgrep `p/secrets` missed it) | **Critical**: verified that the key from the repo can mint a valid token for any user | Anyone with repo access can log in as any customer and read their full vulnerability list | Starter | Fixed |
| F-02 | SQL injection in `GET /scans/search` (f-string in raw SQL); search also ignored the owner | Semgrep `avoid-sqlalchemy-text` + manual | **Critical**: any registered user can run arbitrary SQL | Read every customer's findings and password hashes, or modify data | Starter | Fixed |
| F-03 | IDOR: `GET /scans/{id}` does not check the owner | Manual | **High**: any logged-in user can enumerate IDs | Cross-customer disclosure of unpatched vulnerabilities | Starter | Fixed |
| F-04 | Notify service: anyone can register a webhook and receive every scan event, plus the internal `X-Service-Key` | Manual | **High** (Critical if notify is ever internet-facing) | Ongoing leak of all customers' scan events to an attacker's server | Starter | Deferred, see remediation plan |
| F-05 | Notify service: SSRF, since webhook URLs are not validated (e.g. `169.254.169.254`) | Manual | **High**: in AWS can reach the metadata service; blind (response not returned) | Possible cloud credential theft or internal network probing | Starter | Deferred |
| F-06 | Notify service: `/notify`, `GET /webhooks`, `DELETE /webhooks/:id` unauthenticated | Manual | **Medium**: needs network access to notify | Fake events, deleted subscriptions, leak of other customers' webhook URLs | Starter | Deferred |
| F-07 | Vulnerable dependencies: `python-jose 3.3.0` (Critical), `cryptography 38.0.1`, `python-multipart 0.0.6`, `axios 0.21.1`, `express 4.18.2` chain incl. `proxy-addr` (Critical) | Trivy SCA | **High**: known exploits, including DoS on the public API and flaws in token validation | Outages; weakens login security | Starter | Fixed (66 → 0) |
| F-08 | Passwords written to logs in plain text on every login | Semgrep `logger-credential-disclosure` | **High**: anyone with log access (ops, log vendor) collects passwords | Account takeover, credential reuse on other systems | Starter | Fixed |
| F-09 | `"none"` in the allowed JWT algorithms | Semgrep `jwt-python-none-alg` | **Medium**: tested; the installed library rejects it, but any library change would make it exploitable | Latent full authentication bypass | Starter | Fixed |
| F-10 | Full stack traces returned to clients on errors (both services) | Manual | **Medium**: helps attackers map internals | Leaks file paths, SQL and library versions | Starter | Fixed in API; notify deferred |
| F-11 | CORS reflects any `Origin` with credentials allowed | Manual | **Medium**: lower because auth uses bearer headers, not cookies | Any website could drive the API from a victim's browser if a token is present | Starter | Fixed (allowlist) |
| F-12 | No rate limiting or lockout on login; no password strength rules | Manual | **Medium** | Password guessing and credential stuffing | Starter | Deferred |
| F-13 | Share-link token and password appear in URLs and so in access logs | Manual (design review) | **Medium**: the brief requires the password as a query parameter | Anyone with log access could open shared reports | **New feature** | Fixed: redacted from access logs; `X-Share-Password` header supported |
| F-14 | Share-link password could be brute-forced | Manual (design review) | **Medium**: endpoint is public | Outsider guesses the password and reads the report | **New feature** | Fixed: link locks after 5 wrong passwords |
| F-15 | Notify service key hardcoded in `notify/src/config.js` | Manual | **Medium** | Key is public to anyone with repo access | Starter | Deferred |
| F-16 | Old secrets remain in git history (first commit) | Manual | **High** until rotated | Leaked values stay usable unless rotated | Starter | Deferred: rotate (see plan) |
| F-17 | Packaging tools in the image with CVEs (`setuptools`, `wheel`, `urllib3`, `msgpack`, `jaraco.context`) | Trivy container | **Medium**: not used at runtime but present | Larger attack surface | New (Dockerfile) | Fixed: removed from image |
| F-18 | Debian base image packages with HIGH CVEs and no fix available (`util-linux`, `ncurses`, `libsystemd`, `perl-base`) | Trivy container | **Low**: not used by the app; non-root, read-only filesystem, no capabilities | Minimal | New (Dockerfile) | Accepted, rebuild when fixes ship |
| F-19 | SQLite, single replica, no backups or audit log | Manual | **Medium** (availability and forensics) | Data loss on pod restart; no record of who viewed what | Starter | Deferred |
| F-20 | Checkov `CKV_K8S_21` "default namespace" on 4 resources | Checkov | **False positive**: templates use `.Release.Namespace`; Checkov renders without one | None | New (Helm) | Skipped in CI with this justification |

## Security design of the new Shared Report Link feature

| Decision | Reason |
|---|---|
| Token is 32 random bytes from `secrets` | Cannot be guessed |
| Only the SHA-256 hash of the token is stored | A database leak does not expose working links |
| Only the owner of a scan can share it | Prevents the same IDOR as F-03 |
| Optional password stored as a bcrypt hash, 8–72 characters | Never stored in plain text; bcrypt ignores bytes after 72 |
| Locks after 5 wrong passwords | Stops brute force (F-14) |
| Invalid, expired and locked links return the same 404 | Does not reveal which links exist |
| Public view omits `owner_id` and internal `id` | Outsiders see only what they need |
| `share_url` uses a configured base URL (`SHARE_BASE_URL`, default `http://localhost:8000`), not the request's Host header | Prevents host-header injection producing links to an attacker's site |
| `Cache-Control: no-store`, `Referrer-Policy: no-referrer` | Shared reports are not cached or leaked via the Referer header |
| Deleting a scan deletes its share links | Links cannot outlive their data |