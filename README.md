# github-token-broker

Cloud Run service that exchanges a GitHub Actions OIDC JWT for a 1-hour GitHub App installation token
scoped to exactly the calling repository (`POST /token`). The App private key never leaves Secret Manager.

Env: `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY` (from Secret Manager), `ALLOWED_GITHUB_OWNER`,
optional `BROKER_AUDIENCE` (defaults to the request's public URL), and standard `OTEL_*` variables.

## Using it from a workflow

This repository is also a composite action. The job needs `permissions: id-token: write`.

```yaml
- id: broker
  uses: plengauer/github-token-broker@main # pin to a commit SHA in practice
  with:
    url: ${{ vars.TOKEN_BROKER_URL }}
- uses: some/action@v1
  with:
    token: ${{ steps.broker.outputs.token }}
```
