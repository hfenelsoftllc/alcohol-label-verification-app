import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { ApiError, verify } from '../api/client.js';
import Spinner from '../components/Spinner.jsx';
import {
  APPLICATION_FORM_FIELDS,
  DEFAULT_GOVERNMENT_WARNING,
  FIELD_MAX_LENGTH,
  FIELD_PLACEHOLDERS,
} from '../constants/labelFields.js';

// Mirrors the MAX_IMAGE_MB default in backend/app/validation.py.
const MAX_IMAGE_BYTES = 20 * 1024 * 1024;

// Mirrors the magic-number signatures accepted by backend/app/validation.py.
const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff', 'image/webp'];

function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="M12 16V4m0 0L7 9m5-5l5 5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function emptyFormData() {
  return {
    brand: '',
    class_type: '',
    abv: '',
    net_contents: '',
    name_address: '',
    country_of_origin: '',
    government_warning: DEFAULT_GOVERNMENT_WARNING,
  };
}

// Upload page (route: /). Drag-and-drop a label image, fill in the
// application data, and submit for verification (ISSUE 3.3).
export default function UploadPage() {
  const navigate = useNavigate();
  const [image, setImage] = useState(null);
  const [formData, setFormData] = useState(emptyFormData);
  const [isDragging, setIsDragging] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  function applyFile(file) {
    if (!file) return;
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setError('Please choose a JPG, PNG, GIF, BMP, TIFF, or WEBP image.');
      return;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      setError('That image is larger than 20 MB. Please choose a smaller file.');
      return;
    }
    setError(null);
    const reader = new FileReader();
    reader.onload = () => setImage({ dataUrl: reader.result, name: file.name });
    reader.onerror = () => setError('Could not read that file. Please try again.');
    reader.readAsDataURL(file);
  }

  function handleDrop(event) {
    event.preventDefault();
    setIsDragging(false);
    applyFile(event.dataTransfer.files?.[0]);
  }

  function handleFieldChange(key, value) {
    setFormData((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!image) {
      setError('Add a label image before verifying.');
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      const result = await verify(image.dataUrl, formData);
      navigate(`/results/${result.session_id}`, { state: { result } });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Verification failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  }

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

      <form onSubmit={handleSubmit} className="space-y-6" noValidate>
        <div className="overflow-hidden rounded-2xl border border-slate-200/70 bg-white shadow-card">
          <div className="h-1 bg-gradient-to-r from-treasury-700 via-gold-400 to-treasury-700" />
          <div className="p-8">
            <label
              htmlFor="label-image"
              onDrop={handleDrop}
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
                id="label-image"
                type="file"
                accept={ACCEPTED_TYPES.join(',')}
                className="sr-only"
                onChange={(event) => applyFile(event.target.files?.[0])}
              />
              {image ? (
                <div className="space-y-3">
                  <img
                    src={image.dataUrl}
                    alt={`Preview of uploaded label image: ${image.name}`}
                    className="mx-auto max-h-48 rounded-lg border border-slate-200 object-contain shadow-sm"
                  />
                  <p className="font-medium text-ink">{image.name}</p>
                  <p className="text-sm font-medium text-treasury-600 underline">Choose a different image</p>
                </div>
              ) : (
                <>
                  <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-treasury-700 text-white shadow-sm">
                    <UploadIcon />
                  </span>
                  <p className="mt-4 text-lg font-semibold text-ink">Drag and drop a label image</p>
                  <p className="mt-1 text-sm text-muted">
                    or click to browse — JPG, PNG, GIF, BMP, TIFF, or WEBP, up to 20&nbsp;MB
                  </p>
                </>
              )}
            </label>
          </div>
        </div>

        <div className="overflow-hidden rounded-2xl border border-slate-200/70 bg-white shadow-card">
          <div className="h-1 bg-gradient-to-r from-treasury-700 via-gold-400 to-treasury-700" />
          <div className="space-y-5 p-8">
            <div>
              <h2 className="font-display text-xl font-semibold text-ink">Application data</h2>
              <p className="mt-1 text-sm text-muted">
                Enter the values exactly as they appear on the COLA application. The Government
                Warning is pre-filled with the standard text — edit it only if this application
                uses different wording.
              </p>
            </div>
            <div className="grid gap-5 sm:grid-cols-2">
              {APPLICATION_FORM_FIELDS.map((field) => (
                <div key={field.key} className={field.type === 'textarea' ? 'sm:col-span-2' : ''}>
                  <label htmlFor={`field-${field.key}`} className="block text-sm font-semibold text-ink">
                    {field.label}
                  </label>
                  {field.type === 'textarea' ? (
                    <textarea
                      id={`field-${field.key}`}
                      required
                      rows={4}
                      maxLength={FIELD_MAX_LENGTH[field.key]}
                      value={formData[field.key]}
                      onChange={(event) => handleFieldChange(field.key, event.target.value)}
                      className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-ink shadow-sm"
                    />
                  ) : (
                    <input
                      id={`field-${field.key}`}
                      type="text"
                      required
                      maxLength={FIELD_MAX_LENGTH[field.key]}
                      placeholder={FIELD_PLACEHOLDERS[field.key]}
                      value={formData[field.key]}
                      onChange={(event) => handleFieldChange(field.key, event.target.value)}
                      className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-ink shadow-sm"
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {error && (
          <div role="alert" className="rounded-xl border border-danger/30 bg-danger/5 p-4 text-sm font-medium text-danger">
            {error}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-4">
          <button
            type="submit"
            disabled={isSubmitting}
            className="inline-flex items-center rounded-lg bg-treasury-700 px-6 py-3 font-semibold text-white shadow-sm transition-colors hover:bg-treasury-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? 'Verifying…' : 'Verify label'}
          </button>
          {isSubmitting && <Spinner label="Comparing label to application data…" />}
        </div>
      </form>
    </section>
  );
}
