# OpenBao KV Paths Reference

A concise reference document listing all OpenBao KV paths, which services use them, and sample read commands.

## iacgenie/kv (IaCGenie Backend)
| Path | Keys | Used By | Read Command |
|---|---|---|---|
| `iacgenie/kv/data/postgres` | username, host, port, password | Backend | `bao kv get iacgenie/kv/postgres` |
| `iacgenie/kv/data/redis` | host, port, password | Backend | `bao kv get iacgenie/kv/redis` |
| `iacgenie/kv/data/minio` | access_key, secret_key, endpoint | Backend | `bao kv get iacgenie/kv/minio` |
| `iacgenie/kv/data/keycloak` | admin_user, admin_password, db_password, db_host, db_port, db_name | Backend | `bao kv get iacgenie/kv/keycloak` |
| `iacgenie/kv/data/gitea` | db_password, smtp_* | Backend | `bao kv get iacgenie/kv/gitea` |
| `iacgenie/kv/data/openbao` | root_token, addr, data_dir, storage_type | Admin | `bao kv get iacgenie/kv/openbao` |
| `iacgenie/kv/data/searxng` | secret, port | Backend | `bao kv get iacgenie/kv/searxng` |
| `iacgenie/kv/data/lightserp` | api_secret, api_url | Backend | `bao kv get iacgenie/kv/lightserp` |
| `iacgenie/kv/data/pagezen` | api_url, api_secret, port | Backend | `bao kv get iacgenie/kv/pagezen` |
| `iacgenie/kv/data/nsqd` | data_path, tcp_port, http_port | Backend | `bao kv get iacgenie/kv/nsqd` |
| `iacgenie/kv/data/smtp` | api_key, server, port, from_address | Backend | `bao kv get iacgenie/kv/smtp` |
| `iacgenie/kv/data/llm` | gemini_api_key, anthropic_api_key, openai_api_key | Backend | `bao kv get iacgenie/kv/llm` |
| `iacgenie/kv/data/jwt` | secret, issuer, audience | Backend | `bao kv get iacgenie/kv/jwt` |
| `iacgenie/kv/data/cloudflare` | tunnel_token, account_id | Infra | `bao kv get iacgenie/kv/cloudflare` |

## lightserp/kv (LightSerp Service)
| Path | Keys | Used By | Read Command |
|---|---|---|---|
| `lightserp/kv/data/postgres` | username, host, port, password | LightSerp API | `bao kv get lightserp/kv/postgres` |
| `lightserp/kv/data/redis` | host, port, password | LightSerp API | `bao kv get lightserp/kv/redis` |
| `lightserp/kv/data/minio` | access_key, secret_key, endpoint | LightSerp API | `bao kv get lightserp/kv/minio` |
| `lightserp/kv/data/searxng` | secret, port | LightSerp API | `bao kv get lightserp/kv/searxng` |
| `lightserp/kv/data/api` | api_secret, api_url | LightSerp API | `bao kv get lightserp/kv/api` |
| `lightserp/kv/data/keycloak` | admin_password, db_password, url, realm, client_id, client_secret | LightSerp API | `bao kv get lightserp/kv/keycloak` |
| `lightserp/kv/data/smtp` | api_key, server, port, from_address | LightSerp API | `bao kv get lightserp/kv/smtp` |
| `lightserp/kv/data/jwt` | secret | LightSerp API | `bao kv get lightserp/kv/jwt` |
