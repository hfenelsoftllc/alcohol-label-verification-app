// Horizontal percentage bar for a FieldComparison.score (0-100).
export default function ConfidenceBar({ score, label = 'Confidence' }) {
  const pct = Math.max(0, Math.min(100, Math.round(score)));
  return (
    <div className="flex items-center gap-2">
      <div
        role="progressbar"
        aria-label={label}
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-2 flex-1 rounded-full bg-slate-200"
      >
        <div className="h-2 rounded-full bg-treasury-600" style={{ width: `${pct}%` }} />
      </div>
      <span className="w-10 text-right text-xs font-medium tabular-nums text-muted">{pct}%</span>
    </div>
  );
}
