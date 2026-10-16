# VulnTracker: Executive Security Summary

## Bottom line

Before this work, VulnTracker was not safe to put in front of customers. Any registered user could read every other customer's list of unpatched security weaknesses, which is exactly the information an attacker would want, and anyone with access to our source code could log in as any user. Those problems are now fixed and covered by automated tests, and every code change is checked automatically before it can be merged. Three risks remain, all with clear owners and short timelines, and should be closed before a production launch.

## Before and after

| | Before | After |
|---|---|---|
| Can one customer see another customer's data? | Yes, in two different ways | No |
| Can someone with the source code log in as anyone? | Yes | No: keys are kept in a secrets vault, not in the code |
| Are passwords written to log files? | Yes | No |
| Known-vulnerable third-party software | 66 known issues, 3 critical | None in the application's components |
| Automatic security checks on every change | None | Four types of scan, and changes with serious issues are blocked |
| Deployment configuration | Did not exist | Hardened: least privilege, restricted network access, secrets from a vault |

The new **report sharing feature** was built secure by design: links expire after 24 hours, cannot be guessed, can be password protected, and lock after repeated wrong passwords.

## Top 3 remaining risks

1. **The notification component is still open.** Anyone who can reach it could subscribe to receive every customer's scan updates, or use it to probe our internal network. *Why not fixed:* it needs a design change (who owns each subscription), estimated at 2–3 days, and was outside this assignment's scope. *For now:* it is not exposed to the internet in our deployment.
2. **Old passwords and keys are still visible in the code history.** They were removed from the code, but anyone who copied the code earlier still has them. *Why not fixed:* this needs an operational step, replacing the keys, rather than a code change. *Effort:* about an hour.
3. **No limit on login attempts.** An attacker can keep guessing passwords. *Why not fixed:* time; estimated at half a day. *For now:* password checks are deliberately slow, and failed logins are recorded.

## Recommended next steps

1. **This week:** replace all keys and passwords that appeared in the code history.
2. **Before launch:** secure the notification component and add login attempt limits.
3. **Before launch:** move data to a managed, backed-up database with an audit trail of who viewed which report. Today, data could be lost if the server restarts.
4. **Before launch:** commission an independent penetration test.
5. **Ongoing:** keep the automated checks running and apply security updates to the underlying software automatically.