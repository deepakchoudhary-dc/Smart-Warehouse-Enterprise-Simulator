import { FormEvent, useMemo, useState } from "react";

import type { GridPosition, ScenarioConfig } from "../types";

interface ScenarioWizardProps {
  onSubmit: (config: ScenarioConfig) => Promise<void>;
  onCancel: () => void;
  isSubmitting?: boolean;
}

interface StepState {
  name: string;
  description: string;
  width: number;
  height: number;
  cellSize: number;
  pickupZones: string;
  dropoffZones: string;
  obstacles: string;
  chargingZones: string;
  totalRobots: number;
  startingPositions: string;
  speedCellsPerTick: number;
  payloadCapacity: number;
  batteryMinutes: number;
  packagesPerHour: number;
  priorityStandard: number;
  priorityExpress: number;
  slaStandard: number;
  slaExpress: number;
  cadenceMs: number;
  warmupMinutes: number;
  shiftMinutes: number;
  timeScale: number;
  faultProbability: number;
  meanRecovery: number;
  reservationHorizon: number;
  assignmentPolicy: string;
  planner: string;
  horizonMinutes: number;
  stopOnCompletion: boolean;
  metadataNotes: string;
}

const DEFAULT_STATE: StepState = {
  name: "Custom Enterprise Scenario",
  description: "Operator-authored scenario deploying enterprise constraints.",
  width: 24,
  height: 16,
  cellSize: 32,
  pickupZones: "1:4;1:6;1:8",
  dropoffZones: "22:5;22:9",
  obstacles: "10:2-10:13",
  chargingZones: "2:2;2:13",
  totalRobots: 6,
  startingPositions: "0:1;0:3;0:5;0:7;0:9;0:11",
  speedCellsPerTick: 1.0,
  payloadCapacity: 1,
  batteryMinutes: 240,
  packagesPerHour: 120,
  priorityStandard: 0.6,
  priorityExpress: 0.4,
  slaStandard: 30,
  slaExpress: 12,
  cadenceMs: 400,
  warmupMinutes: 2,
  shiftMinutes: 120,
  timeScale: 12,
  faultProbability: 0.1,
  meanRecovery: 4,
  reservationHorizon: 6,
  assignmentPolicy: "hungarian",
  planner: "astar",
  horizonMinutes: 30,
  stopOnCompletion: false,
  metadataNotes: "Created via dashboard wizard",
};

function parseCoordinateList(value: string): GridPosition[] {
  return value
    .split(/;|\n|,/)
    .map((segment) => segment.trim())
    .filter(Boolean)
    .flatMap((segment) => {
      if (segment.includes("-")) {
        const [start, end] = segment.split("-");
        const [sx, sy] = start.split(":").map((v) => Number.parseInt(v.trim(), 10));
        const [ex, ey] = end.split(":").map((v) => Number.parseInt(v.trim(), 10));
        if ([sx, sy, ex, ey].some((val) => Number.isNaN(val))) {
          return [];
        }
        const positions: GridPosition[] = [];
        if (sx === ex) {
          const [minY, maxY] = sy < ey ? [sy, ey] : [ey, sy];
          for (let y = minY; y <= maxY; y += 1) {
            positions.push({ x: sx, y });
          }
        } else if (sy === ey) {
          const [minX, maxX] = sx < ex ? [sx, ex] : [ex, sx];
          for (let x = minX; x <= maxX; x += 1) {
            positions.push({ x, y: sy });
          }
        }
        return positions;
      }
      const [xStr, yStr] = segment.split(":");
      const x = Number.parseInt(xStr?.trim() ?? "", 10);
      const y = Number.parseInt(yStr?.trim() ?? "", 10);
      if (Number.isNaN(x) || Number.isNaN(y)) {
        return [];
      }
      return [{ x, y }];
    });
}

function parseStartingPositions(value: string): GridPosition[] {
  const positions = parseCoordinateList(value);
  if (positions.length === 0) {
    return [{ x: 0, y: 0 }];
  }
  return positions;
}

function sanitizeProbability(value: number): number {
  if (value < 0) {
    return 0;
  }
  if (value > 1) {
    return 1;
  }
  return Number.isFinite(value) ? value : 0;
}

const steps = ["Layout", "Operations", "Review"] as const;

type Step = (typeof steps)[number];

export function ScenarioWizard({ onSubmit, onCancel, isSubmitting }: ScenarioWizardProps) {
  const [form, setForm] = useState<StepState>(DEFAULT_STATE);
  const [step, setStep] = useState<Step>("Layout");
  const [error, setError] = useState<string | null>(null);

  const priorityMix = useMemo(() => {
    const standard = sanitizeProbability(form.priorityStandard);
    const express = sanitizeProbability(form.priorityExpress);
    const total = standard + express || 1;
    return {
      standard: Number((standard / total).toFixed(2)),
      express: Number((express / total).toFixed(2)),
    };
  }, [form.priorityExpress, form.priorityStandard]);

  function update<K extends keyof StepState>(key: K, value: StepState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function buildScenarioConfig(): ScenarioConfig {
    const pickupZones = parseCoordinateList(form.pickupZones);
    const dropoffZones = parseCoordinateList(form.dropoffZones);
    const obstacles = parseCoordinateList(form.obstacles);
    const chargingZones = parseCoordinateList(form.chargingZones);
    const startingPositions = parseStartingPositions(form.startingPositions);

    return {
      name: form.name,
      description: form.description,
      layout: {
        width: form.width,
        height: form.height,
        cell_size: form.cellSize,
        pickup_zones: pickupZones,
        dropoff_zones: dropoffZones,
        obstacles,
        charging_zones: chargingZones,
      },
      fleet: {
        total_robots: form.totalRobots,
        classes: [
          {
            name: "AGV",
            speed_cells_per_tick: form.speedCellsPerTick,
            payload_capacity: form.payloadCapacity,
            battery_capacity_minutes: form.batteryMinutes,
          },
        ],
        starting_positions: startingPositions,
      },
      demand: {
        packages_per_hour: form.packagesPerHour,
        priority_mix: {
          standard: priorityMix.standard,
          express: priorityMix.express,
        },
        sla_minutes: {
          standard: form.slaStandard,
          express: form.slaExpress,
        },
      },
      operations: {
        shift_minutes: form.shiftMinutes,
        cadence_ms: form.cadenceMs,
        warmup_minutes: form.warmupMinutes,
        time_scale: form.timeScale,
      },
      failures: {
        fault_probability_per_hour: sanitizeProbability(form.faultProbability),
        mean_recovery_minutes: form.meanRecovery,
      },
      optimization: {
        planner: form.planner,
        assignment_policy: form.assignmentPolicy,
        reservation_horizon: form.reservationHorizon,
      },
      horizon: {
        duration_minutes: form.horizonMinutes,
        stop_on_completion: form.stopOnCompletion,
      },
      metadata: {
        notes: form.metadataNotes,
        createdFromWizard: true,
      },
    };
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      setError(null);
      await onSubmit(buildScenarioConfig());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create scenario");
    }
  }

  function nextStep() {
    if (step === "Layout") {
      setStep("Operations");
    } else if (step === "Operations") {
      setStep("Review");
    }
  }

  function prevStep() {
    if (step === "Operations") {
      setStep("Layout");
    } else if (step === "Review") {
      setStep("Operations");
    }
  }

  return (
    <form className="scenario-wizard" onSubmit={handleSubmit}>
      <header className="wizard-header">
        <div>
          <h2>Scenario Builder</h2>
          <p>Capture layout, demand, and operational constraints to simulate enterprise workloads.</p>
        </div>
        <div className="wizard-steps">
          {steps.map((label) => (
            <span key={label} className={label === step ? "active" : ""}>{label}</span>
          ))}
        </div>
      </header>

      <div className="wizard-content">
        {step === "Layout" && (
          <section className="wizard-section">
            <h3>Layout & Inventory Zones</h3>
            <div className="wizard-grid">
              <label>
                Scenario name
                <input value={form.name} onChange={(event) => update("name", event.target.value)} required />
              </label>
              <label>
                Description
                <input value={form.description} onChange={(event) => update("description", event.target.value)} required />
              </label>
              <label>
                Grid width
                <input type="number" min={8} value={form.width} onChange={(event) => update("width", Number(event.target.value))} required />
              </label>
              <label>
                Grid height
                <input type="number" min={8} value={form.height} onChange={(event) => update("height", Number(event.target.value))} required />
              </label>
              <label>
                Cell size (px)
                <input type="number" min={16} value={form.cellSize} onChange={(event) => update("cellSize", Number(event.target.value))} required />
              </label>
            </div>
            <div className="wizard-grid">
              <label>
                Pickup zones (x:y; ...)
                <textarea value={form.pickupZones} onChange={(event) => update("pickupZones", event.target.value)} rows={2} />
              </label>
              <label>
                Drop-off zones (x:y; ...)
                <textarea value={form.dropoffZones} onChange={(event) => update("dropoffZones", event.target.value)} rows={2} />
              </label>
            </div>
            <div className="wizard-grid">
              <label>
                Obstacles (x:y or ranges like 10:2-10:12)
                <textarea value={form.obstacles} onChange={(event) => update("obstacles", event.target.value)} rows={2} />
              </label>
              <label>
                Charging bays (x:y; ...)
                <textarea value={form.chargingZones} onChange={(event) => update("chargingZones", event.target.value)} rows={2} />
              </label>
            </div>
          </section>
        )}

        {step === "Operations" && (
          <section className="wizard-section">
            <h3>Fleet & Operational Rhythm</h3>
            <div className="wizard-grid">
              <label>
                Robots in fleet
                <input type="number" min={1} value={form.totalRobots} onChange={(event) => update("totalRobots", Number(event.target.value))} required />
              </label>
              <label>
                Starting positions (x:y; ...)
                <textarea value={form.startingPositions} onChange={(event) => update("startingPositions", event.target.value)} rows={2} />
              </label>
              <label>
                Speed (cells/tick)
                <input type="number" min={0.2} step={0.1} value={form.speedCellsPerTick} onChange={(event) => update("speedCellsPerTick", Number(event.target.value))} />
              </label>
              <label>
                Battery capacity (min)
                <input type="number" min={30} value={form.batteryMinutes} onChange={(event) => update("batteryMinutes", Number(event.target.value))} />
              </label>
            </div>
            <div className="wizard-grid">
              <label>
                Packages per hour
                <input type="number" min={1} value={form.packagesPerHour} onChange={(event) => update("packagesPerHour", Number(event.target.value))} />
              </label>
              <label>
                Standard priority weight
                <input type="number" min={0} max={1} step={0.05} value={form.priorityStandard} onChange={(event) => update("priorityStandard", Number(event.target.value))} />
              </label>
              <label>
                Express priority weight
                <input type="number" min={0} max={1} step={0.05} value={form.priorityExpress} onChange={(event) => update("priorityExpress", Number(event.target.value))} />
              </label>
              <label>
                SLA standard (minutes)
                <input type="number" min={5} value={form.slaStandard} onChange={(event) => update("slaStandard", Number(event.target.value))} />
              </label>
              <label>
                SLA express (minutes)
                <input type="number" min={2} value={form.slaExpress} onChange={(event) => update("slaExpress", Number(event.target.value))} />
              </label>
            </div>
            <div className="wizard-grid">
              <label>
                Tick cadence (ms)
                <input type="number" min={100} value={form.cadenceMs} onChange={(event) => update("cadenceMs", Number(event.target.value))} />
              </label>
              <label>
                Warmup (minutes)
                <input type="number" min={0} value={form.warmupMinutes} onChange={(event) => update("warmupMinutes", Number(event.target.value))} />
              </label>
              <label>
                Shift duration (minutes)
                <input type="number" min={10} value={form.shiftMinutes} onChange={(event) => update("shiftMinutes", Number(event.target.value))} />
              </label>
              <label>
                Time scale (replay speed)
                <input type="number" min={1} step={0.5} value={form.timeScale} onChange={(event) => update("timeScale", Number(event.target.value))} />
              </label>
            </div>
            <div className="wizard-grid">
              <label>
                Fault probability (per hour)
                <input type="number" min={0} max={1} step={0.01} value={form.faultProbability} onChange={(event) => update("faultProbability", Number(event.target.value))} />
              </label>
              <label>
                Mean recovery (minutes)
                <input type="number" min={1} value={form.meanRecovery} onChange={(event) => update("meanRecovery", Number(event.target.value))} />
              </label>
              <label>
                Reservation horizon
                <input type="number" min={1} value={form.reservationHorizon} onChange={(event) => update("reservationHorizon", Number(event.target.value))} />
              </label>
              <label>
                Assignment policy
                <input value={form.assignmentPolicy} onChange={(event) => update("assignmentPolicy", event.target.value)} />
              </label>
              <label>
                Planner strategy
                <input value={form.planner} onChange={(event) => update("planner", event.target.value)} />
              </label>
            </div>
            <div className="wizard-grid">
              <label>
                Horizon (minutes)
                <input type="number" min={5} value={form.horizonMinutes} onChange={(event) => update("horizonMinutes", Number(event.target.value))} />
              </label>
              <label className="checkbox">
                <input type="checkbox" checked={form.stopOnCompletion} onChange={(event) => update("stopOnCompletion", event.target.checked)} />
                Stop when queue is empty
              </label>
              <label>
                Metadata notes
                <input value={form.metadataNotes} onChange={(event) => update("metadataNotes", event.target.value)} />
              </label>
            </div>
          </section>
        )}

        {step === "Review" && (
          <section className="wizard-section review">
            <h3>Review & Confirm</h3>
            <div className="review-grid">
              <div>
                <h4>Scenario summary</h4>
                <p><strong>Name:</strong> {form.name}</p>
                <p><strong>Description:</strong> {form.description}</p>
                <p><strong>Layout:</strong> {form.width}×{form.height} @ {form.cellSize}px</p>
                <p><strong>Pickup zones:</strong> {form.pickupZones}</p>
                <p><strong>Drop-off zones:</strong> {form.dropoffZones}</p>
                <p><strong>Obstacles:</strong> {form.obstacles || "(none)"}</p>
              </div>
              <div>
                <h4>Fleet & demand</h4>
                <p><strong>Robots:</strong> {form.totalRobots}</p>
                <p><strong>Packages/hour:</strong> {form.packagesPerHour}</p>
                <p><strong>Priority mix:</strong> Standard {priorityMix.standard}, Express {priorityMix.express}</p>
                <p><strong>SLAs:</strong> Standard {form.slaStandard}m, Express {form.slaExpress}m</p>
                <p><strong>Failures:</strong> {(form.faultProbability * 100).toFixed(1)}% per hour</p>
              </div>
              <div>
                <h4>Runtime controls</h4>
                <p><strong>Cadence:</strong> {form.cadenceMs} ms</p>
                <p><strong>Warmup:</strong> {form.warmupMinutes} minutes</p>
                <p><strong>Horizon:</strong> {form.horizonMinutes} minutes</p>
                <p><strong>Stop on completion:</strong> {form.stopOnCompletion ? "Yes" : "No"}</p>
                <p><strong>Notes:</strong> {form.metadataNotes || "(none)"}</p>
              </div>
            </div>
          </section>
        )}

        {error ? <p className="wizard-error" role="alert">{error}</p> : null}
      </div>

      <footer className="wizard-actions">
        <div className="left">
          <button type="button" className="ghost" onClick={onCancel}>Cancel</button>
        </div>
        <div className="right">
          {step !== "Layout" ? (
            <button type="button" className="ghost" onClick={prevStep}>
              Back
            </button>
          ) : null}
          {step !== "Review" ? (
            <button type="button" onClick={nextStep}>
              Continue
            </button>
          ) : (
            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Creating..." : "Create scenario"}
            </button>
          )}
        </div>
      </footer>
    </form>
  );
}
