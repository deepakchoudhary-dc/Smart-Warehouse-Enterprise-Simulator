"""Robot telemetry and control endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from smart_warehouse.server.api.schemas.simulation import RobotHealthSchema
from smart_warehouse.server.dependencies import get_simulation_service
from smart_warehouse.services import SimulationService

router = APIRouter(prefix="/robots", tags=["robots"])


def _service(service: SimulationService = Depends(get_simulation_service)) -> SimulationService:
    return service


@router.get("/health", response_model=List[RobotHealthSchema])
async def robot_health(service: SimulationService = Depends(_service)) -> List[RobotHealthSchema]:
    statuses = service.health_monitor.statuses()
    return [RobotHealthSchema.from_status(status) for status in statuses.values()]


@router.post("/{robot_id}/recover", status_code=status.HTTP_204_NO_CONTENT)
async def recover_robot(robot_id: str, service: SimulationService = Depends(_service)) -> None:
    status_obj = service.health_monitor.status(robot_id)
    if not status_obj or not status_obj.faulted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Robot not faulted")
    service.clear_fault(robot_id)
