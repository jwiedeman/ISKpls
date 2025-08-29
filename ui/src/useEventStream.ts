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

    let retry = 0;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let active = true;

    // Establish the WebSocket connection with exponential backoff reconnects.
    function connect() {
      const ws = new WebSocket(
        `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`
      );
      wsRef.current = ws;
      ws.onopen = () => {
        retry = 0;
        setConnected(true);
      };
      ws.onclose = () => {
        setConnected(false);
        if (!active) return;
        const delay = Math.min(1000 * 2 ** retry, 10000);
        retry += 1;
        reconnectTimer = setTimeout(connect, delay);
      };
      ws.onerror = () => {
        setConnected(false);
        ws.close();
      };
      ws.onmessage = (e) => {
        const evt = JSON.parse(e.data) as RunwayEvent;
        setEvents((prev) => {
          const next = [...prev.slice(-199), evt];
          stash(next);
          return next;
        });
      };
    }

    connect();
    const ping = setInterval(
      () => wsRef.current && wsRef.current.readyState === 1 && wsRef.current.send("ping"),
      10000
    );
    return () => {
      active = false;
      clearInterval(ping);
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (wsRef.current) wsRef.current.close();
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
