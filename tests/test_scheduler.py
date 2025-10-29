from smart_warehouse.enterprise.core import GridPosition, Package, PackageStatus, RobotState
from smart_warehouse.services.scheduler import TaskScheduler


def test_scheduler_assigns_closest_package():
    scheduler = TaskScheduler()
    packages = [
        Package(position=GridPosition(x=1, y=1)),
        Package(position=GridPosition(x=5, y=5)),
    ]

    assignment = scheduler.select_job(
        robot_id="AGV-1",
        robot_position=GridPosition(x=0, y=0),
        robot_state=RobotState.IDLE,
        packages=packages,
    )
    assert assignment is not None
    assert assignment.id == packages[0].id

    packages[0].status = PackageStatus.ASSIGNED
    assignment = scheduler.select_job(
        robot_id="AGV-2",
        robot_position=GridPosition(x=4, y=4),
        robot_state=RobotState.IDLE,
        packages=packages,
        assignments={"AGV-1": packages[0].id},
    )
    assert assignment is not None
    assert assignment.id == packages[1].id


def test_scheduler_respects_robot_state():
    scheduler = TaskScheduler()
    package = Package(position=GridPosition(x=2, y=2))

    assignment = scheduler.select_job(
        robot_id="AGV-1",
        robot_position=GridPosition(x=0, y=0),
        robot_state=RobotState.DELIVERING,
        packages=[package],
    )
    assert assignment is None
