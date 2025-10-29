from datetime import timedelta

from smart_warehouse.enterprise.core import GridPosition
from smart_warehouse.services.reservations import ReservationManager


def test_reservation_claim_and_release():
    manager = ReservationManager()
    position = GridPosition(x=2, y=3)

    reservation = manager.claim("robot-1", position, ttl_seconds=5)
    assert manager.is_reserved(position)
    assert reservation.position == position

    manager.release("robot-1")
    assert not manager.is_reserved(position)


def test_reservation_expiry(monkeypatch):
    manager = ReservationManager()
    position = GridPosition(x=4, y=5)
    reservation = manager.claim("robot-2", position, ttl_seconds=1)

    expired = reservation.model_copy(update={"created_at": reservation.created_at - timedelta(seconds=5)})
    manager._reservations["robot-2"] = expired

    assert not manager.is_reserved(position)
