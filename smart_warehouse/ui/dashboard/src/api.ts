import axios from "axios";

import type {
  AnalyticsScenarioSummary,
  RunTick,
  ScenarioConfig,
  ScenarioRun,
  ScenarioRunDetail,
  ScenarioSummary,
  TimelineEventDetail,
} from "./types";

const rawBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api";
const apiBaseUrl = rawBaseUrl.endsWith("/") ? rawBaseUrl.slice(0, -1) : rawBaseUrl;

export const apiClient = axios.create({
  baseURL: apiBaseUrl,
  timeout: 15000,
});

function resolveApiUrl(path: string): string {
  const base = apiBaseUrl || "/api";
  if (base.startsWith("http://") || base.startsWith("https://")) {
    return `${base}${path}`;
  }
  const origin = window.location.origin.replace(/\/$/, "");
  const prefix = base.startsWith("/") ? base : `/${base}`;
  return `${origin}${prefix}${path}`;
}

function resolveWsUrl(path: string): string {
  const url = new URL(resolveApiUrl(path));
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

export function describeApiBase(): string {
  return resolveApiUrl("");
}

export async function fetchScenarios(): Promise<ScenarioSummary[]> {
  const response = await apiClient.get<ScenarioSummary[]>("/v1/scenarios/");
  return response.data;
}

export async function createScenario(config: ScenarioConfig): Promise<ScenarioSummary> {
  const response = await apiClient.post<ScenarioSummary>("/v1/scenarios/", config);
  return response.data;
}

export async function launchScenario(scenarioId: string): Promise<ScenarioRun> {
  const response = await apiClient.post<ScenarioRun>(`/v1/scenarios/${scenarioId}/launch`);
  return response.data;
}

export async function fetchScenarioRuns(): Promise<ScenarioRun[]> {
  const response = await apiClient.get<ScenarioRun[]>("/v1/scenarios/runs");
  return response.data;
}

export async function fetchRunDetail(runId: string): Promise<ScenarioRunDetail> {
  const response = await apiClient.get<ScenarioRunDetail>(`/v1/scenarios/runs/${runId}`);
  return response.data;
}

export async function fetchRunTimeline(runId: string): Promise<TimelineEventDetail[]> {
  const response = await apiClient.get<TimelineEventDetail[]>(`/v1/scenarios/runs/${runId}/timeline`);
  return response.data;
}

export async function cancelRun(runId: string): Promise<void> {
  await apiClient.post(`/v1/scenarios/runs/${runId}/cancel`);
}

export function subscribeToRun(
  runId: string,
  onMessage: (tick: RunTick) => void,
  onError?: (err: Event) => void,
  onClose?: (event: CloseEvent) => void,
): WebSocket {
  const socket = new WebSocket(resolveWsUrl(`/v1/scenarios/runs/${runId}/stream`));
  socket.onmessage = (event: MessageEvent<string>) => {
    try {
      const data = JSON.parse(event.data) as RunTick;
      onMessage(data);
    } catch (err) {
      console.error("Failed to parse run tick", err);
    }
  };
  if (onError) {
    socket.onerror = onError;
  }
  socket.onclose = (event: CloseEvent) => {
    onClose?.(event);
  };
  return socket;
}

export async function fetchAnalyticsScenarios(): Promise<AnalyticsScenarioSummary[]> {
  const response = await apiClient.get<AnalyticsScenarioSummary[]>("/v1/analytics/scenarios");
  return response.data;
}

export { resolveApiUrl, resolveWsUrl };
