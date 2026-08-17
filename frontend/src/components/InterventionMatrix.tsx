import { AlertTriangle, ArrowRight, CheckCircle2 } from "lucide-react";
import type { Intervention } from "../api";

type Props = {
  interventions: Intervention[];
};

export function InterventionMatrix({ interventions }: Props) {
  const direct = interventions.filter((item) => item.intervention_type === "RETRIEVED_MEMORY_ABLATION");
  const ancestors = interventions.filter((item) => item.intervention_type === "ANCESTOR_ABLATION");
  const onlyCausal = direct.filter((item) => item.decision_changed).map((item) => item.target_display_id).filter(Boolean);

  return (
    <div className="panel p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Counterfactual Interventions</h2>
        <span className="text-xs text-slate-500">Test how memory edits change the decision.</span>
      </div>
      <div className="mt-3 grid gap-4 lg:grid-cols-2">
        <div>
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Retrieved memory ablation</div>
          <Rows rows={direct} />
        </div>
        <div>
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Ancestor recomputation</div>
          <Rows rows={ancestors} />
        </div>
      </div>
      {onlyCausal.length > 0 ? (
        <div className="mt-4 border border-teal/30 bg-teal/10 px-3 py-2 text-xs text-teal" style={{ borderRadius: 10 }}>
          Only {onlyCausal.join(", ")} is causally influential. Removing it changes the decision.
        </div>
      ) : null}
    </div>
  );
}

function Rows({ rows }: { rows: Intervention[] }) {
  if (rows.length === 0) {
    return (
      <div className="border border-dashed border-line p-3 text-sm text-slate-500" style={{ borderRadius: 10 }}>
        No runs yet.
      </div>
    );
  }
  return (
    <div className="space-y-2">
      {rows.map((row) => (
        <div
          key={row.intervention_id}
          className="grid grid-cols-[auto_1fr_auto] items-center gap-3 border border-line bg-panel2 p-3"
          style={{ borderRadius: 10 }}
        >
          <div
            className={`flex h-9 w-9 flex-none items-center justify-center text-xs font-bold ${
              row.decision_changed ? "bg-rose/15 text-rose" : "bg-slate-700/30 text-slate-300"
            }`}
            style={{ borderRadius: 8 }}
          >
            {row.target_display_id ?? "?"}
          </div>
          <div className="min-w-0">
            <div className="text-xs font-semibold uppercase text-slate-500">Remove {row.target_display_id ?? "memory"}</div>
            <div className="mt-0.5 flex items-center gap-2 truncate text-sm text-slate-300">
              <span>{row.baseline_decision}</span>
              <ArrowRight className="h-3 w-3 flex-none text-slate-600" />
              <span className={row.decision_changed ? "font-semibold text-rose" : "text-slate-300"}>{row.counterfactual_decision}</span>
            </div>
          </div>
          <div className={`inline-flex items-center gap-1 text-xs font-semibold ${row.decision_changed ? "text-rose" : "text-emerald"}`}>
            {row.decision_changed ? <AlertTriangle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
            {row.decision_changed ? "Flipped" : "No change"}
          </div>
        </div>
      ))}
    </div>
  );
}
