import { useEffect, useRef, useState } from "react";
import { API_BASE, getStatus } from "./api";

export function useEventStream() {
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<any[]>(() => {
    try {
      const cached = sessionStorage.getItem("runway_events");
      return cached ? JSON.parse(cached) : [];
    } catch {
      return [];
    }
  });
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    function stash(evts: any[]) {
      try {
        sessionStorage.setItem("runway_events", JSON.stringify(evts.slice(-200)));
      } catch {}
    }

    let ws: WebSocket | null = new WebSocket(
      `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`
    );
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    ws.onmessage = (e) => {
      const evt = JSON.parse(e.data);
      setEvents((prev) => {
        const next = [...prev.slice(-199), evt];
        stash(next);
        return next;
      });
    };
    const ping = setInterval(() => ws && ws.readyState === 1 && ws.send("ping"), 10000);
    return () => {
      clearInterval(ping);
      ws && ws.close();
    };
  }, []);

  // Fallback polling when disconnected -------------------------------------------------
  useEffect(() => {
    let poll: any;
    async function refresh() {
      try {
        const snap = await getStatus();
        setEvents((prev) => {
          const evtList = [...prev, ...snap.logs.map((l: any) => ({ ...l, polled: true }))];
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
    return () => poll && clearInterval(poll);
  }, [connected]);

  return { connected, events };
}
