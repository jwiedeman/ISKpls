import { useEffect, useRef, useState } from "react";
import { getStatus } from "./api";
import type { StatusSnapshot } from "./api";

export interface PendingJob {
  job: string;
  runId: string;
  queued_at: string;
}

export interface RunwayEvent {
  type: string;
  runId?: string;
  buildId?: string;
  job?: string;
  progress?: number;
  meta?: Record<string, unknown>;
  phase?: string;
  detail?: string;
  level?: string;
  message?: string;
  stage?: string;
  ok?: boolean;
  itemsWritten?: number;
  items_written?: number;
  unique_types_touched?: number;
  median_snapshot_age_ms?: number;
  errors?: number;
  tiers?: Record<string, number>;
  selected?: number;
  workers?: number;
  expected_pages?: number;
  done?: number;
  total?: number;
  rows?: number;
  ms?: number;
  error?: string;
  remain?: number;
  reset?: number;
  depth?: Record<string, number>;
  pending?: PendingJob[];
  finished?: boolean;
  polled?: boolean;
}

export function useEventStream() {
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<RunwayEvent[]>(() => {
    try {
      const cached = sessionStorage.getItem("runway_events");
      return cached ? (JSON.parse(cached) as RunwayEvent[]) : [];
    } catch {
      return [];
    }
  });
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
      function stash(evts: RunwayEvent[]) {
        try {
          sessionStorage.setItem("runway_events", JSON.stringify(evts.slice(-200)));
        } catch {
          /* ignore */
        }
      }

    const ws = new WebSocket(
      `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`
    );
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    ws.onmessage = (e) => {
      const evt = JSON.parse(e.data) as RunwayEvent;
      setEvents((prev) => {
        const next = [...prev.slice(-199), evt];
        stash(next);
        return next;
      });
    };
    const ping = setInterval(() => ws && ws.readyState === 1 && ws.send("ping"), 10000);
    return () => {
      clearInterval(ping);
      if (ws) ws.close();
    };
  }, []);

  // Fallback polling when disconnected -------------------------------------------------
  useEffect(() => {
    let poll: ReturnType<typeof setInterval> | undefined;
    async function refresh() {
      try {
        const snap: StatusSnapshot = await getStatus();
        setEvents((prev) => {
          const logs = (snap.logs ?? []).map((l) => ({ ...l, polled: true }));
          const evtList = [...prev, ...logs];
          return evtList.slice(-200);
        });
      } catch {
        /* ignore */
      }
    }
    if (!connected) {
      refresh();
      poll = setInterval(refresh, 2000);
    }
    return () => {
      if (poll) clearInterval(poll);
    };
  }, [connected]);

  return { connected, events };
}
