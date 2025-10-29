# Containerisation

Build and run the API together with PostgreSQL and Mosquitto:

```powershell
docker compose -f docker/docker-compose.yml up --build
```

The FastAPI service listens on `http://localhost:8000`, with metrics exposed at `/api/v1/observability/metrics`.
