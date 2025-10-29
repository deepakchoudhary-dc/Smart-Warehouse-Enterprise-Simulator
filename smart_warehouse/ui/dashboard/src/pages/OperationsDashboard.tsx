import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";

import {
  cancelRun,
  createScenario,
  fetchRunDetail,
  fetchRunTimeline,
  fetchScenarioRuns,
  fetchScenarios,
  launchScenario,
  subscribeToRun,
} from "../api";
import { MetricsPanel } from "../components/MetricsPanel";
import { RunHistoryList } from "../components/RunHistoryList";
import { RunPlaybackControls } from "../components/RunPlaybackControls";
import { RunTimeline } from "../components/RunTimeline";
import { ScenarioCatalog } from "../components/ScenarioCatalog";
import { ScenarioWizard } from "../components/ScenarioWizard";
import { StageIndicator } from "../components/StageIndicator";
import { WarehouseCanvas } from "../components/WarehouseCanvas";
import type {
  Layout,
  RunStage,
  RunTick,
  ScenarioRun,
  ScenarioRunDetail,
  ScenarioSummary,
  TimelineEventDetail,
} from "../types";

const TICK_HISTORY_LIMIT = 900;
const TIMELINE_LIMIT = 200;

export function OperationsDashboard() {
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [runs, setRuns] = useState<ScenarioRun[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<ScenarioSummary | null>(null);
  const [activeRun, setActiveRun] = useState<ScenarioRunDetail | null>(null);
  const [timeline, setTimeline] = useState<TimelineEventDetail[]>([]);
  const [tickHistory, setTickHistory] = useState<RunTick[]>([]);
  const [mode, setMode] = useState<"live" | "replay">("live");
  const [cursor, setCursor] = useState(0);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [isCreatingScenario, setIsCreatingScenario] = useState(false);
  const [launchingScenarioId, setLaunchingScenarioId] = useState<string | null>(null);
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [toast, setToast] = useState<{ message: string; tone: "success" | "error" } | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const modeRef = useRef<"live" | "replay">("live");
  const activeRunIdRef = useRef<string | null>(null);
  const runStageRef = useRef<RunStage | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);

  const activeTick = useMemo(() => {
    if (!tickHistory.length) {
      return null;
    }
    if (mode === "replay") {
      return tickHistory[cursor] ?? tickHistory[tickHistory.length - 1];
    }
    return tickHistory[tickHistory.length - 1];
  }, [cursor, mode, tickHistory]);

  const currentState = activeTick?.state ?? activeRun?.state ?? null;
  const currentMetrics = activeTick?.metrics ?? activeRun?.metrics ?? null;
  const currentHeatmap = activeTick?.heatmap ?? activeRun?.heatmap ?? {};

  const recentTimeline = useMemo(() => timeline.slice(-40).reverse(), [timeline]);

  const activeScenario = useMemo(() => {
    if (activeRun) {
      const match = scenarios.find((item) => item.id === activeRun.scenario_id);
      if (match) {
        return match;
      }
    }
    return selectedScenario;
  }, [activeRun, scenarios, selectedScenario]);

  const fallbackLayout = useMemo(() => {
    if (!activeScenario) {
      return null;
    }
    const layout = activeScenario.config.layout;
    return {
      width: layout.width,
      height: layout.height,
      cell_size: layout.cell_size,
      obstacles: layout.obstacles,
      pickup_zones: layout.pickup_zones,
      dropoff_zones: layout.dropoff_zones,
      charging_zones: layout.charging_zones,
    } satisfies Layout;
  }, [activeScenario]);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current !== null) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const closeSocket = useCallback(() => {
    clearReconnectTimer();
    if (socketRef.current) {
      try {
        socketRef.current.close(1000, "client closing");
      } catch (err) {
        console.warn("Failed to close socket", err);
      }
      socketRef.current = null;
    }
  }, [clearReconnectTimer]);

  const refreshScenarios = useCallback(async () => {
    try {
      const list = await fetchScenarios();
      setScenarios(list);
      setSelectedScenario((previous) => {
        if (previous) {
          const updated = list.find((item) => item.id === previous.id);
          if (updated) {
            return updated;
          }
        }
        return list[0] ?? null;
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to load scenarios";
      setToast({ message, tone: "error" });
    }
  }, []);

  const refreshRuns = useCallback(async () => {
    try {
      const list = await fetchScenarioRuns();
      setRuns(list);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to load runs";
      setToast({ message, tone: "error" });
    }
  }, []);

  useEffect(() => {
    refreshScenarios();
    refreshRuns();
    return closeSocket;
  }, [closeSocket, refreshRuns, refreshScenarios]);

  useEffect(() => {
    modeRef.current = mode;
    if (mode === "live" && tickHistory.length) {
      setCursor(tickHistory.length - 1);
    }
  }, [mode, tickHistory.length]);

  useEffect(() => {
    if (activeRun) {
      activeRunIdRef.current = activeRun.id;
      runStageRef.current = activeRun.stage;
    } else {
      activeRunIdRef.current = null;
      runStageRef.current = null;
    }
  }, [activeRun]);

  useEffect(() => {
    if (!toast) {
      return;
    }
    const timer = window.setTimeout(() => setToast(null), 4_000);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const handleTick = useCallback(
    (tick: RunTick) => {
      const runId = activeRunIdRef.current;
      runStageRef.current = tick.stage;
      setTickHistory((previous) => {
        const next = [...previous, tick];
        if (next.length > TICK_HISTORY_LIMIT) {
          next.shift();
        }
        if (modeRef.current === "live") {
          setCursor(next.length - 1);
        }
        return next;
      });
      if (runId) {
        setRuns((previous) =>
          previous.map((run) =>
            run.id === runId
              ? {
                  ...run,
                  stage: tick.stage,
                  metrics: tick.metrics,
                  heatmap: tick.heatmap,
                }
              : run,
          ),
        );
      }
      setActiveRun((previous) =>
        previous
          ? {
              ...previous,
              stage: tick.stage,
              metrics: tick.metrics,
              heatmap: tick.heatmap,
              state: tick.state,
            }
          : previous,
      );
      if (tick.recent_events.length) {
        setTimeline((previous) => {
          const merged = [...previous, ...tick.recent_events];
          if (merged.length > TIMELINE_LIMIT) {
            return merged.slice(merged.length - TIMELINE_LIMIT);
          }
          return merged;
        });
      }
      if (tick.stage === "COMPLETED" || tick.stage === "FAILED" || tick.stage === "CANCELLED") {
        void refreshRuns();
      }
    },
    [refreshRuns],
  );

  const attachRunStream = useCallback(
    (runId: string) => {
      const shouldReconnect = () => {
        if (activeRunIdRef.current !== runId) {
          return false;
        }
        const stage = runStageRef.current;
        return stage == null || stage === "WARMING_UP" || stage === "RUNNING";
      };

      const scheduleReconnect = (attempt: number) => {
        clearReconnectTimer();
        if (!shouldReconnect()) {
          reconnectTimerRef.current = null;
          refreshRuns();
          return;
        }
        if (attempt >= 5) {
          setToast({ message: "Run stream lost connection", tone: "error" });
          reconnectTimerRef.current = null;
          refreshRuns();
          return;
        }
        const delay = Math.min(5, attempt + 1) * 1000;
        reconnectTimerRef.current = window.setTimeout(() => connect(attempt + 1), delay);
      };

      function connect(attempt = 0): void {
        clearReconnectTimer();
        activeRunIdRef.current = runId;
        closeSocket();
        const socket = subscribeToRun(
          runId,
          (tick) => {
            handleTick(tick);
          },
          (event) => {
            console.warn("Run stream error", event);
            if (attempt === 0) {
              setToast({ message: "Run stream interrupted, reconnecting...", tone: "error" });
            }
            scheduleReconnect(attempt);
          },
          (event) => {
            socketRef.current = null;
            if (event.wasClean || !shouldReconnect()) {
              clearReconnectTimer();
              refreshRuns();
              return;
            }
            scheduleReconnect(attempt);
          },
        );
        socketRef.current = socket;
      }

      connect();
    },
    [clearReconnectTimer, closeSocket, handleTick, refreshRuns, setToast],
  );

  const handleScenarioCreate = useCallback(
    async (config: Parameters<typeof createScenario>[0]) => {
      setIsCreatingScenario(true);
      try {
        const created = await createScenario(config);
        setScenarios((previous) => [created, ...previous]);
        setSelectedScenario(created);
        setWizardOpen(false);
        setToast({ message: "Scenario created", tone: "success" });
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unable to create scenario";
        setToast({ message, tone: "error" });
      } finally {
        setIsCreatingScenario(false);
      }
    },
    [],
  );

  const handleRunSelect = useCallback(
    async (runId: string) => {
      try {
        const [detail, timelineSeed] = await Promise.all([fetchRunDetail(runId), fetchRunTimeline(runId)]);
        runStageRef.current = detail.stage;
        activeRunIdRef.current = detail.id;
        setActiveRun(detail);
        setTimeline(timelineSeed.slice(-TIMELINE_LIMIT));
        setSelectedScenario((previous) => {
          if (previous?.id === detail.scenario_id) {
            return previous;
          }
          const matched = scenarios.find((item) => item.id === detail.scenario_id);
          return matched ?? previous ?? null;
        });

        const seedTick: RunTick[] = detail.state
          ? [
              {
                stage: detail.stage,
                elapsed_seconds: 0,
                state: detail.state,
                metrics: detail.metrics,
                heatmap: detail.heatmap,
                recent_events: [],
              },
            ]
          : [];

        setTickHistory(seedTick);
        const isLive = detail.stage === "RUNNING" || detail.stage === "WARMING_UP";
        setMode(isLive ? "live" : seedTick.length ? "replay" : "live");
        setCursor(seedTick.length ? seedTick.length - 1 : 0);

        if (isLive) {
          attachRunStream(runId);
        } else {
          closeSocket();
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unable to load run";
        setToast({ message, tone: "error" });
      }
    },
    [attachRunStream, closeSocket, scenarios],
  );

  const handleLaunch = useCallback(
    async (scenario: ScenarioSummary) => {
      setLaunchingScenarioId(scenario.id);
      try {
        const run = await launchScenario(scenario.id);
        await refreshRuns();
        setToast({ message: `Run launched for ${scenario.config.name}`, tone: "success" });
        handleRunSelect(run.id);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to launch run";
        setToast({ message, tone: "error" });
      } finally {
        setLaunchingScenarioId(null);
      }
    },
    [handleRunSelect, refreshRuns],
  );

  const handleCancelRun = useCallback(async () => {
    if (!activeRun) {
      return;
    }
    try {
      await cancelRun(activeRun.id);
      setToast({ message: "Run cancellation requested", tone: "success" });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to cancel run";
      setToast({ message, tone: "error" });
    }
  }, [activeRun]);

  const scenarioName = useMemo(() => {
    if (!activeRun) {
      return selectedScenario?.config.name ?? "";
    }
    const scenario = scenarios.find((item) => item.id === activeRun.scenario_id);
    return scenario?.config.name ?? selectedScenario?.config.name ?? "Scenario";
  }, [activeRun, scenarios, selectedScenario]);

  useEffect(() => {
    if (!selectedScenario) {
      return;
    }
    if (!runs.length) {
      return;
    }
    const matchingRuns = runs
      .filter((run) => run.scenario_id === selectedScenario.id)
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    if (!matchingRuns.length) {
      return;
    }
    const preferred = matchingRuns.find((run) => run.stage === "RUNNING" || run.stage === "WARMING_UP") ?? matchingRuns[0];
    if (preferred && preferred.id !== activeRun?.id) {
      void handleRunSelect(preferred.id);
    }
  }, [activeRun?.id, handleRunSelect, runs, selectedScenario]);

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>Smart Warehouse Enterprise Simulator</h1>
          <p>Design operational scenarios, launch digital twins, and inspect fulfillment KPIs in real time.</p>
        </div>
        <div className="header-actions">
          <Link to="/analytics" className="ghost nav-link">
            Analytics hub
          </Link>
          <button type="button" className="secondary" onClick={() => setWizardOpen(true)}>
            New scenario
          </button>
        </div>
      </header>

      <main className="app-workspace">
        <aside className="workspace-sidebar">
          <section className="panel">
            <header className="panel-header">
              <div>
                <h2>Scenario library</h2>
                <p className="panel-caption">Curated enterprise scenarios ready for execution.</p>
              </div>
            </header>
            <ScenarioCatalog
              scenarios={scenarios}
              selectedScenarioId={selectedScenario?.id}
              launchingScenarioId={launchingScenarioId}
              onSelect={setSelectedScenario}
              onLaunch={handleLaunch}
            />
          </section>

          <section className="panel">
            <header className="panel-header">
              <div>
                <h2>Run history</h2>
                <p className="panel-caption">Inspect previous executions and pick one to replay.</p>
              </div>
            </header>
            <RunHistoryList
              runs={runs}
              scenarios={scenarios}
              activeRunId={activeRun?.id ?? undefined}
              onSelectRun={handleRunSelect}
            />
          </section>

          {selectedScenario ? (
            <section className="panel scenario-detail">
              <header className="panel-header">
                <h2>Scenario insight</h2>
                <p className="panel-caption">Key levers for {selectedScenario.config.name}</p>
              </header>
              <ul>
                <li><strong>Layout:</strong> {selectedScenario.config.layout.width}×{selectedScenario.config.layout.height}</li>
                <li><strong>Fleet:</strong> {selectedScenario.config.fleet.total_robots} robots</li>
                <li><strong>Demand:</strong> {selectedScenario.config.demand.packages_per_hour} packages/hr</li>
                <li><strong>Horizon:</strong> {selectedScenario.config.horizon.duration_minutes} min</li>
              </ul>
            </section>
          ) : null}
        </aside>

        <section className="workspace-main">
          {activeRun ? (
            <>
              <div className="run-header">
                <div>
                  <h2>{scenarioName}</h2>
                  <p>
                    Run #{activeRun.id.slice(0, 8)} · <StageIndicator stage={activeRun.stage} />
                  </p>
                </div>
                <div className="run-actions">
                  <label className="heatmap-toggle">
                    <input type="checkbox" checked={showHeatmap} onChange={(event) => setShowHeatmap(event.target.checked)} />
                    Heatmap
                  </label>
                  <button type="button" className="ghost" onClick={() => setMode(mode === "live" ? "replay" : "live")}>
                    {mode === "live" ? "Switch to replay" : "Go live"}
                  </button>
                  <button
                    type="button"
                    className="ghost"
                    onClick={handleCancelRun}
                    disabled={activeRun.stage !== "RUNNING" && activeRun.stage !== "WARMING_UP"}
                  >
                    Cancel run
                  </button>
                </div>
              </div>

              <RunPlaybackControls
                mode={mode}
                historyLength={tickHistory.length}
                cursor={cursor}
                onModeChange={setMode}
                onSeek={setCursor}
              />

              <section className="canvas-panel" aria-label="Scenario visualization">
                <WarehouseCanvas
                  layout={currentState?.layout ?? fallbackLayout}
                  packages={currentState?.packages ?? []}
                  robots={currentState?.robots ?? []}
                  reservations={currentState?.reservations ?? []}
                  heatmap={showHeatmap ? currentHeatmap : undefined}
                  showHeatmap={showHeatmap}
                />
              </section>

              <div className="main-panels">
                <MetricsPanel metrics={currentMetrics} />
                <RunTimeline events={recentTimeline} />
              </div>
            </>
          ) : (
            <div className="empty-state hero">
              <h2>No run selected</h2>
              <p>Select a scenario and launch a run to see the warehouse digital twin in action.</p>
            </div>
          )}
        </section>
      </main>

      {wizardOpen ? (
        <div className="wizard-overlay">
          <ScenarioWizard
            onSubmit={handleScenarioCreate}
            onCancel={() => setWizardOpen(false)}
            isSubmitting={isCreatingScenario}
          />
        </div>
      ) : null}

      {toast ? (
        <div className="toast-container" role="status" aria-live="polite">
          <div className={`toast ${toast.tone}`}>{toast.message}</div>
        </div>
      ) : null}
    </div>
  );
}
