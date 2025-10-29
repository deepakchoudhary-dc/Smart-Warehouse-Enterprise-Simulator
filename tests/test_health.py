from smart_warehouse.enterprise.core import GridPosition, RobotState
from smart_warehouse.services.health import RobotHealthMonitor


def test_monitor_flags_fault_after_stall():
    monitor = RobotHealthMonitor(max_stalled_ticks=2)
    monitor.observe("AGV-1", GridPosition(x=0, y=0), RobotState.FETCHING)
    status = monitor.observe("AGV-1", GridPosition(x=0, y=0), RobotState.FETCHING)
    assert not status.faulted
    status = monitor.observe("AGV-1", GridPosition(x=0, y=0), RobotState.FETCHING)
    assert status.faulted


def test_monitor_resets_on_movement():
    monitor = RobotHealthMonitor(max_stalled_ticks=2)
    monitor.observe("AGV-1", GridPosition(x=1, y=1), RobotState.FETCHING)
    monitor.observe("AGV-1", GridPosition(x=1, y=1), RobotState.FETCHING)
    status = monitor.observe("AGV-1", GridPosition(x=2, y=1), RobotState.FETCHING)
    assert status.stalled_ticks == 0
    assert not status.faulted
