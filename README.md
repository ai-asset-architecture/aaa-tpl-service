# aaa-tpl-service

## Purpose / Scope
Template repo for backend/services that follow AAA governance and CI patterns.

## Ownership / CODEOWNERS
Owned by backend maintainers. See `CODEOWNERS` (to be added).

## Versioning / Release
Templates are versioned by git tags. Consumers should use a specific tag when generating new repos.

## How to Consume / Use
Use this repo as a template for new services, then wire CI to `aaa-actions`.

## Contribution / Promotion Rules
Template changes must preserve required docs links and CI wiring guidance.

## Repo Scope
Service implementation only. Contracts, schemas, and prompts live in their designated AAA repos.

## Ops Capability (v0.1 scaffold)
This template includes a backend-first scaffold for the following API contracts:
- `GET /api/ops/capabilities`
- `GET /api/ops/registry/versions`
- `GET /api/ops/registry/workflows`
- `GET /api/ops/version/{version}`

### Canonical Data Sources
- `aaa-tpl-docs/ops/index/version_index.md`
- `aaa-tpl-docs/ops/index/workflow_index.md`

### Capability Gate
- Capability name: `operate_maintain_workflow_v2`
- Env flag: `AAA_ENABLE_OPERATE_MAINTAIN_WORKFLOW_V2`
- If not enabled, ops registry/version APIs must reject requests.

## Docs Link to <org>-docs
Project documentation lives in `<org>-docs`. Link to it from this repo's README and contributing docs.

## CI wiring to aaa-actions
Use reusable workflows from `aaa-actions` with tag pins for lint/test/eval gates.
