# MCP Server Plan for Module 3 Agent Choreography

## Context

The codebase already has a fully wired LangGraph-based workflow orchestration engine (Module 3 Agent Choreography) with:
- A 10+ node DAG: Coding, Validating, Planning, Applying, Testing, Git Push, CI Trigger, CI Monitor, Human Review, Fail
- Three agent types: CommandAgent (OpenTofu CLI), GitAgent, CICIAgent
- Two event broadcast services: in-memory (WebSocket-only) and Redis pub/sub (cross-service)
- Celery task queue with Redis broker
- Postgres persistence with LangGraph checkpointing
- Pipeline management with human intervention/escalation
- Observability stack: Prometheus, Elasticsearch, Grafana

**Current state: Zero MCP server configuration exists in the project.** No `.mcp.json`, no MCP dependencies, no MCP settings anywhere. This plan identifies all MCP servers needed to expose the agent choreography capabilities as first-class MCP servers.

---

## MCP Server 1: LangGraph Workflow Orchestrator

**Purpose:** Expose the LangGraph `WorkflowOrchestrator` as an MCP server so external agents can start, resume, query, and manage workflow sessions.

**Existing code source:**
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/modules/workflow_engine/orchestrator.py` (623 lines)
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/modules/workflow_engine/session_manager.py`
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/modules/workflow_engine/state_machine.py`

**MCP Resources (stateful data):**
- `workflow://{session_id}` - Current workflow state for a session
- `workflow://{session_id}/checkpoint` - Latest checkpoint data
- `workflow://{session_id}/history` - Transition history
- `workflow://sessions` - List of all sessions (paginated, filterable by status)

**MCP Prompts (templates):**
- `start_workflow` - Template for starting a new workflow session (accepts: prompt, git_repo_url, git_branch, ci_provider, ci_inputs)
- `resume_workflow` - Template for resuming a checkpointed session (accepts: session_id, thread_id)
- `human_review_response` - Template for responding to human review (accepts: session_id, action: approve/clarify/escalate, comment)

**MCP Tools (actions):**
- `orchestrator.start_session(session_id, prompt, git_repo_url, git_branch, ci_provider, ci_inputs, metadata, max_iterations)` - Start a new LangGraph workflow
- `orchestrator.resume_session(session_id, thread_id)` - Resume from last checkpoint
- `orchestrator.transition_session(session_id, from_state, to_state, reason, metadata)` - Manual state transition
- `orchestrator.complete_session(session_id, git_commit_sha, ci_run_id)` - Mark session complete
- `orchestrator.fail_session(session_id, error_message)` - Mark session failed
- `orchestrator.escalate_session(session_id, reason, escalation_type)` - Escalate to human review
- `orchestrator.get_session_status(session_id)` - Get current state
- `orchestrator.get_checkpoint(session_id, thread_id)` - Retrieve checkpoint data
- `orchestrator.list_sessions(user_id, status_filter, limit, offset)` - List sessions
- `orchestrator.get_transition_history(session_id, limit)` - Get transition history

**Dependencies:** langgraph, langgraph-checkpoint-postgres, redis, postgres-adapter

---

## MCP Server 2: Redis Event Bus

**Purpose:** Expose the Redis pub/sub infrastructure as a cross-service event communication layer, enabling external services to subscribe, publish, and monitor workflow events.

**Existing code source:**
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/src/workflow_engine/event_broadcast.py` (264 lines)
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/services/event_broadcast.py` (81 lines, in-memory variant)

**MCP Resources (stateful data):**
- `events://{channel}` - Current event stream for a channel (e.g., `workflow:{session_id}`, `workflow:global`)
- `events://subscribers/{channel}` - List of active subscribers
- `events://stats` - Aggregate event statistics (count by type, channel, time window)

**MCP Prompts (templates):**
- `subscribe_events` - Template for subscribing to a channel (accepts: channel, event_types)
- `publish_event` - Template for publishing a structured event (accepts: channel, event_type, data)

**MCP Tools (actions):**
- `events.publish(channel, event_type, data, session_id)` - Publish event to Redis pub/sub channel
- `events.subscribe(channel, callback_url)` - Subscribe to a Redis channel (returns subscription ID)
- `events.unsubscribe(subscription_id)` - Cancel subscription
- `events.list_channels(pattern)` - List active channels matching pattern
- `events.get_event_history(channel, limit, after_timestamp)` - Retrieve recent events from channel
- `events.get_event_types()` - List all known event types (PHASE_TRANSITION, AGENT_START, AGENT_COMPLETE, AGENT_ERROR, SESSION_CREATED, SESSION_UPDATED, SESSION_COMPLETE, SESSION_FAILED, HUMAN_REVIEW_REQUESTED, HEARTBEAT)
- `events.get_stats()` - Get aggregate event statistics

**Event Types:**
- `PHASE_TRANSITION` - Session moved from one state to another
- `AGENT_START` - Agent began execution at a node
- `AGENT_COMPLETE` - Agent finished execution
- `AGENT_ERROR` - Agent encountered an error
- `SESSION_CREATED` - New session initialized
- `SESSION_UPDATED` - Session metadata updated
- `SESSION_COMPLETE` - Session reached terminal completed state
- `SESSION_FAILED` - Session reached terminal failed state
- `HUMAN_REVIEW_REQUESTED` - Session escalated for human review
- `HEARTBEAT` - Periodic keepalive

**Dependencies:** redis, aioredis

---

## MCP Server 3: State Machine Engine

**Purpose:** Expose the state machine transition validation, execution, and rollback logic as a reusable service. This is the core state machine that both the LangGraph orchestrator and the legacy pipeline system rely on.

**Existing code source:**
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/src/workflow_engine/transition_handler.py` (657 lines)
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/modules/workflow_engine/state_machine.py`

**MCP Resources (stateful data):**
- `state-machine://{session_id}/status` - Current session state
- `state-machine://graph` - Complete state machine graph definition (all states and allowed transitions)

**MCP Prompts (templates):**
- `validate_transition` - Template for validating a state transition (accepts: from_state, to_state, session_id)
- `execute_transition` - Template for executing a state transition (accepts: session_id, from_state, to_state, reason, idempotency_key)

**MCP Tools (actions):**
- `state-machine.validate_transition(session_id, from_state, to_state)` - Check if a transition is allowed
- `state-machine.execute_transition(session_id, from_state, to_state, reason, idempotency_key)` - Atomically execute a state transition with rollback capability
- `state-machine.execute_rollback(session_id, from_state, to_state, reason)` - Rollback a failed transition
- `state-machine.escalate_to_review(session_id, reason)` - Transition session to HUMAN_REVIEW
- `state-machine.mark_failed(session_id, reason)` - Transition session to FAILED
- `state-machine.mark_completed(session_id, reason)` - Transition session to COMPLETED
- `state-machine.get_transition_history(session_id, limit)` - Get all transitions for a session
- `state-machine.get_transition_stats(session_id)` - Get aggregate transition statistics
- `state-machine.list_valid_transitions(from_state)` - List all allowed transitions from a state
- `state-machine.get_state_info(state_name)` - Get metadata about a specific state

**State Machine Definition:**
- States: CREATED, CODING, VALIDATING, PLANNING, APPLYING, TESTING, GIT_PUSH, CI_TRIGGER, CI_MONITOR, COMPLETED, CI_FAILED, FAILED, HUMAN_REVIEW, ESCALATE, CLARIFY, FORMAT, INIT, STATIC_ANALYSIS
- Transition types: FORWARD, BACKWARD, ESCALATION, RECOVERY, MANUAL
- Supports idempotency keys, version-based optimistic locking, atomic operations with rollback

**Dependencies:** postgres-adapter, redis-client

---

## MCP Server 4: Pipeline Management

**Purpose:** Expose the pipeline lifecycle management service, including creation, monitoring, human intervention, and cost estimation. This serves as the higher-level API over the raw state machine and workflow orchestrator.

**Existing code source:**
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/routers/pipeline.py` (817 lines)
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/pipeline/factory.py`
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/human_loop/interrupt_manager.py`
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/human_loop/approval_service.py`
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/human_loop/escalation_handler.py`

**MCP Resources (stateful data):**
- `pipeline://{session_id}` - Full pipeline detail including phase history and logs
- `pipeline://{session_id}/metrics` - Pipeline metrics (phase, agent, overall)
- `pipeline://list?user_id={user_id}` - User's pipelines (paginated)

**MCP Prompts (templates):**
- `start_pipeline` - Template for starting a new pipeline (accepts: user_request, name, workspace_id, session_id, deployment_mode, config)
- `human_intervention` - Template for performing human intervention (accepts: session_id, resolution_type, resolution_data)

**MCP Tools (actions):**
- `pipeline.create(user_request, name, workspace_id, session_id, deployment_mode, config)` - Create and start a new pipeline
- `pipeline.start(session_id, user_request)` - Start pipeline execution
- `pipeline.resume(session_id)` - Resume a paused pipeline
- `pipeline.stop(session_id)` - Stop a running pipeline
- `pipeline.interrupt(session_id, error_class, context)` - Trigger human interrupt
- `pipeline.request_approval(session_id, approval_type, context)` - Request human approval
- `pipeline.submit_approval(approval_token, approved, comments)` - Submit approval decision
- `pipeline.human_intervention(session_id, resolution_type, resolution_data)` - Apply human resolution
- `pipeline.get_status(session_id)` - Get pipeline status
- `pipeline.get_detail(session_id)` - Get full pipeline detail with phase history and logs
- `pipeline.get_metrics(session_id)` - Get pipeline/phase/agent metrics
- `pipeline.estimate_cost(session_id)` - Estimate infrastructure cost from generated plan
- `pipeline.list(user_id, status_filter, limit, offset)` - List pipelines
- `pipeline.delete(session_id)` - Soft-delete a pipeline

**Dependencies:** pipeline-factory, interrupt-manager, approval-service, escalation-handler, pipeline-repository

---

## MCP Server 5: OpenTofu Agent

**Purpose:** Expose the CommandAgent capabilities (OpenTofu CLI commands: format, init, validate, plan, apply) as an MCP server. This enables any external agent to run OpenTofu operations in isolated sandbox containers without needing direct access to the orchestration engine.

**Existing code source:**
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/agents/command_agents.py` (410 lines)
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/agents/base_agent.py` (94 lines)
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/src/sandbox_manager/` - ContainerProvisioner, CommandExecutor

**MCP Resources (stateful data):**
- `tofu://{sandbox_id}/workspace` - Current workspace state for a sandbox
- `tofu://{sandbox_id}/output` - Latest command output
- `tofu://workspace-status` - Status of all active sandboxes

**MCP Prompts (templates):**
- `run_tofu_command` - Template for running an OpenTofu command (accepts: command, workspace_files, sandbox_config)
- `create_workspace` - Template for provisioning a new sandbox workspace (accepts: session_id, provider_config, resources)

**MCP Tools (actions):**
- `tofu.provision_sandbox(session_id, cpu, memory)` - Provision a new sandbox container
- `tofu.write_file(sandbox_id, filename, content)` - Write a file to the sandbox workspace
- `tofu.execute_command(sandbox_id, command)` - Run any shell command in the sandbox
- `tofu.format(sandbox_id)` - Run `tofu fmt -recursive`
- `tofu.init(sandbox_id, upgrade=false)` - Run `tofu init`
- `tofu.validate(sandbox_id)` - Run `tofu validate`
- `tofu.plan(sandbox_id, out="tfplan")` - Run `tofu plan -out=tfplan`
- `tofu.apply(sandbox_id, auto_approve=false)` - Run `tofu apply`
- `tofu.output_plan(sandbox_id)` - Read plan output
- `tofu.git_push(sandbox_id, branch, commit_msg)` - Run git add/commit/push
- `tofu.cleanup(sandbox_id)` - Stop and remove sandbox container
- `tofu.list_sandboxes()` - List all active sandboxes

**Dependencies:** docker, sandbox-manager, OpenTofu CLI

---

## MCP Server 6: Celery Task Queue

**Purpose:** Expose the Celery Redis-brokered task queue for submitting, monitoring, and managing async background tasks. This enables external systems to trigger long-running code generation or processing tasks.

**Existing code source:**
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/celery_worker.py`
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/main.py` - `generate_code_task` background task

**MCP Resources (stateful data):**
- `celery://task/{task_id}` - Current task status and result
- `celery://worker-stats` - Worker pool status and queue depth

**MCP Prompts (templates):**
- `submit_task` - Template for submitting an async task (accepts: task_name, args, kwargs, queue, priority)

**MCP Tools (actions):**
- `celery.submit_task(task_name, args, kwargs, queue, priority, countdown, retry)` - Submit a task to the Celery queue
- `celery.get_task_status(task_id)` - Get task status (PENDING, STARTED, SUCCESS, FAILURE, RETRY)
- `celery.get_task_result(task_id)` - Get task result data
- `celery.revoke_task(task_id, terminate=false)` - Revoke a pending task
- `celery.retry_task(task_id)` - Retry a failed task
- `celery.get_queue_depth(queue)` - Get number of tasks waiting in a queue
- `celery.get_worker_stats()` - Get worker pool status
- `celery.get_task_history(task_id, limit)` - Get task execution history

**Task Types:**
- `generate_code_task` - Main async code generation task
- Custom user-defined tasks via dynamic registration

**Dependencies:** celery[redis], redis

---

## MCP Server 7: Observability and Metrics

**Purpose:** Expose the monitoring stack (Prometheus metrics, Elasticsearch logs, Grafana dashboards) as a unified observability MCP server. This enables agents to query system health, performance metrics, and error logs programmatically.

**Existing code source:**
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/observability/` - audit_logger, pipeline_monitor, tracing_service
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/routers/metrics.py`
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/routers/observability.py`
- `docker-compose.yml` - Prometheus, Grafana, Elasticsearch, Kibana, Filebeat

**MCP Resources (stateful data):**
- `metrics://pipeline/{session_id}` - Pipeline-specific metrics
- `metrics://system` - Aggregate system health metrics
- `logs://{session_id}` - Session-specific logs
- `logs://system` - Aggregate system logs

**MCP Prompts (templates):**
- `query_metrics` - Template for querying Prometheus metrics (accepts: metric_name, session_id, time_range)
- `search_logs` - Template for searching Elasticsearch logs (accepts: query, session_id, time_range, level)

**MCP Tools (actions):**
- `observability.get_pipeline_metrics(session_id)` - Get pipeline phase/agent metrics
- `observability.get_system_metrics()` - Get aggregate system health
- `observability.search_logs(query, session_id, time_range, level, limit)` - Search log store
- `observability.get_traces(trace_id)` - Get OpenTelemetry trace
- `observability.get_health_status()` - Get system health across all services
- `observability.get_transition_stats(session_id)` - Get state transition statistics
- `observability.get_cost_estimate(session_id)` - Get cost estimation from pipeline
- `observability.get_audit_log(session_id, action, time_range, limit)` - Get audit trail

**Metrics Available:**
- Pipeline metrics: phase durations, retry counts, error counts
- Agent metrics: execution times, success rates, error patterns
- System metrics: active pipelines, uptime, queue depth
- Cost metrics: estimated infrastructure costs

**Dependencies:** prometheus-client, elasticsearch, opentelemetry, docker

---

## MCP Server 8: Artifact Storage

**Purpose:** Expose the MinIO/S3-compatible object storage for generated HCL artifacts, plans, and state files. This enables agents to store, retrieve, and manage infrastructure code artifacts.

**Existing code source:**
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/src/artifact_store/` - Artifact store module
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/docker-compose.prod.yml` - MinIO service
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/infra/modules/artifact-registry/` - GCP Artifact Registry (cloud equivalent)

**MCP Resources (stateful data):**
- `artifact://session/{session_id}/{path}` - Specific artifact content
- `artifact://list/{session_id}` - List artifacts for a session

**MCP Prompts (templates):**
- `upload_artifact` - Template for storing an artifact (accepts: session_id, path, content, content_type)
- `search_artifacts` - Template for searching artifacts (accepts: session_id, pattern, metadata_filter)

**MCP Tools (actions):**
- `artifacts.upload(session_id, path, content, content_type, metadata)` - Upload an artifact
- `artifacts.download(session_id, path)` - Download artifact content
- `artifacts.list(session_id, prefix)` - List artifacts with optional prefix
- `artifacts.delete(session_id, path)` - Delete an artifact
- `artifacts.get_metadata(session_id, path)` - Get artifact metadata
- `artifacts.search(session_id, pattern)` - Search artifacts by name pattern
- `artifacts.copy(source_session, source_path, dest_session, dest_path)` - Copy between sessions
- `artifacts.presigned_url(session_id, path, expiry)` - Generate presigned download URL

**Storage Structure:**
- `sessions/{session_id}/main.tf` - Generated HCL
- `sessions/{session_id}/plan.tfplan` - Terraform plan binary
- `sessions/{session_id}/output.txt` - Command outputs
- `sessions/{session_id}/logs/` - Execution logs
- `sessions/{session_id}/artifacts/` - Additional generated files

**Dependencies:** minio, boto3-compatible SDK

---

## MCP Server 9: Git and CI/CD Integration

**Purpose:** Expose the Git repository interaction and CI/CD pipeline trigger/monitor capabilities. This enables external agents to manage repositories, create branches, push code, and monitor CI status.

**Existing code source:**
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/agents/git_agent.py`
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/agents/ci_agent.py`
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/src/git_cicd/digger_agent.py`
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/src/git_cicd/webhook_handler.py`
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/routers/git.py`

**MCP Resources (stateful data):**
- `git://{repo}/status` - Repository status and sync state
- `git://{repo}/ci/{run_id}` - CI pipeline run status

**MCP Prompts (templates):**
- `create_branch` - Template for creating a feature branch (accepts: repo_url, base_branch, feature_name)
- `push_code` - Template for pushing generated code (accepts: repo_url, branch, files, commit_msg)
- `trigger_ci` - Template for triggering a CI pipeline (accepts: repo_url, branch, provider, inputs)

**MCP Tools (actions):**
- `git.create_branch(repo_url, base_branch, branch_name)` - Create a new git branch
- `git.push_code(repo_url, branch, files, commit_msg, author)` - Push generated files to repository
- `git.get_branch_status(repo_url, branch)` - Get branch sync status
- `git.get_commit_history(repo_url, branch, limit)` - Get recent commits
- `git.create_pull_request(repo_url, source_branch, target_branch, title, body)` - Create a PR
- `git.get_pull_request(repo_url, pr_number)` - Get PR status and details
- `git.trigger_ci(repo_url, branch, provider, inputs)` - Trigger CI pipeline
- `git.monitor_ci(repo_url, ci_run_id)` - Monitor CI pipeline status
- `git.get_ci_status(repo_url, ci_run_id)` - Get CI run status
- `git.handle_webhook(payload, secret)` - Process incoming webhook events

**CI Providers Supported:**
- GitHub (via GitHub Actions API)
- GitLab (via GitLab CI API)
- Bitbucket (via Bitbucket Pipelines API)

**Dependencies:** docker (for git CLI), requests/http clients

---

## MCP Server 10: Secret Store

**Purpose:** Expose the unified secret management layer for accessing cloud credentials, API keys, and other sensitive configuration. This centralizes secret access across all agents and pipeline phases.

**Existing code source:**
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/src/secret_store/` - Secret store module
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/src/secret_store/service.py`
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/src/secret_store/secret_manager.py`
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/modules/secret_store/api.py`
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/routers/secrets.py`

**MCP Resources (stateful data):**
- `secret://{namespace}/{name}` - Secret metadata (not the value itself)

**MCP Prompts (templates):**
- `get_secret` - Template for retrieving a secret (accepts: name, namespace)
- `rotate_secret` - Template for rotating a secret (accepts: name, namespace)

**MCP Tools (actions):**
- `secrets.get(name, namespace)` - Retrieve a secret value
- `secrets.list(namespace, prefix)` - List secrets with optional filter
- `secrets.put(name, namespace, value, metadata)` - Store a new secret
- `secrets.update(name, namespace, value)` - Update an existing secret
- `secrets.delete(name, namespace)` - Delete a secret
- `secrets.rotate(name, namespace)` - Rotate a secret and return new value
- `secrets.version_history(name, namespace, limit)` - Get version history

**Secret Backends Supported:**
- AWS Secrets Manager
- HashiCorp Vault
- GCP Secret Manager
- Environment variables (fallback)

**Dependencies:** AWS SDK, hvac (HashiCorp Vault), GCP secret manager SDK

---

## MCP Server 11: Identity and Access Management

**Purpose:** Expose the Keycloak-based identity management for verifying tokens, checking permissions, and managing user roles within the agent choreography system.

**Existing code source:**
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/auth_providers/keycloak.py`
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/middleware/auth_middleware.py`
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/security/access_control.py`

**MCP Resources (stateful data):**
- `iam://user/{user_id}` - User profile and permissions
- `iam://role/{role}` - Role definition and allowed operations

**MCP Prompts (templates):**
- `verify_access` - Template for verifying access to a resource (accepts: user_id, resource, action)
- `check_role` - Template for checking role permissions (accepts: user_id, role, resource, action)

**MCP Tools (actions):**
- `iam.verify_token(token)` - Verify and decode a JWT token
- `iam.get_user(user_id)` - Get user profile and roles
- `iam.check_permission(user_id, resource, action)` - Check if user has specific permission
- `iam.list_roles()` - List all roles
- `iam.get_user_roles(user_id)` - Get roles for a user
- `iam.get_resource_permissions(resource)` - Get all permissions for a resource
- `iam.create_user(username, email, roles)` - Create a new user
- `iam.update_user(user_id, roles, attributes)` - Update user roles/attributes

**Dependencies:** keycloak-client, jwt

---

## MCP Server 12: LLM Proxy

**Purpose:** Expose the LiteLLM proxy layer for model routing, cost tracking, and multi-model inference. This enables agents to route prompts to different LLM providers with cost-aware selection.

**Existing code source:**
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/src/llm_proxy/service.py`
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/src/llm_proxy/providers/base.py`
- `/Users/manjunathkanavi/workspace/git_workspace/terragenius/iacgenie/backend/routers/llm.py`

**MCP Resources (stateful data):**
- `llm://models` - Available model list with capabilities
- `llm://cost/{session_id}` - Cost tracking per session
- `llm://usage/{user_id}` - Usage statistics per user

**MCP Prompts (templates):**
- `generate` - Template for LLM generation (accepts: prompt, model, temperature, max_tokens)
- `generate_best` - Template for cost-aware model selection (accepts: prompt, budget, quality_requirement)

**MCP Tools (actions):**
- `llm.generate(prompt, model, temperature, max_tokens, stream)` - Generate text via LiteLLM
- `llm.generate_stream(prompt, model, temperature, max_tokens)` - Stream generation output
- `llm.list_models()` - List available models with capabilities
- `llm.select_best(prompt, budget, quality)` - Automatically select best model
- `llm.get_cost(session_id)` - Get accumulated cost for a session
- `llm.get_usage(user_id, time_range)` - Get usage statistics
- `llm.get_model_stats(model_name)` - Get model performance metrics (latency, success rate)
- `llm.rebalance_budget(session_id, new_budget)` - Adjust session budget

**Model Providers:**
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google (Gemini)
- Custom/self-hosted models via OpenAI-compatible API

**Dependencies:** litellm[proxy], openai, anthropic, google-generativeai

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        External Clients                          │
│              (Other Agents, CI Systems, Admin Tools)            │
└──────────────────────────┬──────────────────────────────────────┘
                           │ MCP Protocol
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
┌─────────────────┐ ┌────────────┐ ┌──────────────┐
│  Workflow Orch. │ │ State      │ │ Pipeline     │
│  Server         │ │ Machine    │ │ Management   │
└────────┬────────┘ └─────┬──────┘ └──────┬───────┘
         │                │               │
         ▼                ▼               │
┌─────────────────┐ ┌────────────┐        │
│  Event Bus      │ │ OpenTofu   │        │
│  (Redis)        │ │ Agent      │        │
└────────┬────────┘ └─────┬──────┘        │
         │                │               │
         ▼                ▼               │
┌─────────────────┐ ┌────────────┐ ┌──────┴───────┐
│  Celery Task    │ │ Git & CI/  │ │ Observability│
│  Queue          │ │ CD         │ │ & Metrics    │
└─────────────────┘ └────────────┘ └──────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
┌───────────────┐ ┌──────────────┐ ┌──────────────┐
│ Artifact      │ │ Secret Store │ │ Identity &   │
│ Storage       │ │              │ │ Access (IAM) │
└───────────────┘ └──────────────┘ └──────────────┘
              │
              ▼
┌──────────────────────┐
│  LLM Proxy           │
│  (LiteLLM)           │
└──────────────────────┘
```

## Implementation Priority

| Priority | MCP Server | Rationale |
|----------|-----------|-----------|
| 1 | LangGraph Workflow Orchestrator | Core orchestration - existing code is complete, just needs MCP wrapping |
| 2 | State Machine Engine | Foundation for all transitions - tightly coupled to workflow orchestrator |
| 3 | Redis Event Bus | Already implemented, enables cross-service communication for all other servers |
| 4 | OpenTofu Agent | Critical for IaC generation - has working sandbox integration |
| 5 | Pipeline Management | Higher-level API that composes workflow + state machine + human review |
| 6 | Git and CI/CD Integration | Required for the git_push and ci_trigger phases of the workflow DAG |
| 7 | Celery Task Queue | Needed for async task delegation from workflow nodes |
| 8 | Observability and Metrics | Enables agents to monitor and troubleshoot workflows |
| 9 | Artifact Storage | Required for persisting generated HCL and plans |
| 10 | Secret Store | Needed for cloud provider credentials in sandbox containers |
| 11 | LLM Proxy | Powers the LLM calls within agents - can be wrapped for external routing |
| 12 | Identity and Access Management | Supports auth/MFA for MCP server access controls |

## Technical Notes

1. **MCP Protocol Version:** Use MCP JSON-RPC 2024-11-05 or latest stable
2. **Transport:** Start with HTTP+SSE, add WebSocket support for real-time event streams
3. **Authentication:** MCP servers should validate incoming tokens via the IAM server before exposing tools/resources
4. **Rate Limiting:** Event bus and observability servers should implement rate limits to prevent overload
5. **Idempotency:** All state-changing tools should accept and honor idempotency keys
6. **Error Handling:** MCP errors should map to existing ErrorClass enum values (RETRYABLE, CLARIFICATION, HUMAN_REQUIRED, FATAL)
7. **Existing Middleware:** Auth middleware (`backend/middleware/auth_middleware.py`) and error handling (`backend/middleware/error_handling.py`) should be reused across all MCP servers
8. **No changes to existing code:** All MCP servers should be new modules that wrap or call existing services, not modify them
