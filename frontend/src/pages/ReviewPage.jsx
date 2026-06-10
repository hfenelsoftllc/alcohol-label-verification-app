import { useParams } from 'react-router-dom';

// Review page (route: /results/:sessionId). The side-by-side comparison view is
// built in ISSUE 3.3; here we establish the route and read the session id.
export default function ReviewPage() {
  const { sessionId } = useParams();

  return (
    <section aria-labelledby="review-heading" className="space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-treasury-600">
          Results
        </p>
        <h1 id="review-heading" className="mt-1 font-display text-3xl font-semibold text-ink">
          Verification results
        </h1>
        <p className="mt-2 text-muted">
          Session{' '}
          <code className="rounded bg-treasury-50 px-1.5 py-0.5 font-mono text-treasury-700 ring-1 ring-treasury-200">
            {sessionId}
          </code>
        </p>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200/70 bg-white shadow-card">
        <div className="h-1 bg-gradient-to-r from-treasury-700 via-gold-400 to-treasury-700" />
        <div className="grid gap-px bg-slate-200/70 sm:grid-cols-2">
          {['Label Says', 'Application Says'].map((title) => (
            <div key={title} className="bg-white p-8">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-muted">{title}</h2>
              <p className="mt-3 text-muted">
                Field-by-field comparison renders here — built in ISSUE&nbsp;3.3.
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
