import { useParams } from 'react-router-dom';

// Review page (route: /results/:sessionId). The side-by-side comparison view is
// built in ISSUE 3.3; here we establish the route and read the session id.
export default function ReviewPage() {
  const { sessionId } = useParams();

  return (
    <section aria-labelledby="review-heading">
      <h1 id="review-heading" className="text-2xl font-bold text-ink">
        Verification results
      </h1>
      <p className="mt-2 text-muted">
        Session <code className="rounded bg-slate-100 px-1.5 py-0.5">{sessionId}</code>
      </p>

      <div className="mt-6 rounded-lg border border-slate-200 bg-white p-8">
        <p className="text-muted">
          Side-by-side “Label Says” vs “Application Says” comparison — built in ISSUE 3.3.
        </p>
      </div>
    </section>
  );
}
