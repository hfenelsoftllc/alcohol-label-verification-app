import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <section
      aria-labelledby="nf-heading"
      className="mx-auto mt-8 max-w-lg rounded-2xl border border-slate-200/70 bg-white p-10 text-center shadow-card"
    >
      <p className="font-display text-5xl font-semibold text-treasury-700">404</p>
      <h1 id="nf-heading" className="mt-2 font-display text-2xl font-semibold text-ink">
        Page not found
      </h1>
      <p className="mt-2 text-muted">The page you’re looking for doesn’t exist.</p>
      <Link
        to="/"
        className="mt-6 inline-flex items-center rounded-lg bg-treasury-700 px-5 py-2.5 font-semibold text-white shadow-sm transition-colors hover:bg-treasury-800"
      >
        Back to start
      </Link>
    </section>
  );
}
