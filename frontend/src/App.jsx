import { Routes, Route, Link, useLocation } from 'react-router-dom';
import Dashboard from './pages/Dashboard.jsx';
import Projector from './pages/Projector.jsx';
import StudentView from './pages/StudentView.jsx';

/**
 * Root application component.
 * Provides top-level routing for the three views:
 *   /           → Dashboard  (instructor control panel)
 *   /projector  → Projector  (fullscreen projector display)
 *   /student    → StudentView (student-facing mobile view)
 */
export default function App() {
  const { pathname } = useLocation();

  // Projector and student views are fullscreen — hide the nav bar
  const showNav = pathname === '/';

  return (
    <div className="min-h-screen bg-surface-900 text-white font-sans">
      {showNav && (
        <nav className="bg-surface-800 border-b border-surface-700 px-6 py-3 flex items-center gap-6">
          <span className="text-accent-blue font-bold text-lg tracking-tight">
            🎓 AI Lecturer
          </span>
          <Link
            to="/"
            className="text-sm text-slate-300 hover:text-white transition-colors"
          >
            Dashboard
          </Link>
          <Link
            to="/projector"
            className="text-sm text-slate-300 hover:text-white transition-colors"
          >
            Projector
          </Link>
          <Link
            to="/student"
            className="text-sm text-slate-300 hover:text-white transition-colors"
          >
            Student View
          </Link>
        </nav>
      )}

      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/projector" element={<Projector />} />
        <Route path="/student" element={<StudentView />} />
      </Routes>
    </div>
  );
}
