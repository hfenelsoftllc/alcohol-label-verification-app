import { useEffect, useState } from 'react';

import { ApiError, jobExportUrl, submitBatch } from '../api/client.js';
import Spinner from '../components/Spinner.jsx';
import StatusBadge from '../components/StatusBadge.jsx';
import { LABEL_FIELD_NAMES } from '../constants/labelFields.js';
import useJobStream from '../hooks/useJobStream.js';
import { extractImagesFromZip } from '../utils/zipImages.js';
import { validateApplicationCsv } from '../utils/validateApplicationCsv.js';

const ACCEPTED_ZIP_TYPES = '.zip,application/zip,application/x-zip-compressed';
const ACCEPTED_CSV_TYPES = '.csv,text/csv';

function LayersIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="M12 3l9 5-9 5-9-5 9-5z" strokeLinejoin="round" />
      <path d="M3 12l9 5 9-5M3 16l9 5 9-5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function TableIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M3 10h18M9 4v16" strokeLinecap="round" />
    </svg>
  );
}

// A drag-and-drop / click-to-browse target for a single file.
function Dropzone({ id, accept, isDragging, setIsDragging, onFile, children }) {
  return (
    <label
      htmlFor={id}
      onDrop={(event) => {
        event.preventDefault();
        setIsDragging(false);
        onFile(event.dataTransfer.files?.[0]);
      }}
      onDragOver={(event) => {
        event.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      className={`block cursor-pointer rounded-xl border-2 border-dashed p-12 text-center transition-colors ${
        isDragging
          ? 'border-treasury-400 bg-treasury-50'
          : 'border-treasury-200 bg-treasury-50/40 hover:border-treasury-400 hover:bg-treasury-50'
      }`}
    >
      <input
        id={id}
        type="file"
        accept={accept}
        className="sr-only"
        onChange={(event) => onFile(event.target.files?.[0])}
      />
      {children}
    </label>
  );
}

function SummaryStat({ label, value, className }) {
  return (
    <div className="rounded-xl border border-slate-200/70 bg-treasury-50/40 p-4 text-center">
      <p className={`font-display text-3xl font-semibold ${className}`}>{value}</p>
      <p className="mt-1 text-xs font-semibold uppercase tracking-wider text-muted">{label}</p>
    </div>
  );
}

function emptyForm() {
  return {
    zipFile: null,
    images: [],
    zipError: null,
    extracting: false,
    csvFile: null,
    csvErrors: [],
    validatingCsv: false,
  };
}

// Upload form (ZIP of label images + application CSV) shown before a batch
// is submitted.
function BatchUploadForm({ form, onZipFile, onCsvFile, onSubmit, submitting, submitError }) {
  const [isDraggingZip, setIsDraggingZip] = useState(false);
  const [isDraggingCsv, setIsDraggingCsv] = useState(false);

  const canSubmit =
    form.zipFile !== null &&
    form.csvFile !== null &&
    form.images.length > 0 &&
    form.zipError === null &&
    form.csvErrors.length === 0 &&
    !form.extracting &&
    !form.validatingCsv &&
    !submitting;

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
      className="space-y-6"
      noValidate
    >
      <div className="overflow-hidden rounded-2xl border border-slate-200/70 bg-white shadow-card">
        <div className="h-1 bg-gradient-to-r from-treasury-700 via-gold-400 to-treasury-700" />
        <div className="space-y-6 p-8">
          <div>
            <h2 className="font-display text-xl font-semibold text-ink">Label images</h2>
            <p className="mt-1 text-sm text-muted">
              A ZIP archive containing one image per label (JPG, PNG, GIF, BMP, TIFF, or WEBP).
            </p>
          </div>
          <Dropzone
            id="batch-zip"
            accept={ACCEPTED_ZIP_TYPES}
            isDragging={isDraggingZip}
            setIsDragging={setIsDraggingZip}
            onFile={onZipFile}
          >
            {form.zipFile ? (
              <div className="space-y-1">
                <p className="font-medium text-ink">{form.zipFile.name}</p>
                {form.extracting ? (
                  <Spinner label="Reading ZIP archive…" />
                ) : (
                  <p className="text-sm text-muted">
                    {form.images.length} image{form.images.length === 1 ? '' : 's'} found
                  </p>
                )}
                <p className="text-sm font-medium text-treasury-600 underline">Choose a different ZIP</p>
              </div>
            ) : (
              <>
                <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-treasury-700 text-white shadow-sm">
                  <LayersIcon />
                </span>
                <p className="mt-4 text-lg font-semibold text-ink">Drag and drop a ZIP of label images</p>
                <p className="mt-1 text-sm text-muted">or click to browse</p>
              </>
            )}
          </Dropzone>
          {form.zipError && (
            <p role="alert" className="text-sm font-medium text-danger">
              {form.zipError}
            </p>
          )}
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200/70 bg-white shadow-card">
        <div className="h-1 bg-gradient-to-r from-treasury-700 via-gold-400 to-treasury-700" />
        <div className="space-y-6 p-8">
          <div>
            <h2 className="font-display text-xl font-semibold text-ink">Application data</h2>
            <p className="mt-1 text-sm text-muted">
              A CSV with one row per image, in the same order, with columns:{' '}
              <code className="rounded bg-treasury-50 px-1 py-0.5 font-mono text-xs text-treasury-700 ring-1 ring-treasury-200">
                {LABEL_FIELD_NAMES.join(', ')}
              </code>
            </p>
          </div>
          <Dropzone
            id="batch-csv"
            accept={ACCEPTED_CSV_TYPES}
            isDragging={isDraggingCsv}
            setIsDragging={setIsDraggingCsv}
            onFile={onCsvFile}
          >
            {form.csvFile ? (
              <div className="space-y-1">
                <p className="font-medium text-ink">{form.csvFile.name}</p>
                {form.validatingCsv ? (
                  <Spinner label="Checking CSV columns…" />
                ) : (
                  <p className="text-sm font-medium text-treasury-600 underline">Choose a different CSV</p>
                )}
              </div>
            ) : (
              <>
                <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-treasury-700 text-white shadow-sm">
                  <TableIcon />
                </span>
                <p className="mt-4 text-lg font-semibold text-ink">Drag and drop the application CSV</p>
                <p className="mt-1 text-sm text-muted">or click to browse</p>
              </>
            )}
          </Dropzone>
          {form.csvErrors.length > 0 && (
            <div role="alert" className="rounded-xl border border-danger/30 bg-danger/5 p-4 text-sm font-medium text-danger">
              <p className="font-semibold">Fix the application CSV before uploading:</p>
              <ul className="mt-1 list-inside list-disc space-y-1">
                {form.csvErrors.map((error) => (
                  <li key={error}>{error}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {submitError && (
        <div role="alert" className="rounded-xl border border-danger/30 bg-danger/5 p-4 text-sm font-medium text-danger">
          {submitError}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-4">
        <button
          type="submit"
          disabled={!canSubmit}
          className="inline-flex items-center rounded-lg bg-treasury-700 px-6 py-3 font-semibold text-white shadow-sm transition-colors hover:bg-treasury-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting ? 'Starting…' : 'Start verification'}
        </button>
        {submitting && <Spinner label="Submitting batch…" />}
      </div>
    </form>
  );
}

// Live progress, results feed, and completion summary for a submitted batch.
function BatchProgressView({ jobId, totalImages, stream, onRestart }) {
  const { completed, total, recentResults, summary, done, reconnecting } = stream;
  const effectiveTotal = total || totalImages;
  const pct = effectiveTotal > 0 ? Math.round((completed / effectiveTotal) * 100) : 0;

  return (
    <div className="space-y-6">
      <div className="overflow-hidden rounded-2xl border border-slate-200/70 bg-white shadow-card">
        <div className="h-1 bg-gradient-to-r from-treasury-700 via-gold-400 to-treasury-700" />
        <div className="space-y-4 p-8">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-display text-lg font-semibold text-ink">
              {done ? 'Batch complete' : 'Processing batch…'}
            </h2>
            <span className="text-sm font-semibold text-treasury-700">
              {completed} of {effectiveTotal} complete
            </span>
          </div>
          <div
            role="progressbar"
            aria-label="Batch progress"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
            className="h-3 w-full overflow-hidden rounded-full bg-slate-200"
          >
            <div className="h-3 rounded-full bg-treasury-600 transition-[width]" style={{ width: `${pct}%` }} />
          </div>
          {reconnecting && (
            <p role="status" aria-live="polite" className="text-sm font-medium text-warning">
              Reconnecting…
            </p>
          )}
          {!done && <Spinner label="Verifying labels — this can take a while for large batches…" />}
        </div>
      </div>

      {recentResults.length > 0 && (
        <div className="overflow-hidden rounded-2xl border border-slate-200/70 bg-white shadow-card">
          <div className="h-1 bg-gradient-to-r from-treasury-700 via-gold-400 to-treasury-700" />
          <div className="p-8">
            <h2 className="font-display text-lg font-semibold text-ink">Recently completed</h2>
            <ul className="mt-4 divide-y divide-slate-200/70">
              {recentResults.map((result) => (
                <li key={result.session_id} className="flex items-center justify-between gap-4 py-3">
                  <span className="truncate font-medium text-ink">{result.filename || result.session_id}</span>
                  <StatusBadge status={result.overall_status} />
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {done && summary && (
        <div className="overflow-hidden rounded-2xl border border-slate-200/70 bg-white shadow-card">
          <div className="h-1 bg-gradient-to-r from-treasury-700 via-gold-400 to-treasury-700" />
          <div className="p-8">
            <h2 className="font-display text-lg font-semibold text-ink">Summary</h2>
            <dl className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
              <SummaryStat label="Match" value={summary.match} className="text-success" />
              <SummaryStat label="Partial" value={summary.partial} className="text-warning" />
              <SummaryStat label="Fail" value={summary.fail} className="text-danger" />
              <SummaryStat label="Error" value={summary.error} className="text-danger" />
            </dl>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-4">
        {done && (
          <a
            href={jobExportUrl(jobId)}
            download
            className="inline-flex items-center rounded-lg bg-treasury-700 px-5 py-2.5 font-semibold text-white shadow-sm transition-colors hover:bg-treasury-800"
          >
            Download Full Report
          </a>
        )}
        <button
          type="button"
          onClick={onRestart}
          className="inline-flex items-center rounded-lg border border-treasury-200 bg-white px-5 py-2.5 font-semibold text-treasury-700 shadow-sm transition-colors hover:bg-treasury-50"
        >
          Restart
        </button>
      </div>
    </div>
  );
}

// Batch page (route: /batch). Upload a ZIP of label images plus an
// application CSV, validate the CSV client-side, submit for processing, and
// track live progress via SSE (ISSUE 3.4, FedRAMP SI-10).
export default function BatchPage() {
  const [form, setForm] = useState(emptyForm);
  const [jobId, setJobId] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  const stream = useJobStream(jobId);

  // Re-validate the CSV whenever it or the extracted image count changes, so
  // column-mapping and row-count errors surface before the upload starts.
  useEffect(() => {
    if (!form.csvFile) return undefined;
    let cancelled = false;
    setForm((prev) => ({ ...prev, validatingCsv: true }));
    validateApplicationCsv(form.csvFile, form.images.length).then((errors) => {
      if (!cancelled) setForm((prev) => ({ ...prev, csvErrors: errors, validatingCsv: false }));
    });
    return () => {
      cancelled = true;
    };
  }, [form.csvFile, form.images]);

  async function handleZipFile(file) {
    if (!file) return;
    setForm((prev) => ({ ...prev, zipFile: file, zipError: null, images: [], extracting: true }));
    try {
      const images = await extractImagesFromZip(file);
      setForm((prev) => ({
        ...prev,
        images,
        extracting: false,
        zipError:
          images.length === 0 ? 'No image files (JPG, PNG, GIF, BMP, TIFF, or WEBP) were found in that ZIP.' : null,
      }));
    } catch {
      setForm((prev) => ({ ...prev, images: [], extracting: false, zipError: 'Could not read that file as a ZIP archive.' }));
    }
  }

  function handleCsvFile(file) {
    if (!file) return;
    setForm((prev) => ({ ...prev, csvFile: file, csvErrors: [] }));
  }

  async function handleSubmit() {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const response = await submitBatch(form.images, form.csvFile);
      setJobId(response.job_id);
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : 'Could not start the batch. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  function handleRestart() {
    setForm(emptyForm());
    setJobId(null);
    setSubmitting(false);
    setSubmitError(null);
  }

  return (
    <section aria-labelledby="batch-heading" className="space-y-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-treasury-600">Bulk processing</p>
        <h1 id="batch-heading" className="mt-1 font-display text-3xl font-semibold text-ink">
          Verify a batch of labels
        </h1>
        <p className="mt-3 max-w-2xl text-muted">
          Process 200–300 labels at once and track progress in real time as each result completes.
        </p>
      </div>

      {jobId === null ? (
        <BatchUploadForm
          form={form}
          onZipFile={handleZipFile}
          onCsvFile={handleCsvFile}
          onSubmit={handleSubmit}
          submitting={submitting}
          submitError={submitError}
        />
      ) : (
        <BatchProgressView jobId={jobId} totalImages={form.images.length} stream={stream} onRestart={handleRestart} />
      )}
    </section>
  );
}
