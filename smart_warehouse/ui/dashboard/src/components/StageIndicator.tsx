import type { RunStage } from "../types";

const STAGE_COPY: Record<RunStage, string> = {
  QUEUED: "Queued",
  WARMING_UP: "Warming up",
  RUNNING: "Live",
  COMPLETED: "Completed",
  FAILED: "Failed",
  CANCELLED: "Cancelled",
};

export function StageIndicator({ stage }: { stage: RunStage }) {
  return <span className={`stage-indicator stage-${stage.toLowerCase()}`}>{STAGE_COPY[stage]}</span>;
}
