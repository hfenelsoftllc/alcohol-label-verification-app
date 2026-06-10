import { NavLink, Outlet } from 'react-router-dom';

import BackendStatus from './BackendStatus.jsx';
import Emblem from './Emblem.jsx';

const navItems = [
  { to: '/', label: 'Single Label', end: true },
  { to: '/batch', label: 'Batch', end: false },
];

function navClass({ isActive }) {
  return [
    'on-dark relative rounded-md px-3 py-2 text-sm font-medium transition-colors',
    isActive
      ? 'text-white after:absolute after:inset-x-3 after:-bottom-px after:h-0.5 after:rounded-full after:bg-gold-400'
      : 'text-treasury-100 hover:text-white hover:bg-white/10',
  ].join(' ');
}

export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      {/* Keyboard skip link (ISSUE 4.3). */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-gold-400 focus:px-4 focus:py-2 focus:font-semibold focus:text-treasury-950"
      >
        Skip to main content
      </a>

      <header className="bg-gradient-to-b from-treasury-900 to-treasury-800 text-white shadow-[0_8px_24px_-16px_rgb(7_42_32_/_0.8)]">
        {/* Gold ribbon */}
        <div className="h-1 bg-gradient-to-r from-gold-600 via-gold-400 to-gold-600" />
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-4 py-4">
          <div className="flex items-center gap-3">
            <span className="text-gold-400">
              <Emblem className="h-10 w-10" />
            </span>
            <div className="leading-tight">
              <p className="text-[0.65rem] font-semibold uppercase tracking-[0.18em] text-gold-300">
                U.S. Department of the Treasury · TTB
              </p>
              <p className="font-display text-xl font-semibold text-white">Label Verification</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <nav aria-label="Primary" className="flex gap-1">
              {navItems.map((item) => (
                <NavLink key={item.to} to={item.to} end={item.end} className={navClass}>
                  {item.label}
                </NavLink>
              ))}
            </nav>
            <BackendStatus />
          </div>
        </div>
      </header>

      <main id="main-content" className="mx-auto w-full max-w-5xl flex-1 px-4 py-10">
        <Outlet />
      </main>

      <footer className="border-t-2 border-gold-400/60 bg-treasury-900 text-treasury-100">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-2 px-4 py-5 text-sm">
          <span className="flex items-center gap-2">
            <span className="text-gold-400">
              <Emblem className="h-5 w-5" />
            </span>
            TTB COLA Automation — Proof of Concept
          </span>
          <span className="text-treasury-200">In-memory processing · no data retained</span>
        </div>
      </footer>
    </div>
  );
}
