// Maps a MatchStatus or OverallStatus (backend/app/models.py) to an icon +
// text label + color. The icon is decorative — color and meaning are always
// carried by the text too, per the design system's accessibility rule
// (frontend/src/index.css). A Map (rather than a plain object) sidesteps
// security/detect-object-injection on the lookup below.
const STATUS = new Map([
  ['MATCH', { icon: '✅', label: 'Match', className: 'text-success' }],
  ['PARTIAL_MATCH', { icon: '⚠️', label: 'Partial match', className: 'text-warning' }],
  ['PARTIAL', { icon: '⚠️', label: 'Partial match', className: 'text-warning' }],
  ['NO_MATCH', { icon: '❌', label: 'No match', className: 'text-danger' }],
  ['FAIL', { icon: '❌', label: 'Discrepancy found', className: 'text-danger' }],
  ['ERROR', { icon: '❌', label: 'Error', className: 'text-danger' }],
]);

export default function StatusBadge({ status }) {
  const config = STATUS.get(status) ?? STATUS.get('NO_MATCH');
  return (
    <span className={`inline-flex items-center gap-1.5 text-sm font-semibold ${config.className}`}>
      <span aria-hidden="true">{config.icon}</span>
      {config.label}
    </span>
  );
}
