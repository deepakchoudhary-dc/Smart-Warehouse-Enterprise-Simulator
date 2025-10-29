import asyncio
from datetime import datetime

from smart_warehouse.services.scenario_engine import RunStage, ScenarioEngine


async def main() -> None:
    engine = ScenarioEngine()
    scenario = (await engine.list_scenarios())[0]
    run = await engine.launch_run(scenario.id)
    last_tick_at: datetime | None = None
    count = 0
    async for tick in engine.subscribe(run.id):
        now = datetime.utcnow()
        if last_tick_at is None:
            print("first tick", tick.stage.value)
        else:
            delta = (now - last_tick_at).total_seconds()
            print(f"next tick after {delta:.2f}s stage={tick.stage.value} elapsed={tick.elapsed_seconds:.1f}")
        last_tick_at = now
        count += 1
        if count >= 6 or tick.stage not in {RunStage.WARMING_UP, RunStage.RUNNING}:
            break
    await engine.cancel_run(run.id)


if __name__ == "__main__":
    asyncio.run(main())
