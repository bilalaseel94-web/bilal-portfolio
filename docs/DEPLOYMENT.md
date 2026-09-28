# Deployment and recovery

Production URL: https://bilalaseel.pages.dev/

Existing Cloudflare Pages project: `bilalaseel`. Keep this project and URL.

## Workflow

`.github/workflows/site.yml` checks pull requests and pushes to `main`. It generates translations, rejects stale generated pages, validates HTML/references/public files and checks JavaScript syntax. Third-party actions are pinned to commit IDs.

Publication runs only after checks pass, only for `main`, never for a pull request, and only when repository variable `CLOUDFLARE_DEPLOY_ENABLED` is `true`.

To enable publication, an authorised owner configures these GitHub Actions repository secrets:

- `CLOUDFLARE_API_TOKEN`: a Cloudflare API token limited to Cloudflare Pages Edit on the account that owns this project.
- `CLOUDFLARE_ACCOUNT_ID`: the account containing the existing project.

Store values in GitHub Secrets, never source code or logs. Repository variable `CLOUDFLARE_DEPLOY_ENABLED=true` enables the deployment job. This Pages permission may cover other Pages projects in the selected account; it is not a project-specific permission.

The `production` environment identifies live deployments. This file does not imply that protected-environment approval is configured. Owners should review changes before merging to `main`.

The pinned Wrangler CLI uploads `site-build` to the existing project. `public-files.json` and `scripts/check_site.py` prevent unlisted assets from being added to the deployment output.

## When something goes wrong

- A failed check prevents the deployment job from running. Inspect the failed step under the repository's Actions tab.
- A failed upload leaves the previous successful production deployment available; inspect Cloudflare's deployment status before assuming a new version is live.
- To suspend automatic publishing, set `CLOUDFLARE_DEPLOY_ENABLED=false`.
- To undo an ordinary code change, revert its commit through the normal review process; a successful `main` workflow then publishes the reverted version.
- For an urgent incident, an authorised owner can select a previous successful production deployment in Cloudflare and use its rollback control. Reconcile the repository before the next publish.

Read the [Cloudflare CI deployment guide](https://developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/) for the underlying integration.
