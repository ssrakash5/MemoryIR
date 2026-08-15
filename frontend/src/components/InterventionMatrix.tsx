import { AlertTriangle, CheckCircle2 } from "lucide-react";
import type { Intervention } from "../api";

type Props = {
  interventions: Intervention[];
};

export function InterventionMatrix({ interventions }: Props) {
  const direct = interventions.filter((item) => item.intervention_type === "RETRIEVED_MEMORY_ABLATION");
  const ancestors = interventions.filter((item) => item.intervention_type === "ANCESTOR_ABLATION");
  return (
    <div className="panel p-4">
      <h2 className="text-sm font-semibold uppercase text-slate-500">Interventions</h2>
      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <div>
          <div className="mb-2 text-xs font-semibold uppercase text-slate-500">Retrieved memory ablation</div>
          <Rows rows={direct} />
        </div>
        <div>
          <div className="mb-2 text-xs font-semibold uppercase text-slate-500">Ancestor recomputation</div>
          <Rows rows={ancestors} />
        </div>
      </div>
    </div>
  );
}

function Rows({ rows }: { rows: Intervention[] }) {
  if (rows.length === 0) {
    return <div className="border border-dashed border-line p-3 text-sm text-slate-500" style={{ borderRadius: 8 }}>No runs yet.</div>;
  }
  return (
    <div className="space-y-2">
      {rows.map((row) => (
        <div key={row.intervention_id} className="flex items-center justify-between gap-3 border border-line bg-slate-50 p-3" style={{ borderRadius: 8 }}>
          <div className="min-w-0">
            <div className="text-sm font-semibold">Remove {row.target_display_id ?? "memory"}</div>
            <div className="truncate text-xs text-slate-600">
              {row.baseline_decision} -&gt; {row.counterfactual_decision}
            </div>
          </div>
          <div className={`inline-flex items-center gap-1 text-xs font-semibold ${row.decision_changed ? "text-rose" : "text-teal"}`}>
            {row.decision_changed ? <AlertTriangle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
            {row.decision_changed ? "FLIP" : "no effect"}
          </div>
        </div>
      ))}
    </div>
  );
}
