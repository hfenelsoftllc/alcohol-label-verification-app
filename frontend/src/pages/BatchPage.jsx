// Batch page (route: /batch). The full bulk workflow — ZIP + CSV upload, live
// progress, summary — is built in ISSUE 3.4.
export default function BatchPage() {
  return (
    <section aria-labelledby="batch-heading">
      <h1 id="batch-heading" className="text-2xl font-bold text-ink">
        Batch verification
      </h1>
      <p className="mt-2 max-w-2xl text-muted">
        Upload up to 300 labels at once and track progress as they are processed.
      </p>

      <div className="mt-6 rounded-lg border-2 border-dashed border-slate-300 bg-white p-10 text-center">
        <p className="font-medium text-ink">Upload a ZIP of images and a CSV of application data</p>
        <p className="mt-1 text-sm text-muted">live progress UI — built in ISSUE 3.4</p>
      </div>
    </section>
  );
}
