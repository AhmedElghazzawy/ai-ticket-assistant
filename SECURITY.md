# Security policy

This is a student project and not an official BŞEÜ service. It still handles messages that can contain
personal data, so security reports are welcome and taken seriously.

## Reporting a vulnerability
Please use GitHub's private vulnerability reporting (the repository's **Security** tab, then **Report a
vulnerability**). Do not open a public issue for a security problem. You can expect a first answer
within a week.

## Scope
In scope: the code in this repository and the demo at https://bseu-helpdesk.onrender.com (prompt
injection that changes a decision or leaks instructions, access to another student's ticket or another
office's queue, authentication or CSRF bypass, personal data in logs or responses, secret exposure).

Out of scope: denial of service against the free hosting tier, social engineering, and findings in
third-party services (Render, Neon, Google).

## How the system defends itself
See section 5 of [ARCHITECTURE.md](ARCHITECTURE.md) and the decision records 0007, 0009 and 0010 in
[docs/decisions/](docs/decisions/).
