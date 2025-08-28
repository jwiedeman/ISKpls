import React from "react";
import { useEventStream } from "../useEventStream";

function useRunwayVM(events: any[]) {
  const inflight: Record<string, any> = {};
  const builds: Record<string, any> = {};
  let esi = { remain: null, reset: null } as any;
  let queue = { P0: 0, P1: 0, P2: 0, P3: 0 };
  const logs: any[] = [];

  for (const e of events) {
    if (e.type === "job_started") inflight[e.runId] = { ...e, progress: 0 };
    if (e.type === "job_progress" && inflight[e.runId])
      (inflight[e.runId].progress = e.progress,
      (inflight[e.runId].detail = e.detail));
    if (e.type === "job_log") logs.push(e);
    if (e.type === "job_finished")
      inflight[e.runId] = { ...inflight[e.runId], ...e, done: true };
    if (e.type === "build_started") builds[e.buildId] = { ...e, progress: 0 };
    if (e.type === "build_progress" && builds[e.buildId])
      (builds[e.buildId].progress = e.progress,
      (builds[e.buildId].stage = e.stage),
      (builds[e.buildId].detail = e.detail));
    if (e.type === "build_finished")
      builds[e.buildId] = { ...builds[e.buildId], ...e, done: true };
    if (e.type === "esi") esi = { remain: e.remain, reset: e.reset };
    if (e.type === "queue") queue = e.depth;
  }
  const inflightList = Object.values(inflight).filter((x: any) => !x.done);
  const recentJobs = Object.values(inflight)
    .filter((x: any) => x.done)
    .slice(-10)
    .reverse();
  const recentBuilds = Object.values(builds)
    .filter((x: any) => x.done)
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
        {inflightList.map((j: any) => (
          <li key={j.runId} title={j.detail}>
            <strong>{j.job}</strong> {j.progress}% {trunc(j.detail)}
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
        {recentBuilds.map((b: any) => (
          <li key={b.buildId} title={b.detail}>
            <strong>{b.job}</strong> {b.progress}% {b.stage} {trunc(b.detail)}
          </li>
        ))}
      </ul>
      <h3>Logs</h3>
      <ul>
        {logs.slice(-50).map((l: any, i: number) => (
          <li key={i} title={l.message}>
            {l.level}: {trunc(l.message)}
          </li>
        ))}
      </ul>
    </div>
  );
}
