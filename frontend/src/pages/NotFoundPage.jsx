import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <section aria-labelledby="nf-heading" className="text-center">
      <h1 id="nf-heading" className="text-2xl font-bold text-ink">
        Page not found
      </h1>
      <p className="mt-2 text-muted">The page you’re looking for doesn’t exist.</p>
      <Link
        to="/"
        className="mt-6 inline-block rounded-md bg-brand-700 px-5 py-2.5 font-semibold text-white hover:bg-brand-800"
      >
        Back to start
      </Link>
    </section>
  );
}
