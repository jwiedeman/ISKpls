import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAuthStatus, connectAuth, type AuthStatus } from '../api';
import Spinner from '../Spinner';
import ErrorBanner from '../ErrorBanner';

export default function Login() {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function refresh() {
    setLoading(true);
    try {
      const data = await getAuthStatus();
      setStatus(data);
      if (data.has_token) {
        navigate('/');
      }
      setError('');
    } catch (e: unknown) {
      if (e instanceof Error) {
        setError(e.message);
      } else {
        setError(String(e));
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function connect() {
    setLoading(true);
    try {
      await connectAuth();
      await refresh();
    } catch (e: unknown) {
      if (e instanceof Error) {
        setError(e.message);
      } else {
        setError(String(e));
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h2>Connect EVE Account</h2>
      <ErrorBanner message={error} />
      {loading && <Spinner />}
      {!status?.has_token && (
        <button onClick={connect} disabled={loading}>Connect</button>
      )}
      {status?.has_token && <p>Connected. Redirecting...</p>}
    </div>
  );
}
