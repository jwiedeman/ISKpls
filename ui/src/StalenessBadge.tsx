export default function StalenessBadge({ ms }: { ms: number }) {
  let label = 'Stale';
  let color: string = 'red';
  if (ms < 5 * 60 * 1000) {
    label = 'Fresh';
    color = 'green';
  } else if (ms < 30 * 60 * 1000) {
    label = 'Warm';
    color = 'orange';
  }
  return <span style={{ color }}>{label}</span>;
}
