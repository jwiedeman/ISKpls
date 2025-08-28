import type { RunwayEvent, PendingJob } from "./useEventStream";

export function useRunwayVM(events: RunwayEvent[]) {
  const inflight: Record<string, RunwayEvent> = {};
  const builds: Record<string, RunwayEvent> = {};
  let esi = { remain: null as number | null, reset: null as number | null };
  let queue: Record<string, number> = { P0: 0, P1: 0, P2: 0, P3: 0 };
  let pending: PendingJob[] = [];
  const logs: RunwayEvent[] = [];

  for (const e of events) {
    if (e.type === "job_started" && e.runId)
      inflight[e.runId] = { ...e, progress: 0 };
    if (e.type === "job_progress" && e.runId && inflight[e.runId]) {
      inflight[e.runId].progress = e.progress ?? 0;
      inflight[e.runId].detail = e.detail;
    }
    if (e.job && e.phase && e.runId && inflight[e.runId]) {
      if (e.phase === "start") {
        inflight[e.runId] = { ...inflight[e.runId], ...e };
      } else if (e.phase === "progress") {
        inflight[e.runId].done = e.done;
        inflight[e.runId].total = e.total;
        inflight[e.runId].detail = e.detail;
      } else if (e.phase === "finish") {
        inflight[e.runId] = { ...inflight[e.runId], ...e, finished: true };
      }
    }
    if (e.type === "job_log") logs.push(e);
    if (e.type === "job_finished" && e.runId && inflight[e.runId])
      inflight[e.runId] = { ...inflight[e.runId], ...e, finished: true };
    if (e.type === "build_started" && e.buildId)
      builds[e.buildId] = { ...e, progress: 0 };
    if (e.type === "build_progress" && e.buildId && builds[e.buildId]) {
      builds[e.buildId].progress = e.progress ?? 0;
      builds[e.buildId].stage = e.stage;
      builds[e.buildId].detail = e.detail;
    }
    if (e.type === "build_finished" && e.buildId && builds[e.buildId])
      builds[e.buildId] = { ...builds[e.buildId], ...e, finished: true };
    if (e.type === "esi") esi = { remain: e.remain ?? null, reset: e.reset ?? null };
    if (e.type === "queue") queue = e.depth ?? queue;
    if (e.type === "jobs") pending = (e.pending as PendingJob[]) ?? pending;
  }
  const inflightList = Object.values(inflight).filter((x) => !x.finished);
  const recentJobs = Object.values(inflight)
    .filter((x) => x.finished)
    .slice(-10)
    .reverse();
  const buildInflight = Object.values(builds).filter((b) => !b.finished);
  const recentBuilds = Object.values(builds)
    .filter((x) => x.finished)
    .slice(-5)
    .reverse();
  return {
    inflightList,
    buildInflight,
    recentJobs,
    recentBuilds,
    pending,
    esi,
    queue,
    logs,
  };
}
