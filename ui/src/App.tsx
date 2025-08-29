import { Link, Routes, Route, useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';
import Recommendations from './pages/Recommendations';
import Orders from './pages/Orders';
import Portfolio from './pages/Portfolio';
import Snipes from './pages/Snipes';
import Login from './pages/Login';
import Db from './pages/Db';
import { getAuthStatus } from './api';
import './App.css';

export default function App() {
  const navigate = useNavigate();
  useEffect(() => {
    getAuthStatus().then(s => {
      if (!s.has_token) navigate('/login');
    }).catch(() => navigate('/login'));
  }, [navigate]);

  return (
    <>
      <nav>
        <Link to="/">Dashboard</Link> |
        <Link to="/db">DB</Link> |
        <Link to="/recommendations">Recommendations</Link> |
        <Link to="/portfolio">Portfolio</Link> |
        <Link to="/snipes">Snipes</Link> |
        <Link to="/orders">Orders</Link> |
        <Link to="/settings">Settings</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/db" element={<Db />} />
        <Route path="/recommendations" element={<Recommendations />} />
        <Route path="/portfolio" element={<Portfolio />} />
        <Route path="/snipes" element={<Snipes />} />
        <Route path="/orders" element={<Orders />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/login" element={<Login />} />
      </Routes>
    </>
  );
}
