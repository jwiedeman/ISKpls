import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAuthStatus, connectAuth, AuthStatus } from '../api';

export default function Login() {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  async function refresh() {
    try {
      const data = await getAuthStatus();
      setStatus(data);
      if (data.has_token) {
        navigate('/');
      }
    } catch (e: unknown) {
      if (e instanceof Error) {
        setError(e.message);
      } else {
        setError(String(e));
      }
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function connect() {
    try {
      await connectAuth();
      await refresh();
    } catch (e: unknown) {
      if (e instanceof Error) {
        setError(e.message);
      } else {
        setError(String(e));
      }
    }
  }

  return (
    <div>
      <h2>Connect EVE Account</h2>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {!status?.has_token && (
        <button onClick={connect}>Connect</button>
      )}
      {status?.has_token && <p>Connected. Redirecting...</p>}
    </div>
  );
}
