# Security boundary

ShopfloorIQ is an unauthenticated local prototype containing synthetic data. Keep it on loopback. Do not expose its port through a tunnel or use it for real production, personal or regulated records.

The API checks selected roles, incident revisions, origin and a per-server write token. It restricts static files and import sizes. These controls reduce mistakes in the demo; the identity selector is not authentication and the token is not a user credential. Filesystem access can alter SQLite, including audit records. A legacy administrative reset exists for disposable scenarios.

No external service or secret is needed. Do not put API keys or real event payloads into example files, issues, screenshots or logs. The local publication scanner is a useful guardrail, not a comprehensive secret-detection service.

There is no production support or security-response SLA. For a reproducible defect, use a minimal synthetic example, describe the local action and include sanitized expected/actual behavior. If a credential was exposed, revoke it at its issuer; deleting a file or adding it to `.gitignore` does not remove Git history.
