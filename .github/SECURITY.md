# Security Policy

We take the security of `artifact-parser` seriously. Thanks for helping keep it
and its users safe — responsible disclosure makes everyone's day better.

## Supported versions

`artifact-parser` is pre-1.0 and follows a "latest is supported" policy: fixes
land on `main` and ship in the next release. Please reproduce on the latest
released version before reporting.

| Version        | Supported          |
|----------------|--------------------|
| Latest release | :white_check_mark: |
| Older releases | :x:                |

## Reporting a vulnerability

**Please do not open a public issue, pull request, or discussion for security
problems.** Public disclosure before a fix is available puts users at risk.

Instead, report it privately through GitHub's
[private vulnerability reporting](https://github.com/datnguye/artifact-parser/security/advisories/new):

1. Go to the **Security** tab of the repository.
2. Click **Report a vulnerability**.
3. Fill in the advisory form with as much detail as you can.

This opens a private channel between you and the maintainers.

### What to include

A good report helps us fix things fast:

- A description of the vulnerability and its impact.
- The affected version(s) and, if relevant, Python version and platform.
- Step-by-step reproduction — ideally a minimal artifact or code snippet.
- Any proof-of-concept, logs, or stack traces.
- Suggested remediation, if you have one.

## What to expect

- **Acknowledgement** within 5 business days.
- An assessment and, where accepted, a remediation plan with a target timeline.
- Coordinated disclosure: we'll agree on a public-disclosure date with you,
  typically once a fix is released.
- Credit in the advisory and release notes, unless you'd prefer to stay
  anonymous.

## Scope

This project parses **untrusted JSON artifacts** into pydantic models, so we
especially care about:

- Crashes, hangs, or unbounded resource use triggered by a crafted artifact
  (denial of service).
- Any path where parsing an artifact leads to code execution or arbitrary file
  access.
- Issues in the codegen pipeline that could inject unsafe content into the
  generated models.

Out of scope: vulnerabilities in third-party dependencies themselves (please
report those upstream), and reports that require an already-compromised host.

Thank you for contributing to the security of the project.
