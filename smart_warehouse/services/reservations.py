"""Reservation management utilities for the warehouse simulation."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Optional

from smart_warehouse.enterprise.core.models import GridPosition, Reservation


class ReservationManager:
	"""Tracks cell reservations with automatic TTL eviction."""

	def __init__(self) -> None:
		self._reservations: Dict[str, Reservation] = {}

	def claim(self, robot_id: str, position: GridPosition, ttl_seconds: int = 3) -> Reservation:
		reservation = Reservation(robot_id=robot_id, position=position, ttl_seconds=ttl_seconds)
		self._reservations[robot_id] = reservation
		return reservation

	def release(self, robot_id: str) -> None:
		self._reservations.pop(robot_id, None)

	def reservations(self) -> List[Reservation]:
		self._purge_expired()
		return list(self._reservations.values())

	def get(self, robot_id: str) -> Optional[Reservation]:
		self._purge_expired()
		return self._reservations.get(robot_id)

	def is_reserved(self, position: GridPosition, exclude_robot: Optional[str] = None) -> bool:
		self._purge_expired()
		for robot, reservation in self._reservations.items():
			if exclude_robot and robot == exclude_robot:
				continue
			if reservation.position.x == position.x and reservation.position.y == position.y:
				return True
		return False

	def _purge_expired(self) -> None:
		now = datetime.utcnow()
		expired = [rid for rid, res in self._reservations.items() if res.is_expired(now)]
		for rid in expired:
			self._reservations.pop(rid, None)

	def reset(self) -> None:
		self._reservations.clear()
