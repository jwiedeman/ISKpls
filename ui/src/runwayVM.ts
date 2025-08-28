import type { RunwayEvent, PendingJob } from "./useEventStream";

export function useRunwayVM(events: RunwayEvent[]) {
  const inflight: Record<string, RunwayEvent> = {};
  const builds: Record<string, RunwayEvent> = {};
  let esi = { remain: null as number | null, reset: null as number | null };
  let queue: Record<string, number> = { P0: 0, P1: 0, P2: 0, P3: 0 };
  let pending: PendingJob[] = [];
  const logs: RunwayEvent[] = [];

  for (const e of events) {
    if (e.type === "job_started" && e.runId) inflight[e.runId] = { ...e, progress: 0 };
    if (e.type === "job_progress" && e.runId && inflight[e.runId]) {
      inflight[e.runId].progress = e.progress ?? 0;
      inflight[e.runId].detail = e.detail;
    }
    if (e.type === "job_log") logs.push(e);
    if (e.type === "job_finished" && e.runId && inflight[e.runId])
      inflight[e.runId] = { ...inflight[e.runId], ...e, done: true };
    if (e.type === "build_started" && e.buildId)
      builds[e.buildId] = { ...e, progress: 0 };
    if (e.type === "build_progress" && e.buildId && builds[e.buildId]) {
      builds[e.buildId].progress = e.progress ?? 0;
      builds[e.buildId].stage = e.stage;
      builds[e.buildId].detail = e.detail;
    }
    if (e.type === "build_finished" && e.buildId && builds[e.buildId])
      builds[e.buildId] = { ...builds[e.buildId], ...e, done: true };
    if (e.type === "esi") esi = { remain: e.remain ?? null, reset: e.reset ?? null };
    if (e.type === "queue") queue = e.depth ?? queue;
    if (e.type === "jobs") pending = (e.pending as PendingJob[]) ?? pending;
  }
  const inflightList = Object.values(inflight).filter((x) => !x.done);
  const recentJobs = Object.values(inflight)
    .filter((x) => x.done)
    .slice(-10)
    .reverse();
  const recentBuilds = Object.values(builds)
    .filter((x) => x.done)
    .slice(-5)
    .reverse();
  return { inflightList, recentJobs, recentBuilds, pending, esi, queue, logs };
}
