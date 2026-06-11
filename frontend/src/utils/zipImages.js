import JSZip from 'jszip';

// Mirrors the magic-number signatures accepted by backend/app/validation.py.
const EXTENSION_MIME = new Map([
  ['jpg', 'image/jpeg'],
  ['jpeg', 'image/jpeg'],
  ['png', 'image/png'],
  ['gif', 'image/gif'],
  ['bmp', 'image/bmp'],
  ['tif', 'image/tiff'],
  ['tiff', 'image/tiff'],
  ['webp', 'image/webp'],
]);

function extensionOf(name) {
  const dot = name.lastIndexOf('.');
  return dot === -1 ? '' : name.slice(dot + 1).toLowerCase();
}

// True for entries that are real label images: not a directory, not a
// macOS/Finder artifact (__MACOSX/, .DS_Store), and a recognized image
// extension.
function isImageEntry(entry) {
  if (entry.dir) return false;
  if (entry.name.startsWith('__MACOSX/')) return false;
  const base = entry.name.split('/').pop() || '';
  if (base.startsWith('.')) return false;
  return EXTENSION_MIME.has(extensionOf(base));
}

// Unzips `zipFile` and returns its label images as `File` objects, sorted by
// path (natural/numeric order) so the order lines up with the application
// CSV's row order.
export async function extractImagesFromZip(zipFile) {
  const zip = await JSZip.loadAsync(zipFile);
  const entries = Object.values(zip.files)
    .filter(isImageEntry)
    .sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));

  const images = [];
  for (const entry of entries) {
    const buffer = await entry.async('arraybuffer');
    const base = entry.name.split('/').pop();
    images.push(new File([buffer], base, { type: EXTENSION_MIME.get(extensionOf(base)) }));
  }
  return images;
}
