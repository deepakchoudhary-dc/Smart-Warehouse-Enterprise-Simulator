"""Scenario management endpoints for enterprise simulation runs."""

from __future__ import annotations

import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status

from smart_warehouse.server.api.schemas.scenarios import (
    RunTickSchema,
    ScenarioConfigSchema,
    ScenarioRunDetailSchema,
    ScenarioRunSchema,
    ScenarioSummarySchema,
    RunMetricsSchema,
    TimelineEventSchema,
)
from smart_warehouse.server.api.schemas.simulation import SimulationStateSchema
from smart_warehouse.server.dependencies import get_scenario_engine
from smart_warehouse.services.scenario_engine import RunStage, RunTick, ScenarioEngine

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


async def _get_engine() -> ScenarioEngine:
    return get_scenario_engine()


@router.get("/", response_model=List[ScenarioSummarySchema])
async def list_scenarios(engine: ScenarioEngine = Depends(_get_engine)) -> List[ScenarioSummarySchema]:
    definitions = await engine.list_scenarios()
    return [ScenarioSummarySchema.from_definition(item) for item in definitions]


@router.post("/", response_model=ScenarioSummarySchema, status_code=status.HTTP_201_CREATED)
async def create_scenario(
    payload: ScenarioConfigSchema,
    engine: ScenarioEngine = Depends(_get_engine),
) -> ScenarioSummarySchema:
    definition = await engine.create_scenario(payload.to_config())
    return ScenarioSummarySchema.from_definition(definition)


@router.post("/{scenario_id}/launch", response_model=ScenarioRunSchema, status_code=status.HTTP_202_ACCEPTED)
async def launch_scenario(scenario_id: str, engine: ScenarioEngine = Depends(_get_engine)) -> ScenarioRunSchema:
    try:
        run = await engine.launch_run(scenario_id)
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Scenario {scenario_id} not found") from exc
    return ScenarioRunSchema.from_run(run)


@router.get("/runs", response_model=List[ScenarioRunSchema])
async def list_runs(engine: ScenarioEngine = Depends(_get_engine)) -> List[ScenarioRunSchema]:
    runs = await engine.list_runs()
    return [ScenarioRunSchema.from_run(run) for run in runs]


@router.get("/runs/{run_id}", response_model=ScenarioRunDetailSchema)
async def get_run(run_id: str, engine: ScenarioEngine = Depends(_get_engine)) -> ScenarioRunDetailSchema:
    try:
        run = await engine.get_run(run_id)
        scenario = await engine.get_scenario(run.scenario_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found") from exc

    state_schema = None
    if run.last_snapshot:
        layout = scenario.config.layout.to_layout()
        state_schema = SimulationStateSchema.from_domain(run.last_snapshot, layout)
    detail = ScenarioRunDetailSchema(
        **ScenarioRunSchema.from_run(run).model_dump(),
        state=state_schema,
        timeline=[TimelineEventSchema.from_event(evt) for evt in run.timeline],
    )
    return detail


@router.get("/runs/{run_id}/timeline", response_model=List[TimelineEventSchema])
async def get_run_timeline(run_id: str, engine: ScenarioEngine = Depends(_get_engine)) -> List[TimelineEventSchema]:
    try:
        timeline = await engine.get_timeline(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found") from exc
    return [TimelineEventSchema.from_event(evt) for evt in timeline]


@router.post("/runs/{run_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel_run(run_id: str, engine: ScenarioEngine = Depends(_get_engine)) -> None:
    try:
        await engine.cancel_run(run_id)
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found") from exc


@router.websocket("/runs/{run_id}/stream")
async def run_stream(websocket: WebSocket, run_id: str) -> None:
    engine = await _get_engine()
    try:
        run = await engine.get_run(run_id)
        scenario = await engine.get_scenario(run.scenario_id)
    except KeyError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    layout = scenario.config.layout.to_layout()
    async def convert(tick: RunTick) -> dict:
        state_schema = SimulationStateSchema.from_domain(tick.state, layout)
        payload = RunTickSchema(
            stage=tick.stage,
            elapsed_seconds=tick.elapsed_seconds,
            state=state_schema,
            metrics=RunMetricsSchema.from_metrics(tick.metrics),
            heatmap=dict(tick.heatmap),
            recent_events=[TimelineEventSchema.from_event(evt) for evt in tick.recent_events],
        )
        return json.loads(payload.model_dump_json())

    try:
        async for tick in engine.subscribe(run_id):
            payload = await convert(tick)
            await websocket.send_json(payload)
            if tick.stage in {RunStage.COMPLETED, RunStage.FAILED, RunStage.CANCELLED}:
                return
    except WebSocketDisconnect:  # pragma: no cover - client initiated
        return
    except KeyError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    except Exception as exc:  # pragma: no cover - runtime guard
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason=str(exc))
