import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import AboutPage from "./pages/AboutPage";
import DemosPage from "./pages/DemosPage";
import HomePage from "./pages/HomePage";
import RunPage from "./pages/RunPage";

// Backend verdicts are displayed only. No page computes or changes a
// verdict (see AGENTS.md hard rules).
export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/runs/:runId" element={<RunPage />} />
        <Route path="/demos" element={<DemosPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route
          path="*"
          element={
            <div className="flex flex-col gap-2">
              <h1 className="text-xl font-semibold">Page not found.</h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                The page you asked for does not exist.
              </p>
            </div>
          }
        />
      </Routes>
    </Layout>
  );
}
