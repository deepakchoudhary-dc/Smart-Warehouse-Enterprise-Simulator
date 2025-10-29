import { Route, Routes } from "react-router-dom";

import { AnalyticsDashboard } from "./pages/AnalyticsDashboard";
import { OperationsDashboard } from "./pages/OperationsDashboard";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<OperationsDashboard />} />
      <Route path="/analytics" element={<AnalyticsDashboard />} />
    </Routes>
  );
}
