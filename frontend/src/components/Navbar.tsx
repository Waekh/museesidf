import { useEffect, useState } from "react";
import { Link, NavLink } from "react-router-dom";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-2 text-sm font-medium transition-colors ${isActive ? "text-ocre" : "text-ink/70 dark:text-cream/70 hover:text-ocre"
  }`;

export default function Navbar() {
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") || "light");

  useEffect(() => {
    const root = window.document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = () => setTheme((prev) => (prev === "dark" ? "light" : "dark"));

  return (
    <header className="border-b border-ink/10 dark:border-cream/10 bg-cream/90 dark:bg-ink/90 backdrop-blur sticky top-0 z-[1000]">
      <nav className="mx-auto max-w-6xl px-4 h-16 flex items-center justify-between">
        <Link to="/" className="font-display text-2xl font-bold">
          Musées <span className="text-ocre">IDF</span>
        </Link>
        <div className="flex items-center gap-2">
          <NavLink to="/" className={linkClass} end>
            Événements
          </NavLink>
          <NavLink to="/alertes" className={linkClass}>
            Alertes email
          </NavLink>

          <button
            onClick={toggleTheme}
            className="p-2 ml-4 text-ink dark:text-cream hover:text-ocre dark:hover:text-ocre transition-colors"
            title="Basculer le thème"
          >
            {theme === "dark" ? (
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="4" />
                <path d="M12 2v2" /><path d="M12 20v2" /><path d="m4.93 4.93 1.41 1.41" /><path d="m17.66 17.66 1.41 1.41" /><path d="M2 12h2" /><path d="M20 12h2" /><path d="m6.34 17.66-1.41 1.41" /><path d="m19.07 4.93-1.41 1.41" />
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
              </svg>
            )}
          </button>
        </div>
      </nav>
    </header>
  );
}
