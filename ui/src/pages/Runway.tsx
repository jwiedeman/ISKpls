import React from "react";
import { useEventStream } from "../useEventStream";
import type { RunwayEvent } from "../useEventStream";

interface EsiInfo {
  remain: number | null;
  reset: number | null;
}

function useRunwayVM(events: RunwayEvent[]) {
  const inflight: Record<string, RunwayEvent> = {};
  const builds: Record<string, RunwayEvent> = {};
  let esi: EsiInfo = { remain: null, reset: null };
  let queue: Record<string, number> = { P0: 0, P1: 0, P2: 0, P3: 0 };
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
  return { inflightList, recentJobs, recentBuilds, esi, queue, logs };
}

export default function Runway() {
  const { connected, events } = useEventStream();
  const { inflightList, recentBuilds, esi, queue, logs } = useRunwayVM(events);
  const dotStyle: React.CSSProperties = {
    width: 10,
    height: 10,
    borderRadius: "50%",
    backgroundColor: connected ? "green" : "red",
    display: "inline-block",
    marginRight: 8,
  };
  const trunc = (s: string) => (s && s.length > 80 ? s.slice(0, 80) + "…" : s);

  return (
    <div>
      <h2>Runway</h2>
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <span style={dotStyle}></span>
        <span>
          ESI remain: {esi.remain ?? ""} reset: {esi.reset ?? ""}
        </span>
      </div>
      <h3>Now Running</h3>
      <ul>
        {inflightList.length === 0 && <li>None</li>}
        {inflightList.map((j) => (
          <li key={j.runId} title={j.detail}>
            <strong>{j.job}</strong> {j.progress}% {trunc(j.detail ?? "")}
          </li>
        ))}
      </ul>
      <h3>Queue</h3>
      <div>
        {Object.entries(queue).map(([k, v]) => (
          <span
            key={k}
            style={{
              marginRight: "8px",
              padding: "2px 4px",
              border: "1px solid #ccc",
              borderRadius: "4px",
            }}
          >
            {k}:{String(v)}
          </span>
        ))}
      </div>
      <h3>Recent Builds</h3>
      <ul>
          {recentBuilds.map((b) => (
            <li key={b.buildId} title={b.detail}>
              <strong>{b.job}</strong> {b.progress}% {b.stage} {trunc(b.detail ?? "")}
            </li>
          ))}
      </ul>
      <h3>Logs</h3>
      <ul>
        {logs.slice(-50).map((l, i) => (
          <li key={i} title={l.message}>
            {l.level}: {trunc(l.message ?? "")}
          </li>
        ))}
      </ul>
    </div>
  );
}
