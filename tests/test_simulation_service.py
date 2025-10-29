from smart_warehouse.enterprise.core import GridPosition, Package, PackageStatus, RobotState
from smart_warehouse.enterprise.core.models import RobotTelemetry
from smart_warehouse.services.simulation import SimulationService


def _telemetry(robot_id: str, position: GridPosition, state: RobotState) -> RobotTelemetry:
    return RobotTelemetry(robot_id=robot_id, state=state, position=position, path=[])


def test_plan_path_returns_grid_positions():
    service = SimulationService()
    start = GridPosition(x=0, y=0)
    end = GridPosition(x=2, y=0)

    path = service.plan_path(start, end)

    assert path
    assert path[-1].x == end.x and path[-1].y == end.y


def test_assign_jobs_marks_packages_assigned():
    service = SimulationService()
    package = Package(position=GridPosition(x=1, y=1))
    service.simulator.packages.append(package)

    telemetry = [_telemetry("AGV-1", GridPosition(x=0, y=0), RobotState.IDLE)]
    assignments = service.assign_jobs(telemetry)

    assert "AGV-1" in assignments
    assert assignments["AGV-1"].id == package.id
    assert package.assigned_robot == "AGV-1"
    assert package.status == PackageStatus.ASSIGNED


def test_dropoff_for_returns_known_zone():
    service = SimulationService()
    dropoff = service.dropoff_for(GridPosition(x=0, y=0))
    assert dropoff in service.context.layout.dropoff_zones
