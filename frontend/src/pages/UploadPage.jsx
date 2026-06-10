// Upload page (route: /). The full single-label workflow — drag-and-drop,
// application fields, side-by-side results — is built in ISSUE 3.3. This is the
// accessible shell it slots into.
export default function UploadPage() {
  return (
    <section aria-labelledby="upload-heading">
      <h1 id="upload-heading" className="text-2xl font-bold text-ink">
        Verify a single label
      </h1>
      <p className="mt-2 max-w-2xl text-muted">
        Upload a label image and its application data to check them field-by-field.
      </p>

      <div className="mt-6 rounded-lg border-2 border-dashed border-slate-300 bg-white p-10 text-center">
        <p className="font-medium text-ink">Drag and drop a label image here</p>
        <p className="mt-1 text-sm text-muted">or click to browse — built in ISSUE 3.3</p>
      </div>
    </section>
  );
}
