import { Activity, AlertTriangle, ChevronLeft, ChevronRight, RefreshCw, Search, Shield, ShieldCheck, Sigma } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { getDashboardSummary, type DashboardSummary, type SystemHealth, type TraceSummary } from "../api";

type Props = {
  onOpenAction: () => void;
  health: SystemHealth | null;
};

const PAGE_SIZE = 8;

export function Dashboard({ onOpenAction, health }: Props) {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

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

  const filtered = useMemo(() => {
    const rows = summary?.recent ?? [];
    if (!search.trim()) return rows;
    const needle = search.trim().toLowerCase();
    return rows.filter(
      (row) =>
        row.user_query.toLowerCase().includes(needle) ||
        (row.decision ?? "").toLowerCase().includes(needle) ||
        row.trace_id.toLowerCase().includes(needle)
    );
  }, [summary, search]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageRows = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const unguarded = (summary?.total_actions ?? 0) - (summary?.guarded_actions ?? 0);
  const live = !!health && health.provider !== "mock";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold text-white">Security Dashboard</h1>
            <span
              className={`inline-flex items-center gap-1.5 border px-2 py-0.5 text-[11px] font-semibold ${
                live ? "border-emerald/40 text-emerald" : "border-line text-slate-400"
              }`}
              style={{ borderRadius: 999 }}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${live ? "bg-emerald" : "bg-slate-500"}`} />
              {live ? "Live" : "Sandbox"}
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-400">
            Every agent action MemoryIR has evaluated, whether it was causally guarded, and what the guard found.
          </p>
        </div>
        <div className="flex gap-2">
          <button type="button" className="secondary-button" onClick={() => void load()} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button type="button" className="command-button" onClick={onOpenAction}>
            <Shield className="h-4 w-4" />
            Evaluate an Action
          </button>
        </div>
      </div>

      {error ? (
        <div className="border border-rose/40 bg-rose/10 p-3 text-sm text-rose" style={{ borderRadius: 10 }}>
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          icon={Activity}
          tone="teal"
          label="Actions evaluated"
          value={summary?.total_actions ?? (loading ? "…" : 0)}
        />
        <StatTile
          icon={ShieldCheck}
          tone="emerald"
          label="Causally guarded"
          value={summary?.guarded_actions ?? (loading ? "…" : 0)}
          sub={unguarded > 0 ? `${unguarded} pending guard` : "all evaluated"}
        />
        <StatTile
          icon={AlertTriangle}
          tone="rose"
          label="Proxy citations flagged"
          value={summary?.flagged_actions ?? (loading ? "…" : 0)}
          sub="claimed a memory that wasn't the real cause"
        />
        <StatTile
          icon={Sigma}
          tone="amber"
          label="Avg causal precision"
          value={summary?.avg_causal_precision != null ? summary.avg_causal_precision.toFixed(2) : loading ? "…" : "n/a"}
          sub="share of claimed memories that actually drove the decision"
        />
      </div>

      <section className="panel p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Recent activity</h2>
          <label className="flex h-9 items-center gap-2 border border-line bg-panel2 px-3 text-sm text-slate-300" style={{ borderRadius: 10 }}>
            <Search className="h-3.5 w-3.5 text-slate-500" />
            <input
              className="w-48 bg-transparent outline-none placeholder:text-slate-500"
              placeholder="Search traces…"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(1);
              }}
            />
          </label>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[760px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-line text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-3">Trace</th>
                <th className="py-2 pr-3">Action</th>
                <th className="py-2 pr-3">Decision</th>
                <th className="py-2 pr-3">Causal memory</th>
                <th className="py-2 pr-3">Verdict</th>
                <th className="py-2 pr-3">Time</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.map((row) => (
                <TraceRow key={row.trace_id} row={row} />
              ))}
              {summary && filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    {summary.recent.length === 0
                      ? "No actions evaluated yet. Run one from Protected Action or Agent Trace."
                      : "No traces match that search."}
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>

        {filtered.length > PAGE_SIZE ? (
          <div className="mt-4 flex items-center justify-between text-xs text-slate-500">
            <span>
              Page {page} of {pageCount}
            </span>
            <div className="flex gap-1">
              <button
                type="button"
                className="icon-button h-8 w-8"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                type="button"
                className="icon-button h-8 w-8"
                disabled={page >= pageCount}
                onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}

function TraceRow({ row }: { row: TraceSummary }) {
  const when = new Date(row.started_at).toLocaleString();
  const causalMemory = row.ground_path ? row.ground_path.split(" -> ")[0] : "—";
  return (
    <tr className="border-b border-line/70 last:border-0 hover:bg-panel2/60">
      <td className="py-3 pr-3 font-mono text-xs text-slate-500">{row.trace_id.slice(0, 8)}</td>
      <td className="py-3 pr-3 max-w-[260px] truncate text-slate-200" title={row.user_query}>
        {row.user_query}
      </td>
      <td className="py-3 pr-3">
        <span className="border border-line bg-panel2 px-2 py-0.5 text-xs font-semibold text-slate-200" style={{ borderRadius: 8 }}>
          {row.decision ?? "—"}
        </span>
      </td>
      <td className="py-3 pr-3 font-mono text-xs text-slate-400">{causalMemory}</td>
      <td className="py-3 pr-3">
        {row.guarded ? (
          row.flagged ? (
            <Badge tone="rose" icon={AlertTriangle} label="Flagged" />
          ) : (
            <Badge tone="emerald" icon={ShieldCheck} label="Clean" />
          )
        ) : (
          <Badge tone="slate" label="Unguarded" />
        )}
      </td>
      <td className="py-3 pr-3 whitespace-nowrap text-slate-500">{when}</td>
    </tr>
  );
}

function Badge({
  tone,
  icon: Icon,
  label
}: {
  tone: "rose" | "emerald" | "slate";
  icon?: typeof AlertTriangle;
  label: string;
}) {
  const toneClass =
    tone === "rose"
      ? "border-rose/40 bg-rose/10 text-rose"
      : tone === "emerald"
        ? "border-emerald/40 bg-emerald/10 text-emerald"
        : "border-line text-slate-400";
  return (
    <span className={`inline-flex items-center gap-1 border px-2 py-0.5 text-xs font-semibold ${toneClass}`} style={{ borderRadius: 999 }}>
      {Icon ? <Icon className="h-3 w-3" /> : null}
      {label}
    </span>
  );
}

const TONE_STYLES = {
  teal: { bg: "bg-teal/15", text: "text-teal" },
  emerald: { bg: "bg-emerald/15", text: "text-emerald" },
  rose: { bg: "bg-rose/15", text: "text-rose" },
  amber: { bg: "bg-amber/15", text: "text-amber" }
} as const;

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
  tone: keyof typeof TONE_STYLES;
}) {
  const style = TONE_STYLES[tone];
  return (
    <div className="panel p-4">
      <div className={`inline-flex h-9 w-9 items-center justify-center ${style.bg} ${style.text}`} style={{ borderRadius: 10 }}>
        <Icon className="h-4 w-4" />
      </div>
      <div className="mt-3 text-3xl font-semibold text-white">{value}</div>
      <div className="mt-1 text-xs font-medium text-slate-400">{label}</div>
      {sub ? <div className="mt-0.5 text-[11px] text-slate-500">{sub}</div> : null}
    </div>
  );
}
