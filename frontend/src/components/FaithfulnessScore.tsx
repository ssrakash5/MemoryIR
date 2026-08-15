import type { AttributionReport } from "../api";

type Props = {
  report: AttributionReport;
};

export function FaithfulnessScore({ report }: Props) {
  const metrics = [
    ["Claim/retrieval precision", report.claim_retrieval_precision],
    ["Causal precision", report.causal_precision],
    ["Causal recall", report.causal_recall],
    ["Proxy citation rate", report.proxy_citation_rate]
  ] as const;
  return (
    <div className="space-y-3">
      {metrics.map(([label, value]) => (
        <div key={label}>
          <div className="mb-1 flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-600">{label}</span>
            <span className="tabular-nums text-slate-500">{value.toFixed(2)}</span>
          </div>
          <div className="h-2 overflow-hidden bg-slate-200" style={{ borderRadius: 8 }}>
            <div className="h-full bg-teal" style={{ width: `${Math.min(100, value * 100)}%` }} />
          </div>
        </div>
      ))}
      <div className="border-t border-line pt-3 text-sm">
        <span className="font-semibold text-ink">Ground path </span>
        <span className="text-slate-600">
          {report.ground_provenance.length
            ? report.ground_provenance.map((item) => (item.path as string[]).join(" -> ")).join(", ")
            : "pending"}
        </span>
      </div>
    </div>
  );
}
