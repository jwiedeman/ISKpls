import { Link, Routes, Route } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';
import Recommendations from './pages/Recommendations';
import Orders from './pages/Orders';
import './App.css';

export default function App() {
  return (
    <>
      <nav>
        <Link to="/">Dashboard</Link> |
        <Link to="/recommendations">Recommendations</Link> |
        <Link to="/orders">Orders</Link> |
        <Link to="/settings">Settings</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/recommendations" element={<Recommendations />} />
        <Route path="/orders" element={<Orders />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </>
  );
}
