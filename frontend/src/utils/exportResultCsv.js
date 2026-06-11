import { COMPARISON_FIELDS, GOVERNMENT_WARNING_LABEL } from '../constants/labelFields.js';

function csvEscape(value) {
  const text = value === null || value === undefined ? '' : String(value);
  if (/["\r\n,]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function csvRow(values) {
  return `${values.map(csvEscape).join(',')}\r\n`;
}

// Builds a CSV summary of a single VerificationResult for the "Export CSV" button.
export function buildResultCsv(result) {
  let csv = '';
  csv += csvRow(['Session ID', result.session_id]);
  csv += csvRow(['Filename', result.filename]);
  csv += csvRow(['Overall Status', result.overall_status]);
  csv += csvRow(['Confidence Score', result.confidence_score]);
  csv += csvRow(['Image Quality Score', result.image_quality_score]);
  csv += csvRow(['Image Quality Issues', result.quality_issues.join('; ')]);
  csv += csvRow(['OCR Engine', result.ocr_engine_used]);
  csv += '\r\n';
  csv += csvRow(['Field', 'Label Says', 'Application Says', 'Status', 'Confidence (%)']);

  const fieldByKey = new Map(result.fields.map((field) => [field.field, field]));
  for (const { key, label } of COMPARISON_FIELDS) {
    const field = fieldByKey.get(key);
    if (!field) continue;
    csv += csvRow([label, field.extracted, field.expected, field.status, Math.round(field.score)]);
  }

  const warning = result.government_warning;
  csv += csvRow([
    GOVERNMENT_WARNING_LABEL,
    warning.extracted_text,
    warning.expected_text,
    warning.valid ? 'MATCH' : 'NO_MATCH',
    '',
  ]);

  return csv;
}

// Triggers a browser download of `content` as `filename`.
export function downloadCsv(filename, content) {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
