# Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│                          Smart Warehouse                              │
│ ┌──────────────┐   ┌───────────────────────────┐   ┌────────────────┐ │
│ │  UI Layer    │   │     Service Layer         │   │ Observability  │ │
│ │• React SPA   │←→ │• SimulationService        │←→ │• Structlog      │ │
│ │• Tkinter Dev │   │• TaskScheduler            │   │• Prometheus     │ │
│ └──────────────┘   │• ReservationManager       │   │• OTLP Tracing   │ │
│                    │• RobotHealthMonitor       │   └────────────────┘ │
│                    └─────────────▲────────────┘                        │
│                                  │                                     │
│                             Domain Models                              │
│                     (Pydantic + SQLAlchemy ORM)                         │
│                                  │                                     │
│ ┌────────────────────────────────┴──────────────────────────────────┐  │
│ │                          Interfaces                              │  │
│ │  REST (FastAPI)   gRPC (grpc.aio)    Messaging (MQTT/AMQP)        │  │
│ └────────────────────────────────┬──────────────────────────────────┘  │
│                                  │                                     │
│                     Persistence (PostgreSQL / In-memory)              │
└──────────────────────────────────────────────────────────────────────┘
```

- **FastAPI** exposes simulation state, configuration, robot health, and observability endpoints under `/api/v1`.
- **gRPC** mirrors core operations for low-latency consumers via `smartwarehouse.Simulation` service.
- **Persistence** relies on async SQLAlchemy to persist packages, reservations, and events, falling back to an in-memory repository when a database is unavailable.
- **Messaging** abstraction handles secure MQTT connections and includes optional AMQP support for enterprise brokers.
- **Observability** combines Structlog for structured logs, Prometheus metrics, and optional OTLP tracing for distributed insights.
