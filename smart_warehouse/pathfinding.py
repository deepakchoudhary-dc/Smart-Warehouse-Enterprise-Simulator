"""Pathfinding algorithms for the simulation."""

from __future__ import annotations

import heapq
from collections import deque
from typing import Dict, Iterable, List, Optional, Set, Tuple


def manhattan(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def find_path_bfs(
    start: Tuple[int, int],
    end: Tuple[int, int],
    obstacles: Set[Tuple[int, int]],
    grid_width: int,
    grid_height: int,
    forbidden: Optional[Iterable[Tuple[int, int]]] = None,
) -> Optional[List[Tuple[int, int]]]:
    """Compute a path using BFS, optionally avoiding forbidden cells."""

    blocked = set(obstacles)
    if forbidden:
        blocked.update(forbidden)

    queue = deque([(start, [start])])
    visited = {start}

    while queue:
        (x, y), path = queue.popleft()

        if (x, y) == end:
            return path

        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < grid_width and 0 <= ny < grid_height):
                continue
            if (nx, ny) in visited or (nx, ny) in blocked:
                continue
            visited.add((nx, ny))
            queue.append(((nx, ny), path + [(nx, ny)]))

    return None


def find_path_astar(
    start: Tuple[int, int],
    end: Tuple[int, int],
    obstacles: Set[Tuple[int, int]],
    grid_width: int,
    grid_height: int,
    reservations: Optional[Dict[int, Set[Tuple[int, int]]]] = None,
    max_cost: int = 512,
) -> Optional[List[Tuple[int, int]]]:
    """A* pathfinding that accounts for time-indexed reservations."""

    open_set: list[Tuple[int, int, Tuple[int, int], List[Tuple[int, int]], int]] = []
    heapq.heappush(open_set, (manhattan(start, end), 0, start, [start], 0))
    visited: Dict[Tuple[int, int], int] = {start: 0}

    reservations = reservations or {}

    while open_set:
        _score, cost, node, path, time = heapq.heappop(open_set)
        if node == end:
            return path

        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = node[0] + dx, node[1] + dy
            if not (0 <= nx < grid_width and 0 <= ny < grid_height):
                continue
            if (nx, ny) in obstacles:
                continue

            next_time = time + 1
            if (next_time in reservations and (nx, ny) in reservations[next_time]) or (
                next_time - 1 in reservations and (nx, ny) in reservations[next_time - 1]
            ):
                continue

            new_cost = cost + 1
            if new_cost > max_cost:
                continue

            if (nx, ny) in visited and visited[(nx, ny)] <= new_cost:
                continue
            visited[(nx, ny)] = new_cost

            new_path = path + [(nx, ny)]
            priority = new_cost + manhattan((nx, ny), end)
            heapq.heappush(open_set, (priority, new_cost, (nx, ny), new_path, next_time))

    return None


def build_reservation_table(paths: Dict[str, List[Tuple[int, int]]]) -> Dict[int, Set[Tuple[int, int]]]:
    """Convert robot paths into a time-indexed reservation lookup."""

    table: Dict[int, Set[Tuple[int, int]]] = {}
    for path in paths.values():
        for time, cell in enumerate(path, start=1):
            table.setdefault(time, set()).add(cell)
    return table