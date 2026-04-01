import { Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Processing from "./pages/Processing";
import Minutes from "./pages/Minutes";
import Speakers from "./pages/Speakers";
import Docs from "./pages/Docs";

export default function App() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto bg-background">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/processing/:jobId" element={<Processing />} />
          <Route path="/minutes/:jobId" element={<Minutes />} />
          <Route path="/speakers" element={<Speakers />} />
          <Route path="/docs" element={<Docs />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
