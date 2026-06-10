import { NavLink, Outlet } from 'react-router-dom';

import BackendStatus from './BackendStatus.jsx';

const navItems = [
  { to: '/', label: 'Single Label', end: true },
  { to: '/batch', label: 'Batch', end: false },
];

function navClass({ isActive }) {
  return [
    'rounded-md px-3 py-2 text-sm font-medium',
    isActive ? 'bg-brand-700 text-white' : 'text-ink hover:bg-brand-50',
  ].join(' ');
}

export default function Layout() {
  return (
    <div className="min-h-screen">
      {/* Keyboard skip link (ISSUE 4.3). */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-brand-700 focus:px-4 focus:py-2 focus:text-white"
      >
        Skip to main content
      </a>

      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-3">
            <span className="text-lg font-bold text-brand-700">Label Verification</span>
            <nav aria-label="Primary" className="flex gap-1">
              {navItems.map((item) => (
                <NavLink key={item.to} to={item.to} end={item.end} className={navClass}>
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>
          <BackendStatus />
        </div>
      </header>

      <main id="main-content" className="mx-auto max-w-5xl px-4 py-8">
        <Outlet />
      </main>

      <footer className="mx-auto max-w-5xl px-4 py-6 text-sm text-muted">
        TTB COLA Automation — Proof of Concept
      </footer>
    </div>
  );
}
