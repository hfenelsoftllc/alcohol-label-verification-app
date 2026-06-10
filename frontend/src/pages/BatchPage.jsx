function LayersIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="M12 3l9 5-9 5-9-5 9-5z" strokeLinejoin="round" />
      <path d="M3 12l9 5 9-5M3 16l9 5 9-5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const STEPS = [
  { n: '1', t: 'Upload', d: 'A ZIP of label images and a CSV of application data.' },
  { n: '2', t: 'Process', d: 'Up to 300 labels verified in parallel, ≤5s each.' },
  { n: '3', t: 'Review', d: 'A summary of matches, partials, and failures to export.' },
];

// Batch page (route: /batch). The full bulk workflow — live progress, summary —
// is built in ISSUE 3.4.
export default function BatchPage() {
  return (
    <section aria-labelledby="batch-heading" className="space-y-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-treasury-600">
          Bulk processing
        </p>
        <h1 id="batch-heading" className="mt-1 font-display text-3xl font-semibold text-ink">
          Verify a batch of labels
        </h1>
        <p className="mt-3 max-w-2xl text-muted">
          Process 200–300 labels at once and track progress in real time as each result
          completes.
        </p>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200/70 bg-white shadow-card">
        <div className="h-1 bg-gradient-to-r from-treasury-700 via-gold-400 to-treasury-700" />
        <div className="p-8">
          <div className="rounded-xl border-2 border-dashed border-treasury-200 bg-treasury-50/40 p-12 text-center transition-colors hover:border-treasury-400 hover:bg-treasury-50">
            <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-treasury-700 text-white shadow-sm">
              <LayersIcon />
            </span>
            <p className="mt-4 text-lg font-semibold text-ink">Upload a ZIP of images and a CSV</p>
            <p className="mt-1 text-sm text-muted">one CSV row of application data per image</p>
            <p className="mt-4 text-xs font-medium uppercase tracking-wider text-treasury-500">
              Live progress UI arrives in ISSUE 3.4
            </p>
          </div>
        </div>
      </div>

      <ol className="grid gap-4 sm:grid-cols-3">
        {STEPS.map((s) => (
          <li key={s.n} className="rounded-xl border border-slate-200/70 bg-white p-5 shadow-card">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-treasury-50 font-display text-base font-semibold text-treasury-700 ring-1 ring-treasury-200">
              {s.n}
            </span>
            <p className="mt-3 font-semibold text-ink">{s.t}</p>
            <p className="mt-1 text-sm text-muted">{s.d}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
