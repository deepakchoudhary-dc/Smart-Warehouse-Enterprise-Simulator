# Enterprise Upgrade Plan

## Phase 0 – Foundations (Current)
- [x] Scaffold enterprise-ready folder structure.
- [x] Establish project planning artifacts (architecture, roadmap, requirements).
- [x] Pin core dependencies in `pyproject.toml`.

## Phase 1 – Configuration & Domain Model
- [x] Implement typed configuration system (Pydantic BaseSettings) with YAML/.env support.
- [x] Define domain models for robots, packages, zones, reservations.
- [x] Introduce validation and serialization utilities.

## Phase 2 – Core Simulation Engine
- [x] Refactor simulation loop into service classes decoupled from UI.
- [x] Implement robust multi-agent task scheduler and path planner (prioritized planning + deadlock detection).
- [x] Add fault tolerance (robot health monitoring, task requeue, reservation TTLs).

## Phase 3 – Services & APIs
- [x] Build messaging abstraction (MQTT/AMQP) with secure configuration.
- [x] Create reservation service & central orchestrator API (FastAPI).
- [x] Expose REST/gRPC endpoints for control, telemetry, and configuration.

## Phase 4 – Observability & Persistence
- [x] Integrate structured logging, metrics, and tracing (OpenTelemetry/Prometheus).
- [x] Persist simulation state and events (PostgreSQL via SQLAlchemy/async).
- [ ] Add audit trails and replay capability.

## Phase 5 – UI & Developer Experience
- [x] Develop web dashboard (React/Vue) consuming backend APIs.
- [ ] Refactor Tkinter UI to consume same services (optional developer tool).
- [x] Expand documentation, onboarding guides, architecture diagrams.

## Phase 6 – Deployment & Quality Gates
- [x] Containerize services (Docker) and provide docker-compose/Helm.
- [x] Add CI/CD workflows (lint, type-check, tests, security scan, build).
- [x] Supply Infrastructure-as-Code templates (Terraform/Bicep) and secrets management guidance.

> Track progress in `.todo/list.json` and keep plan synchronized.

