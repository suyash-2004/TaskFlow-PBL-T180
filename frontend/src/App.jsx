import { Routes, Route } from 'react-router-dom';

// Layouts
import MainLayout from './components/layouts/MainLayout';

// Pages
import Dashboard from './pages/Dashboard';
import Calendar from './pages/Calendar';
import Tasks from './pages/Tasks';
import Reports from './pages/Reports';
import Scheduler from './pages/Scheduler';
import NotFound from './pages/NotFound';

function App() {
  return (
    <Routes>
      {/* All routes are public now */}
      <Route path="/" element={<MainLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="calendar" element={<Calendar />} />
        <Route path="tasks" element={<Tasks />} />
        <Route path="reports" element={<Reports />} />
        <Route path="scheduler/generate" element={<Scheduler />} />
      </Route>
      
      {/* Not found route */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

export default App; 