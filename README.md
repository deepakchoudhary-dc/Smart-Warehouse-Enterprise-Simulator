# Smart Warehouse Simulation

Enterprise-ready multi-agent warehouse simulator with FastAPI, gRPC, and observability tooling.

## Features

- **Domain services** for scheduling, reservation management, and robot health monitoring
- **REST API** (`/api/v1`) exposing simulation control, configuration, metrics, and telemetry
- **gRPC service** (`smartwarehouse.Simulation`) offering state queries and package spawning
- **Persistence layer** with async SQLAlchemy models plus in-memory fallback for local runs
- **Observability** via Structlog, Prometheus metrics, and OTLP tracing hooks
- **Web dashboard** (React/Vite) polling API endpoints for live status
- **Container & IaC** assets: Dockerfile, Compose stack, and Terraform targeting Azure Container Apps
- **CI pipeline** running linting, type-checking, and tests on GitHub Actions

## Getting Started

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
pytest
uvicorn smart_warehouse.server.app:app --reload
```

OpenAPI docs live at `http://localhost:8000/docs`.

### gRPC

```
python -m grpc_tools.protoc --python_out=. --grpc_python_out=. ...
```

For this project a lightweight generic handler is already provided. Example call using `grpcurl`:

```
grpcurl -plaintext localhost:50051 smartwarehouse.Simulation/GetState
```

### Dashboard

```powershell
cd smart_warehouse/ui/dashboard
npm install
npm run dev
```

## Deployment

- `docker/docker-compose.yml` – local stack including PostgreSQL and Mosquitto
- `infra/terraform.tf` – Azure resources (Container Apps, PostgreSQL Flexible Server, Log Analytics)
- `.github/workflows/ci.yml` – Continuous integration pipeline

Set `SW_DATABASE__URL`, `SW_MQTT__BROKER_HOST`, and telemetry variables for production deployments.

