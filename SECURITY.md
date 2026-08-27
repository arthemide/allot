# Security Policy

## Supported versions

Only the tip of `main` is maintained. There is no released version yet.

## Reporting a vulnerability

If you discover a security vulnerability in this project, please report it responsibly:

1. **Do NOT open a public issue.**
2. Use [GitHub's private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability) on this repository.
3. Include a description, steps to reproduce, and the potential impact.

We will acknowledge receipt within 48 hours and keep you informed of the progress toward a fix. Please give us a reasonable amount of time to address the issue before any public disclosure.

## Best practices for contributors

- **Never commit secrets** (`.env` files, API keys, tokens, private keys). Keep them out of version control via `.gitignore`.
- **Rotate credentials** immediately if they are accidentally exposed.
- **Keep dependencies up to date** and review security advisories for the packages you use.
- **Validate and sanitize** all external input.
