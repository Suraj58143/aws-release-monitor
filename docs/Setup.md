# Setup and operations

## Requirements

No local tools are required to run the monitor. GitHub Actions installs Python
and the collector dependencies automatically. A GitHub account and repository
permissions to configure Actions and Pages are required for administration.

## Repository and Pages

1. Create `aws-release-monitor` on GitHub and push this project to its default
   branch.
2. In **Settings → Actions → General → Workflow permissions**, allow the
   workflow to write to the repository. The collector workflow declares
   `contents: write` explicitly.
3. In **Settings → Pages**, choose **GitHub Actions** as the build and deploy
   source. The collector workflow uploads and deploys the static artifact.
4. Enable Actions if GitHub prompts for it, then run **Actions → Collect AWS
   announcements → Run workflow** once.
5. Once deployment succeeds, the repository's Pages URL is shown in the
   `github-pages` environment and in the deploy job summary.

The expected project URL for owner `Suraj58143` is
`https://Suraj58143.github.io/aws-release-monitor/`.

### Private repositories

The current GitHub account plan does not support Pages for this private
repository. The collector continues to run and commit data; Pages deployment is
skipped while the repository is private. When ready to publish, change
visibility under **Settings → General → Danger Zone → Change repository
visibility → Public**. Review the complete repository history and remove
anything sensitive before making it public. Then select **GitHub Actions** in
**Settings → Pages** and rerun the collector workflow. Public repositories
deploy automatically. Making a repository public exposes its full Git history
and files.

If the account later gains a plan that supports private-repository Pages,
enable Pages with **GitHub Actions** and create the repository Actions variable
`PAGES_ENABLED` with value `true` to allow deployment while the repository
remains private.

## Monitor a source manually

In GitHub, open **Actions → Collect AWS announcements → Run workflow**. The
scheduled run starts daily at **00:00 UTC**. GitHub may delay scheduled
workflows during periods of high load.

## Run the dashboard for development

For local development only, serve the repository root with any static HTTP
server and open `/dashboard/`. Opening the file directly with a `file://` URL
does not allow browsers to fetch JSON.

## Data files

- `data/articles.json` is an append-only historical record, deduplicated by
  SHA-256 of normalized title plus URL.
- `data/state.json` records the most recent run, per-source status, and counts.
- `schemas/` contains the JSON Schema contracts checked by CI.

## AWS service selection

The collector keeps announcements whose title matches an AWS-owned service or
product in `collector/services.json`. Add canonical names and title aliases to
that catalog to extend coverage. It filters general roundups and known
third-party products, including Microsoft and Windows Server announcements.
The dashboard's **AWS service** filter is populated from the retained dataset.
