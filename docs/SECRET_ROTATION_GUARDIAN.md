# Secret Rotation Guardian

The weekly `Secret Rotation Guardian` checks the age of GitHub Actions secret metadata. It never reads or prints secret values.

## Required Setup

Create a fine-grained personal access token or GitHub App installation token with access limited to `reprewindai-dev/veklom-byos-backend` and repository permission `Secrets: read`. Store its value as the repository Actions secret `SECRET_ROTATION_GH_TOKEN`.

The workflow deliberately does not fall back to `github.token`: that token cannot read Actions secret metadata, which would make the audit fail with `Resource not accessible by integration`.

## Scope

By default, the guardian audits repository Actions secrets only. To audit organization secrets assigned to this repository as well:

1. Grant the audit token organization permission `Secrets: read`.
2. Set repository variable `SECRET_ROTATION_INCLUDE_ORGANIZATION_SECRETS` to `true`, or select the option when manually dispatching the workflow.

If organization auditing is enabled without that additional permission, the workflow fails instead of silently claiming complete coverage.

## Verification

After the secret is configured, run **Actions -> Secret Rotation Guardian -> Run workflow**. A passing report contains secret names and timestamps only, and follows the 75-day warning / 90-day failure policy.
