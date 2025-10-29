# Project Report: Smart Warehouse Enterprise Simulator

## Executive summary

This project is a Multi-Agent Smart Warehouse Simulator: a software platform to simulate automated guided vehicles (AGVs) operating in a warehouse grid, handling package pickup and delivery, and coordinating via reservation messages. It combines a Python simulation engine and local GUI with a modern React dashboard and analytics backend. The simulator is intended as a PoC and development sandbox for path planning, collision avoidance, telemetry and analytics.

No code was changed to create this report.

## What we built
- Real-time simulation of multiple robots and package flows
- MQTT-based reservation messaging to emulate distributed coordination between agents
- Pathfinding algorithms (A* with time-indexed reservations, BFS) and reservation table builder
- FastAPI backend exposing REST and WebSocket endpoints, plus analytics aggregation
- React + Vite dashboard for live visualization, history playback and analytics
- Tkinter-based local GUI for quick development visualization

## High-level architecture

- Simulation Layer (Python): `WarehouseSimulator`, `RobotAgent`, `SimulationService`, reservation manager.
- Messaging (MQTT): `MQTTManager` using paho-mqtt to publish/subscribe reservation messages.
- Backend API (FastAPI): REST endpoints, WebSocket run streams, analytics router, OpenTelemetry instrumentation.
- Frontend (React + Vite): live operations page and analytics page with heatmaps and charts.
- Local GUI: `main.py` running a Tkinter canvas for interactive debugging.
- Persistence: SQLAlchemy-based repository scaffolding exists for durable storage (not always used by analytics in-memory aggregation).

## Technology stack

- Languages: Python 3.x, TypeScript/JavaScript (React)
- Python frameworks & libs: FastAPI, pydantic, paho-mqtt, OpenTelemetry, SQLAlchemy (async), uvicorn, pytest, tkinter
- Frontend: React, react-router-dom, axios, Vite, TypeScript
- Dev tools: Git, npm, virtualenv (.venv), GitHub

## IoT components and messaging

- MQTT is used to emulate distributed reservation messaging between AGVs. Agents publish JSON messages with `agent_id`, `x`, `y` to a configured topic and subscribe to receive reservations from others.
- TLS, client certificate, and username/password authentication are supported via settings, enabling secure broker configurations for production testing.
- Robot telemetry objects are available to forward state and position to monitoring systems or brokers.

## Data & control flows

1. Scenario start: ScenarioEngine configures layout and fleet; run is started via API or UI.
2. Assignment: SimulationService inspects idle robots and packages and assigns jobs.
3. Path planning: A* (with time-indexed reservations) computes paths; reservation tables built to avoid conflicts.
4. Movement: RobotAgent checks reservations, publishes its intended cell via MQTT, and moves if free.
5. Observability: Backend records run ticks and exposes REST and WebSocket streams for the UI; analytics aggregate run metrics and heatmaps.

## How to run locally (summary)

Prerequisites: Python 3.8+, Node 18+, npm. Optional: MQTT broker (Mosquitto) for full messaging.

Backend (PowerShell):
```powershell
cd E:\sensors\smart_warehouse
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt  # if present
.\.venv\Scripts\python.exe -m uvicorn smart_warehouse.server.app:app --reload --host 127.0.0.1 --port 8000
```

Frontend (PowerShell):
```powershell
cd E:\sensors\smart_warehouse\smart_warehouse\ui\dashboard
npm install
npm run dev
# Open http://localhost:5173
```

Local GUI (PowerShell):
```powershell
cd E:\sensors\smart_warehouse
.\.venv\Scripts\Activate.ps1
python main.py --num-robots=4
```

## Testing & validation

- Unit tests: add tests for pathfinding, reservation logic, and RobotAgent behavior (assignments, state transitions).
- Integration tests: run a full scenario with multiple robots and verify no collisions and correct deliveries.
- E2E/UI tests: Playwright or Cypress to verify live WebSocket tick updates and analytics rendering.

## Deployment & scaling notes

- For production, persist runs/ticks in a durable store (Postgres, TimescaleDB) and adapt analytics to query persisted data.
- Scale the FastAPI app with multiple uvicorn workers behind a load balancer and use a managed MQTT broker for reliability.
- Containerize services and provide a docker-compose for local orchestration (backend, MQTT broker, Postgres, frontend static server).

## Security considerations

- Do not commit secrets; use `.gitignore` and store secrets in CI/certificate stores.
- Use TLS for MQTT and authentication for the FastAPI endpoints.

## Limitations & assumptions

- Simulation is not real-time control; it's a development/test sandbox.
- Agents are simulated; production integration requires hardware adapters.
- Analytics currently aggregates in-memory runs; wiring to persistent storage is recommended for historical analytics.

## Recommended next steps

1. Wire analytics to persistent DB and persist ticks/heatmap snapshots.
2. Add unit and integration tests (pytest) and UI E2E tests (Playwright).
3. Provide Docker Compose for reproducible local environments.
4. Add GitHub Actions CI to run tests and build frontend.

---

If you want this file committed and pushed to your GitHub repository, run the following PowerShell commands from the project root (I cannot push from here):

```powershell
cd E:\sensors\smart_warehouse
git add "Project Report.md"
git commit -m "Add Project Report"
git push origin main
```

If `git push` fails because the remote has no history or the local branch doesn't exist yet, run:

```powershell
git branch -M main
git push -u origin main
```

If you hit any errors, paste the exact error output here and I will guide you through fixing them.
