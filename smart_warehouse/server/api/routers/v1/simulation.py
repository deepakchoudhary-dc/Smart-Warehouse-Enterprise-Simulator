"""Simulation control and query endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from smart_warehouse.observability.metrics import record_simulation_metric
from smart_warehouse.server.api.schemas.simulation import (
    AppConfigSchema,
    EventSchema,
    PackageSchema,
    SimulationStateSchema,
)
from smart_warehouse.server.dependencies import (
    get_app_settings,
    get_repository,
    get_simulation_service,
)
from smart_warehouse.services import SimulationService

router = APIRouter(prefix="/simulation", tags=["simulation"])


def _service(service: SimulationService = Depends(get_simulation_service)) -> SimulationService:
    return service


@router.get("/state", response_model=SimulationStateSchema)
async def get_simulation_state(service: SimulationService = Depends(_service)) -> SimulationStateSchema:
    snapshot = service.snapshot(telemetry=[])
    layout = service.context.layout
    return SimulationStateSchema.from_domain(snapshot, layout)


@router.post("/packages", response_model=PackageSchema, status_code=status.HTTP_201_CREATED)
async def spawn_package(
    service: SimulationService = Depends(_service),
    repo=Depends(get_repository),
) -> PackageSchema:
    package = service.spawn_package()
    if not package:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No available pickup zones to spawn a new package.",
        )
    record_simulation_metric(spawned=True)
    await repo.record_package_spawn(package)
    await repo.record_event(
        "package_spawned",
        {"package_id": package.id, "position": package.position.to_tuple()},
        package_id=package.id,
    )
    await repo.session.commit()
    return PackageSchema.from_domain(package)


@router.post("/packages/{package_id}/complete", response_model=PackageSchema)
async def complete_package(
    package_id: str,
    service: SimulationService = Depends(_service),
    repo=Depends(get_repository),
) -> PackageSchema:
    package = service.complete_package(package_id)
    if not package:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    await repo.update_package_status(package)
    await repo.record_event(
        "package_completed",
        {"package_id": package.id},
        package_id=package.id,
    )
    await repo.session.commit()
    return PackageSchema.from_domain(package)


@router.post("/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_simulation(service: SimulationService = Depends(_service)) -> None:
    service.reset()


@router.get("/events", response_model=List[EventSchema])
async def get_recent_events(repo=Depends(get_repository)) -> List[EventSchema]:
    events = await repo.recent_events()
    return [EventSchema.from_record(event) for event in events]


@router.get("/config", response_model=AppConfigSchema)
async def get_configuration(settings=Depends(get_app_settings)) -> AppConfigSchema:
    return AppConfigSchema.from_settings(settings)
