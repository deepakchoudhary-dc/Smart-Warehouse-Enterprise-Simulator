import { useEffect, useMemo, useRef } from "react";

import type {
  Layout,
  SimulationPackage,
  RobotTelemetry,
  Reservation,
  GridPosition,
} from "../types";

const ROBOT_COLORS = ["#2563eb", "#dc2626", "#16a34a", "#f97316", "#8b5cf6", "#0ea5e9", "#d97706"];

const HEATMAP_COLORS = [
  { stop: 0, color: "rgba(30, 64, 175, 0)" },
  { stop: 0.2, color: "rgba(30, 64, 175, 0.35)" },
  { stop: 0.4, color: "rgba(37, 99, 235, 0.45)" },
  { stop: 0.6, color: "rgba(59, 130, 246, 0.55)" },
  { stop: 0.8, color: "rgba(239, 68, 68, 0.65)" },
  { stop: 1, color: "rgba(220, 38, 38, 0.78)" },
];

function hashString(value: string): number {
  let hash = 0;
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash << 5) - hash + value.charCodeAt(i);
    hash |= 0; // Convert to 32bit integer
  }
  return hash;
}

function robotColor(robotId: string): string {
  const index = Math.abs(hashString(robotId)) % ROBOT_COLORS.length;
  return ROBOT_COLORS[index];
}

function drawGrid(ctx: CanvasRenderingContext2D, layout: Layout): void {
  const { width, height, cell_size: size } = layout;
  ctx.fillStyle = "#0f172a";
  ctx.fillRect(0, 0, width * size, height * size);

  ctx.strokeStyle = "rgba(148, 163, 184, 0.18)";
  ctx.lineWidth = 1;

  for (let x = 0; x <= width; x += 1) {
    ctx.beginPath();
    ctx.moveTo(x * size + 0.5, 0);
    ctx.lineTo(x * size + 0.5, height * size);
    ctx.stroke();
  }

  for (let y = 0; y <= height; y += 1) {
    ctx.beginPath();
    ctx.moveTo(0, y * size + 0.5);
    ctx.lineTo(width * size, y * size + 0.5);
    ctx.stroke();
  }
}

function drawCells(ctx: CanvasRenderingContext2D, positions: GridPosition[], size: number, color: string): void {
  ctx.fillStyle = color;
  positions.forEach((pos) => {
    ctx.fillRect(pos.x * size, pos.y * size, size, size);
  });
}

function drawChargingZones(ctx: CanvasRenderingContext2D, positions: GridPosition[] | undefined, size: number): void {
  if (!positions || positions.length === 0) {
    return;
  }
  ctx.strokeStyle = "rgba(248, 250, 252, 0.75)";
  ctx.lineWidth = Math.max(2, size * 0.08);
  positions.forEach((pos) => {
    ctx.strokeRect(pos.x * size + size * 0.12, pos.y * size + size * 0.12, size * 0.76, size * 0.76);
  });
}

function drawHeatmap(
  ctx: CanvasRenderingContext2D,
  heatmap: Record<string, number> | undefined,
  size: number,
): void {
  if (!heatmap) {
    return;
  }
  const entries = Object.entries(heatmap);
  if (entries.length === 0) {
    return;
  }
  const maxCount = Math.max(...entries.map(([, value]) => value));
  if (maxCount <= 0) {
    return;
  }
  entries.forEach(([key, count]) => {
    const [xRaw, yRaw] = key.split(":");
    const x = Number.parseInt(xRaw, 10);
    const y = Number.parseInt(yRaw, 10);
    if (Number.isNaN(x) || Number.isNaN(y)) {
      return;
    }
    const intensity = Math.min(count / maxCount, 1);
    const gradient = ctx.createLinearGradient(x * size, y * size, (x + 1) * size, (y + 1) * size);
    HEATMAP_COLORS.forEach((stop) => {
      gradient.addColorStop(stop.stop, stop.color);
    });
    ctx.globalAlpha = intensity;
    ctx.fillStyle = gradient;
    ctx.fillRect(x * size, y * size, size, size);
  });
  ctx.globalAlpha = 1;
}

function drawReservations(
  ctx: CanvasRenderingContext2D,
  reservations: Reservation[],
  size: number,
): void {
  ctx.fillStyle = "rgba(59, 130, 246, 0.25)";
  reservations.forEach((reservation) => {
    ctx.fillRect(reservation.position.x * size, reservation.position.y * size, size, size);
  });
}

function drawPackages(ctx: CanvasRenderingContext2D, packages: SimulationPackage[], size: number): void {
  packages.forEach((pkg) => {
    const x = pkg.position.x * size + size * 0.1;
    const y = pkg.position.y * size + size * 0.1;
    const boxSize = size * 0.8;
    ctx.fillStyle = pkg.status === "delivered" ? "#16a34a" : "#f97316";
    ctx.fillRect(x, y, boxSize, boxSize);

    ctx.fillStyle = "#0f172a";
    ctx.font = `${Math.max(12, size * 0.35)}px Inter, sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(pkg.id.slice(-3).toUpperCase(), x + boxSize / 2, y + boxSize / 2);
  });
}

function drawRobotPath(ctx: CanvasRenderingContext2D, robot: RobotTelemetry, size: number, color: string): void {
  if (!robot.path.length) {
    return;
  }

  ctx.strokeStyle = `${color}80`;
  ctx.lineWidth = Math.max(2, size * 0.1);
  ctx.beginPath();
  const startX = robot.position.x * size + size / 2;
  const startY = robot.position.y * size + size / 2;
  ctx.moveTo(startX, startY);
  robot.path.forEach((step) => {
    ctx.lineTo(step.x * size + size / 2, step.y * size + size / 2);
  });
  ctx.stroke();
}

function drawRobots(ctx: CanvasRenderingContext2D, robots: RobotTelemetry[], size: number): void {
  robots.forEach((robot) => {
    const color = robotColor(robot.robot_id);
    drawRobotPath(ctx, robot, size, color);

    const centerX = robot.position.x * size + size / 2;
    const centerY = robot.position.y * size + size / 2;
    const radius = size * 0.35;

    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "#0f172a";
    ctx.font = `${Math.max(12, size * 0.4)}px Inter, sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(robot.robot_id.replace("AGV-", ""), centerX, centerY);
  });
}

interface WarehouseCanvasProps {
  layout: Layout | null;
  packages: SimulationPackage[];
  robots: RobotTelemetry[];
  reservations: Reservation[];
  heatmap?: Record<string, number>;
  showHeatmap?: boolean;
}

export function WarehouseCanvas({ layout, packages, robots, reservations, heatmap, showHeatmap = true }: WarehouseCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const surface = useMemo(() => {
    if (!layout) {
      return { width: 0, height: 0 };
    }
    const width = layout.width * layout.cell_size;
    const height = layout.height * layout.cell_size;
    return { width, height };
  }, [layout]);

  useEffect(() => {
    if (!layout) {
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    canvas.width = surface.width;
    canvas.height = surface.height;
    canvas.style.width = "100%";
    canvas.style.height = "auto";

    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }

    drawGrid(ctx, layout);
    drawCells(ctx, layout.obstacles, layout.cell_size, "#334155");
    drawCells(ctx, layout.pickup_zones, layout.cell_size, "rgba(34, 197, 94, 0.35)");
    drawCells(ctx, layout.dropoff_zones, layout.cell_size, "rgba(139, 92, 246, 0.35)");
    drawChargingZones(ctx, layout.charging_zones, layout.cell_size);
    if (showHeatmap) {
      drawHeatmap(ctx, heatmap, layout.cell_size);
    }
    drawReservations(ctx, reservations, layout.cell_size);
    drawPackages(ctx, packages, layout.cell_size);
    drawRobots(ctx, robots, layout.cell_size);
  }, [heatmap, layout, packages, robots, reservations, showHeatmap, surface.height, surface.width]);

  if (!layout) {
    return (
      <div className="canvas-empty">Connect to the simulation to see live activity.</div>
    );
  }

  return (
    <div className="canvas-wrapper">
      <canvas ref={canvasRef} aria-label="Warehouse simulation canvas" />
      <div className="canvas-legend">
        <div className="legend-item"><span className="legend-swatch pickup" />Pickup zone</div>
        <div className="legend-item"><span className="legend-swatch dropoff" />Drop-off zone</div>
        <div className="legend-item"><span className="legend-swatch reservation" />Reserved</div>
        <div className="legend-item"><span className="legend-swatch package" />Package</div>
    <div className="legend-item"><span className="legend-swatch robot" />Robot</div>
    <div className="legend-item">Charging bay</div>
    {showHeatmap ? <div className="legend-item">Heatmap intensity</div> : null}
      </div>
    </div>
  );
}
