import { Activity, AlertTriangle, RefreshCw, ShieldCheck, ShieldQuestion } from "lucide-react";
import { useEffect, useState } from "react";
import { getDashboardSummary, type DashboardSummary, type TraceSummary } from "../api";

type Props = {
  onOpenAction: () => void;
};

export function Dashboard({ onOpenAction }: Props) {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setSummary(await getDashboardSummary());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const unguarded = (summary?.total_actions ?? 0) - (summary?.guarded_actions ?? 0);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Security Dashboard</h1>
          <p className="text-sm text-slate-600">
            Every agent action MemoryIR has seen, whether it was causally guarded, and what the guard found.
          </p>
        </div>
        <div className="flex gap-2">
          <button type="button" className="secondary-button" onClick={() => void load()} disabled={loading}>
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button type="button" className="command-button" onClick={onOpenAction}>
            <ShieldCheck className="h-4 w-4" />
            Evaluate an Action
          </button>
        </div>
      </div>

      {error ? (
        <div className="border border-rose bg-rose-50 p-3 text-sm text-rose" style={{ borderRadius: 8 }}>
          {error}
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          icon={Activity}
          label="Actions evaluated"
          value={summary?.total_actions ?? (loading ? "…" : 0)}
        />
        <StatTile
          icon={ShieldCheck}
          label="Causally guarded"
          value={summary?.guarded_actions ?? (loading ? "…" : 0)}
          sub={unguarded > 0 ? `${unguarded} pending guard` : "all evaluated"}
        />
        <StatTile
          icon={AlertTriangle}
          label="Proxy citations flagged"
          value={summary?.flagged_actions ?? (loading ? "…" : 0)}
          tone={summary && summary.flagged_actions > 0 ? "rose" : undefined}
          sub="claimed a memory that wasn't the real cause"
        />
        <StatTile
          icon={ShieldQuestion}
          label="Avg causal precision"
          value={
            summary?.avg_causal_precision != null ? summary.avg_causal_precision.toFixed(2) : loading ? "…" : "n/a"
          }
          sub="share of claimed memories that actually drove the decision"
        />
      </div>

      <section className="panel p-4">
        <h2 className="text-sm font-semibold uppercase text-slate-500">Recent activity</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[720px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-line text-left text-xs font-semibold uppercase text-slate-500">
                <th className="py-2 pr-3">When</th>
                <th className="py-2 pr-3">Query</th>
                <th className="py-2 pr-3">Decision</th>
                <th className="py-2 pr-3">Guard</th>
                <th className="py-2 pr-3">Causal precision</th>
                <th className="py-2 pr-3">Ground path</th>
              </tr>
            </thead>
            <tbody>
              {(summary?.recent ?? []).map((row) => (
                <TraceRow key={row.trace_id} row={row} />
              ))}
              {summary && summary.recent.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-6 text-center text-slate-500">
                    No actions evaluated yet. Run one from Protected Action or Agent Trace.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function TraceRow({ row }: { row: TraceSummary }) {
  const when = new Date(row.started_at).toLocaleString();
  return (
    <tr className="border-b border-line last:border-0">
      <td className="py-2 pr-3 whitespace-nowrap text-slate-500">{when}</td>
      <td className="py-2 pr-3 max-w-[280px] truncate text-ink" title={row.user_query}>
        {row.user_query}
      </td>
      <td className="py-2 pr-3 font-semibold text-ink">{row.decision ?? "—"}</td>
      <td className="py-2 pr-3">
        {row.guarded ? (
          row.flagged ? (
            <span className="inline-flex items-center gap-1 border border-rose px-2 py-0.5 text-xs font-semibold text-rose" style={{ borderRadius: 8 }}>
              <AlertTriangle className="h-3 w-3" />
              Proxy flagged
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 border border-teal px-2 py-0.5 text-xs font-semibold text-teal" style={{ borderRadius: 8 }}>
              <ShieldCheck className="h-3 w-3" />
              Clean
            </span>
          )
        ) : (
          <span className="inline-flex items-center gap-1 border border-line px-2 py-0.5 text-xs font-semibold text-slate-500" style={{ borderRadius: 8 }}>
            Unguarded
          </span>
        )}
      </td>
      <td className="py-2 pr-3 tabular-nums text-slate-700">
        {row.causal_precision != null ? row.causal_precision.toFixed(2) : "—"}
      </td>
      <td className="py-2 pr-3 text-slate-600">{row.ground_path ?? "—"}</td>
    </tr>
  );
}

function StatTile({
  icon: Icon,
  label,
  value,
  sub,
  tone
}: {
  icon: typeof Activity;
  label: string;
  value: string | number;
  sub?: string;
  tone?: "rose";
}) {
  return (
    <div className="panel p-4">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase text-slate-500">
        <Icon className="h-4 w-4" />
        {label}
      </div>
      <div className={`mt-2 text-3xl font-semibold ${tone === "rose" ? "text-rose" : "text-ink"}`}>{value}</div>
      {sub ? <div className="mt-1 text-xs text-slate-500">{sub}</div> : null}
    </div>
  );
}
