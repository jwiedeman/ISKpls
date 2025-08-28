import React from "react";
import { useEventStream } from "../useEventStream";
import RunwayPanel from "../RunwayPanel";

export default function Runway() {
  const { connected, events } = useEventStream();
  return (
    <div>
      <h2>Runway</h2>
      <RunwayPanel connected={connected} events={events} />
    </div>
  );
}
