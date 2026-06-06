# Security Policy

Asterion AI is local-first. Prompts, files, memories, research artifacts, and agent logs must stay on the user's machine unless the user explicitly approves a hybrid or external action.

## Supported Versions

Security fixes target the current `main` branch until the first public release tag is cut.

## Reporting

Do not open public issues with exploit details, secrets, private logs, or user data. Send a private report to the repository owner and include:

- affected commit or release;
- reproducible steps;
- expected and actual behavior;
- whether external network, shell, plugin, or broad file permissions are involved.

## Security Baseline

- Production secrets must never be committed to `.env`, docs, fixtures, logs, or test snapshots.
- SQLCipher key material must come from OS keychain through `keyring`.
- External API calls, public web access, network plugins, shell access, and broad file writes require explicit consent.
- Structured logs must include `ts`, `action`, `tool`, `privacy_level`, and `error`.
- Sandbox code execution must reject shell and network operations unless the run permissions allow them.

## Docker Note

`docker-compose.yml` is a local development profile. It sets `ASTERION_ALLOW_PLAINTEXT_SQLITE_FOR_DEV=1` because OS keychain access is not reliable in generic containers. Desktop builds keep SQLCipher + keychain as the default path.
