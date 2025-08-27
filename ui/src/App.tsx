import { Link, Routes, Route } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';
import './App.css';

export default function App() {
  return (
    <>
      <nav>
        <Link to="/">Dashboard</Link> | <Link to="/settings">Settings</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </>
  );
}
