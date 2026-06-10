// Decorative emblem — a classical treasury-building facade (pediment + columns).
// Original line-art, not the official Treasury seal. Inherits color via
// `currentColor`; set a text color on the parent (e.g. text-gold-400).
export default function Emblem({ className = 'h-9 w-9' }) {
  return (
    <svg
      viewBox="0 0 48 48"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {/* Pediment */}
      <path d="M7 17 L24 7 L41 17 Z" />
      {/* Architrave */}
      <path d="M9 21 H39" />
      {/* Columns */}
      <path d="M13 21 V35 M20 21 V35 M28 21 V35 M35 21 V35" />
      {/* Stylobate / steps */}
      <path d="M9 35 H39 M6 39 H42" />
    </svg>
  );
}
