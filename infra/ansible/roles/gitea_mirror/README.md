# gitea_mirror — GitHub → Gitea Pull Mirrors

Deploys and manages pull mirrors from GitHub to Gitea's internal Git server.

## What It Does

1. Verifies Gitea Postgres `mirror` table exists
2. Creates mirror entries for each repo in `gitea_mirror_repos`
3. Marks repos as mirrors in the `repository` table
4. Triggers initial mirror sync via Gitea API
5. Reports mirror status

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `gitea_mirror_repos` | `['iacgenie', 'iacgenie-unified-infra', 'LightSerp']` | List of repo names to mirror |
| `gitea_mirror_interval` | `3600` | Sync interval in seconds |
| `gitea_mirror_enable_prune` | `true` | Remove unreferenced objects on sync |

## Architecture

```
GitHub ──(pull mirror, hourly)──→ Gitea
                                 ↑
                            Gitea Actions CI/CD
                            runs on Gitea's copy
```

## Important

- **Push → GitHub only.** Gitea pulls automatically.
- Uses direct DB manipulation (Gitea 1.23.4 lacks `/mirror-sync` API endpoint)
- Mirror entries stored in `mirror` table, repos marked `is_mirror=true`
- Gitea's internal cron handles periodic syncs
