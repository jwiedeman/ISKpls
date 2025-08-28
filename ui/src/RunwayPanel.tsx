import React from "react";
import type { RunwayEvent } from "./useEventStream";
import { useRunwayVM } from "./runwayVM";

interface Props {
  connected: boolean;
  events: RunwayEvent[];
}

export default function RunwayPanel({ connected, events }: Props) {
  const {
    inflightList,
    buildInflight,
    recentJobs,
    recentBuilds,
    pending,
    esi,
    queue,
    logs,
  } = useRunwayVM(events);
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
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <span style={dotStyle}></span>
        <span>
          ESI remain: {esi.remain ?? ""} reset: {esi.reset ?? ""}
        </span>
      </div>
      <h3>Now Running</h3>
      <ul>
        {inflightList.length === 0 && buildInflight.length === 0 && <li>None</li>}
        {inflightList.map((j) => (
          <li key={j.runId} title={j.detail}>
            <strong>{j.job}</strong> {j.progress}%
            {typeof j.done === "number" &&
            typeof (j.total ?? j.meta?.total) === "number" ? (
              <> {j.done}/{j.total ?? j.meta?.total}</>
            ) : null}{" "}
            {trunc(j.detail ?? "")}
          </li>
        ))}
        {buildInflight.map((b) => (
          <li key={b.buildId} title={b.detail}>
            <strong>{b.job}</strong> {b.progress}% {b.stage} {trunc(b.detail ?? "")}
          </li>
        ))}
      </ul>
      <h3>Pending Queue</h3>
      <ul>
        {pending.length === 0 && <li>None</li>}
        {pending.map((p) => (
          <li key={p.runId}>
            {p.job} queued {p.queued_at}
          </li>
        ))}
      </ul>
      <h3>Queue Depth</h3>
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
      <h3>Recent Jobs</h3>
      <ul>
        {recentJobs.map((j) => (
          <li key={j.runId} title={j.detail}>
            <strong>{j.job}</strong> {j.ok ? "ok" : "fail"} {j.ms}ms {trunc(j.detail ?? "")}
          </li>
        ))}
      </ul>
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
