import { Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import EventDetail from "./pages/EventDetail";
import Home from "./pages/Home";
import Subscribe from "./pages/Subscribe";

export default function App() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/evenements/:id" element={<EventDetail />} />
        <Route path="/alertes" element={<Subscribe />} />
      </Routes>
      <footer className="mt-16 border-t border-ink/10 dark:border-cream/10 py-8 text-center text-xs text-ink/50 dark:text-cream/50">
        <p>
          Données : OpenAgenda · Que Faire à Paris ? · data.culture.gouv.fr · sites officiels des musées
        </p>
        <p className="mt-2 text-[11px]">
          &copy; {new Date().getFullYear()} Site proposé par Tino Nguyen
        </p>
      </footer>
    </div>
  );
}
