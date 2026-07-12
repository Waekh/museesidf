import { Link, NavLink } from "react-router-dom";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-2 text-sm font-medium transition-colors ${
    isActive ? "text-ocre" : "text-ink/70 dark:text-cream/70 hover:text-ocre"
  }`;

export default function Navbar() {
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
        </div>
      </nav>
    </header>
  );
}
