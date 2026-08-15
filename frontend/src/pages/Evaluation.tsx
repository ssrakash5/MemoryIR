import { BarChart3 } from "lucide-react";
import { useEffect, useState } from "react";
import { getEvaluation } from "../api";

type Summary = {
  label: string;
  case_count: number;
  scenario_types: string[];
  metrics: Record<string, number>;
  comparison: Array<Record<string, number | string>>;
};

export function Evaluation() {
  const [summary, setSummary] = useState<Summary | null>(null);

  useEffect(() => {
    getEvaluation().then(setSummary).catch(() => setSummary(null));
  }, []);

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <div className="icon-button">
          <BarChart3 className="h-4 w-4" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold text-ink">Quality Benchmarks</h1>
          <p className="text-sm text-slate-600">
            How reliably MemoryIR's causal attribution holds up across direct, one-hop, multi-hop, and proxy-citation
            scenarios.
          </p>
        </div>
      </div>
      {summary ? (
        <>
          <div className="grid gap-3 md:grid-cols-4">
            {summary.scenario_types.map((scenario) => (
              <div key={scenario} className="panel p-4">
                <div className="text-sm font-semibold text-ink">{scenario}</div>
              </div>
            ))}
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="panel p-4">
              <h2 className="text-sm font-semibold uppercase text-slate-500">Metrics</h2>
              <div className="mt-4 space-y-3">
                {Object.entries(summary.metrics).map(([key, value]) => (
                  <div key={key}>
                    <div className="mb-1 flex items-center justify-between text-sm">
                      <span className="capitalize text-slate-700">{key.replace(/_/g, " ")}</span>
                      <span className="tabular-nums text-slate-500">{value}</span>
                    </div>
                    <div className="h-2 overflow-hidden bg-slate-200" style={{ borderRadius: 8 }}>
                      <div className="h-full bg-amber" style={{ width: `${Math.min(100, Number(value) * 100)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="panel p-4">
              <h2 className="text-sm font-semibold uppercase text-slate-500">Comparison</h2>
              <div className="mt-4 space-y-3">
                {summary.comparison.map((row) => (
                  <div key={String(row.method)} className="border border-line p-3" style={{ borderRadius: 8 }}>
                    <div className="font-semibold">{String(row.method)}</div>
                    <div className="mt-2 grid grid-cols-2 gap-3 text-sm text-slate-600">
                      <span>Precision {Number(row.causal_precision).toFixed(2)}</span>
                      <span>Recall {Number(row.causal_recall).toFixed(2)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="text-sm text-slate-600">{summary.case_count} controlled scenarios evaluated.</div>
        </>
      ) : (
        <div className="panel p-6 text-sm text-slate-600">
          Benchmark results aren't available. Run <code className="font-mono">python eval/run_causal_eval.py</code> from
          the repo to generate them.
        </div>
      )}
    </div>
  );
}
