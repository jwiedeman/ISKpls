import { useTypeName } from './TypeNamesContext';

interface Props {
  id: number;
  name?: string;
}

export default function TypeName({ id, name }: Props) {
  const ctxName = useTypeName(id);
  const display = name || ctxName || String(id);
  const copy = () => {
    try {
      void navigator.clipboard.writeText(String(id));
    } catch {
      // ignore clipboard errors
    }
  };
  return (
    <span>
      {display} · #{id}{' '}
      <button onClick={copy} title="Copy type ID" style={{ border: 'none', background: 'none', cursor: 'pointer' }}>
        📋
      </button>
    </span>
  );
}
