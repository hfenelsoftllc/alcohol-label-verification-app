import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'jest-axe';

import App from '../App.jsx';

afterEach(cleanup);

// jsdom does not perform layout/paint, so axe cannot evaluate computed
// colors — contrast is verified manually instead (docs/ACCESSIBILITY-REPORT.md).
const AXE_OPTIONS = { rules: { 'color-contrast': { enabled: false } } };

function renderApp(initialEntries) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <App />
    </MemoryRouter>,
  );
}

const GOOD_RESULT = {
  session_id: 'abc123',
  filename: 'sample-label.jpg',
  image_quality_score: 92,
  quality_issues: [],
  overall_status: 'MATCH',
  fields: [
    { field: 'brand', extracted: 'Old Faithful', expected: 'Old Faithful', score: 100, status: 'MATCH' },
    { field: 'class_type', extracted: 'Bourbon Whiskey', expected: 'Bourbon Whiskey', score: 100, status: 'MATCH' },
    { field: 'abv', extracted: '40% Alc. by Vol.', expected: '40% Alc. by Vol.', score: 100, status: 'MATCH' },
    { field: 'net_contents', extracted: '750 mL', expected: '750 mL', score: 100, status: 'MATCH' },
    {
      field: 'name_address',
      extracted: 'Old Faithful Distillery, Springfield, IL',
      expected: 'Old Faithful Distillery, Springfield, IL',
      score: 100,
      status: 'MATCH',
    },
    { field: 'country_of_origin', extracted: 'United States', expected: 'United States', score: 100, status: 'MATCH' },
  ],
  government_warning: {
    valid: true,
    issues: [],
    extracted_text: 'GOVERNMENT WARNING: ...',
    expected_text: 'GOVERNMENT WARNING: ...',
  },
};

const FLAGGED_RESULT = {
  ...GOOD_RESULT,
  session_id: 'def456',
  image_quality_score: 28,
  quality_issues: ['blurry', 'excessive_glare'],
  overall_status: 'PARTIAL',
  fields: GOOD_RESULT.fields.map((field, index) =>
    index === 0 ? { ...field, extracted: 'Old Faithfull', score: 82, status: 'PARTIAL_MATCH' } : field,
  ),
  government_warning: {
    valid: false,
    issues: ['MISSING_TEXT'],
    extracted_text: 'GOVERNMENT WARNING: incomplete...',
    expected_text: 'GOVERNMENT WARNING: ...',
  },
};

describe('accessibility (axe)', () => {
  it('upload page (empty form) has no violations', async () => {
    const { container } = renderApp(['/']);
    expect(await axe(container, AXE_OPTIONS)).toHaveNoViolations();
  });

  it('upload page with a selected image has no violations', async () => {
    const { container } = renderApp(['/']);
    const file = new File(['fake-image-bytes'], 'sample-label.jpg', { type: 'image/jpeg' });
    const fileInput = container.querySelector('#label-image');

    fireEvent.change(fileInput, { target: { files: [file] } });
    await waitFor(() => screen.getByText('sample-label.jpg'));

    expect(await axe(container, AXE_OPTIONS)).toHaveNoViolations();
  });

  it('review page (no result in route state) has no violations', async () => {
    const { container } = renderApp(['/results/abc123']);
    expect(await axe(container, AXE_OPTIONS)).toHaveNoViolations();
  });

  it('review page (matching result) has no violations', async () => {
    const { container } = renderApp([{ pathname: '/results/abc123', state: { result: GOOD_RESULT } }]);
    expect(await axe(container, AXE_OPTIONS)).toHaveNoViolations();
  });

  it('review page (flagged result with low quality + warnings) has no violations', async () => {
    const { container } = renderApp([{ pathname: '/results/def456', state: { result: FLAGGED_RESULT } }]);
    expect(await axe(container, AXE_OPTIONS)).toHaveNoViolations();
  });

  it('batch page (upload form) has no violations', async () => {
    const { container } = renderApp(['/batch']);
    expect(await axe(container, AXE_OPTIONS)).toHaveNoViolations();
  });

  it('not found page has no violations', async () => {
    const { container } = renderApp(['/this-route-does-not-exist']);
    expect(await axe(container, AXE_OPTIONS)).toHaveNoViolations();
  });
});
