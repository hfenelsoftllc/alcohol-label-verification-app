const CHECKED_FIELDS = [
  'Brand Name',
  'Class / Type',
  'Alcohol Content',
  'Net Contents',
  'Name & Address',
  'Country of Origin',
  'Government Warning',
];

function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="M12 16V4m0 0L7 9m5-5l5 5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// Upload page (route: /). The full workflow — drag-and-drop, application fields,
// side-by-side results — is built in ISSUE 3.3. This is the shell it slots into.
export default function UploadPage() {
  return (
    <section aria-labelledby="upload-heading" className="space-y-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-treasury-600">
          Single label
        </p>
        <h1 id="upload-heading" className="mt-1 font-display text-3xl font-semibold text-ink">
          Verify a label against its application
        </h1>
        <p className="mt-3 max-w-2xl text-muted">
          Upload a label image and its COLA application data. The system reads the label,
          compares every required field, and flags any discrepancy — in seconds.
        </p>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200/70 bg-white shadow-card">
        <div className="h-1 bg-gradient-to-r from-treasury-700 via-gold-400 to-treasury-700" />
        <div className="p-8">
          <div className="group rounded-xl border-2 border-dashed border-treasury-200 bg-treasury-50/40 p-12 text-center transition-colors hover:border-treasury-400 hover:bg-treasury-50">
            <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-treasury-700 text-white shadow-sm">
              <UploadIcon />
            </span>
            <p className="mt-4 text-lg font-semibold text-ink">Drag and drop a label image</p>
            <p className="mt-1 text-sm text-muted">
              or click to browse — JPG, PNG, or PDF, up to 20&nbsp;MB
            </p>
            <p className="mt-4 text-xs font-medium uppercase tracking-wider text-treasury-500">
              Interactive upload arrives in ISSUE 3.3
            </p>
          </div>
        </div>
      </div>

      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted">What we check</h2>
        <ul className="mt-3 flex flex-wrap gap-2">
          {CHECKED_FIELDS.map((field) => (
            <li
              key={field}
              className="rounded-full border border-treasury-200 bg-white px-3 py-1 text-sm font-medium text-treasury-700"
            >
              {field}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
