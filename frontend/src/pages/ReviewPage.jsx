import { Link, useLocation } from 'react-router-dom';

import ConfidenceBar from '../components/ConfidenceBar.jsx';
import StatusBadge from '../components/StatusBadge.jsx';
import { COMPARISON_FIELDS, GOVERNMENT_WARNING_LABEL } from '../constants/labelFields.js';
import { buildResultCsv, downloadCsv } from '../utils/exportResultCsv.js';

// Below this image quality score, the reviewer is warned the result may be
// unreliable.
const LOW_QUALITY_THRESHOLD = 40;

const OVERALL_SUMMARY = {
  MATCH: 'Every field matches the application data.',
  PARTIAL: 'Some fields are a partial match — review the highlighted fields below.',
  FAIL: 'One or more fields do not match the application data.',
  ERROR: 'The label could not be processed.',
};

function NotDetected() {
  return <span className="italic text-muted">Not detected</span>;
}

// Review page (route: /results/:sessionId). Renders the VerificationResult
// passed from UploadPage via route state (ISSUE 3.3) — there is no backend
// endpoint to re-fetch a single-label result by session id.
export default function ReviewPage() {
  const location = useLocation();
  const result = location.state?.result;

  if (!result) {
    return (
      <section
        aria-labelledby="review-heading"
        className="mx-auto mt-8 max-w-lg rounded-2xl border border-slate-200/70 bg-white p-10 text-center shadow-card"
      >
        <h1 id="review-heading" className="font-display text-2xl font-semibold text-ink">
          No result to show
        </h1>
        <p className="mt-2 text-muted">
          Results aren&rsquo;t saved between visits. Verify a label to see its results here.
        </p>
        <Link
          to="/"
          className="mt-6 inline-flex items-center rounded-lg bg-treasury-700 px-5 py-2.5 font-semibold text-white shadow-sm transition-colors hover:bg-treasury-800"
        >
          Verify a label
        </Link>
      </section>
    );
  }

  const fieldByKey = new Map(result.fields.map((field) => [field.field, field]));
  const lowQuality = result.image_quality_score < LOW_QUALITY_THRESHOLD;

  return (
    <section aria-labelledby="review-heading" className="space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-treasury-600">Results</p>
        <h1 id="review-heading" className="mt-1 font-display text-3xl font-semibold text-ink">
          Verification results
        </h1>
        <p className="mt-2 text-muted">
          Session{' '}
          <code className="rounded bg-treasury-50 px-1.5 py-0.5 font-mono text-treasury-700 ring-1 ring-treasury-200">
            {result.session_id}
          </code>
          {result.filename && <> · {result.filename}</>}
        </p>
      </div>

      {lowQuality && (
        <div role="alert" className="flex items-start gap-3 rounded-xl border border-warning/30 bg-warning/5 p-4">
          <span aria-hidden="true" className="text-xl leading-none">
            ⚠️
          </span>
          <div>
            <p className="font-semibold text-warning">Image quality may affect accuracy</p>
            <p className="mt-1 text-sm text-muted">
              Quality score {Math.round(result.image_quality_score)}/100
              {result.quality_issues.length > 0 && ` — ${result.quality_issues.join(', ')}`}. Consider
              retaking the photo with better lighting and focus.
            </p>
          </div>
        </div>
      )}

      <div className="overflow-hidden rounded-2xl border border-slate-200/70 bg-white shadow-card">
        <div className="h-1 bg-gradient-to-r from-treasury-700 via-gold-400 to-treasury-700" />
        <div className="flex flex-wrap items-center justify-between gap-4 p-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted">Overall result</p>
            <p className="mt-2 text-lg font-semibold text-ink">
              {OVERALL_SUMMARY[result.overall_status] ?? OVERALL_SUMMARY.ERROR}
            </p>
            {result.message && <p className="mt-2 text-sm text-muted">{result.message}</p>}
          </div>
          <StatusBadge status={result.overall_status} />
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200/70 bg-white shadow-card">
        <div className="h-1 bg-gradient-to-r from-treasury-700 via-gold-400 to-treasury-700" />
        <div className="divide-y divide-slate-200/70">
          {COMPARISON_FIELDS.map(({ key, label }) => {
            const field = fieldByKey.get(key);
            if (!field) return null;
            return (
              <div key={key} className="p-6">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h2 className="font-display text-lg font-semibold text-ink">{label}</h2>
                  <StatusBadge status={field.status} />
                </div>
                <div className="mt-3 grid gap-4 sm:grid-cols-2">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-muted">Label says</p>
                    <p className="mt-1 text-ink">{field.extracted ?? <NotDetected />}</p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-muted">Application says</p>
                    <p className="mt-1 text-ink">{field.expected ?? <NotDetected />}</p>
                  </div>
                </div>
                <div className="mt-4 max-w-sm">
                  <ConfidenceBar score={field.score} label={`${label} confidence`} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200/70 bg-white shadow-card">
        <div className="h-1 bg-gradient-to-r from-treasury-700 via-gold-400 to-treasury-700" />
        <div className="p-8">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-display text-lg font-semibold text-ink">{GOVERNMENT_WARNING_LABEL}</h2>
            <StatusBadge status={result.government_warning.valid ? 'MATCH' : 'NO_MATCH'} />
          </div>
          <div className="mt-3 grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted">Label says</p>
              <p className="mt-1 whitespace-pre-wrap text-sm text-ink">
                {result.government_warning.extracted_text ?? <NotDetected />}
              </p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted">Application says</p>
              <p className="mt-1 whitespace-pre-wrap text-sm text-ink">
                {result.government_warning.expected_text ?? <NotDetected />}
              </p>
            </div>
          </div>
          {result.government_warning.issues.length > 0 && (
            <ul className="mt-4 list-inside list-disc space-y-1 text-sm text-danger">
              {result.government_warning.issues.map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <button
          type="button"
          onClick={() => downloadCsv(`verification-${result.session_id}.csv`, buildResultCsv(result))}
          className="inline-flex items-center rounded-lg border border-treasury-200 bg-white px-5 py-2.5 font-semibold text-treasury-700 shadow-sm transition-colors hover:bg-treasury-50"
        >
          Export CSV
        </button>
        <Link
          to="/"
          className="inline-flex items-center rounded-lg bg-treasury-700 px-5 py-2.5 font-semibold text-white shadow-sm transition-colors hover:bg-treasury-800"
        >
          Verify another label
        </Link>
      </div>
    </section>
  );
}
