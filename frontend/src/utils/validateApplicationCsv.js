import { LABEL_FIELD_NAMES } from '../constants/labelFields.js';
import { parseCsv } from './parseCsv.js';

// Strips a UTF-8 BOM, mirroring the backend's `utf-8-sig` decode
// (backend/batch/csv_input.py).
function stripBom(text) {
  return text.charCodeAt(0) === 0xfeff ? text.slice(1) : text;
}

// Mirrors the structural checks in backend/batch/csv_input.py so column
// mapping problems and row-count mismatches surface before the upload
// starts (ISSUE 3.4, FedRAMP SI-10). Returns a list of human-readable error
// strings; an empty list means the CSV is ready to submit. `expectedRows`
// is the number of images extracted from the ZIP so far — the row-count
// check is skipped while that's still 0 (ZIP not uploaded/processed yet).
export async function validateApplicationCsv(csvFile, expectedRows) {
  const rows = parseCsv(stripBom(await csvFile.text()));

  if (rows.length === 0) {
    return ['application_csv is empty'];
  }

  const [header, ...dataRows] = rows;
  const errors = [];

  const missing = LABEL_FIELD_NAMES.filter((name) => !header.includes(name));
  if (missing.length > 0) {
    errors.push(`application_csv is missing required column(s): ${missing.join(', ')}`);
  }

  if (errors.length === 0 && expectedRows > 0 && dataRows.length !== expectedRows) {
    errors.push(
      `application_csv has ${dataRows.length} row(s) but ${expectedRows} image file(s) were found in the ZIP`,
    );
  }

  return errors;
}
