import { AlertTriangle, CheckCircle2, Database, Play, Search, Shield, ShieldCheck } from "lucide-react";
import type { AttributionReport, Intervention, QueryResult } from "../api";
import { FaithfulnessScore } from "../components/FaithfulnessScore";
import { InterventionMatrix } from "../components/InterventionMatrix";
import { RetrievalPanel } from "../components/RetrievalPanel";

export const PROTECTED_ACTION_QUERY =
  "A deploy script wants to modify the production database architecture for customer orders. Which database architecture should be used?";

type Props = {
  result: QueryResult | null;
  interventions: Intervention[];
  report: AttributionReport | null;
  loading: boolean;
  onAttempt: () => Promise<void>;
  onGuard: () => Promise<void>;
  onOpenTrace: () => void;
  onOpenForensics: () => void;
};

const requestedMutation = "customer_orders.primary_database = POSTGRES_SINGLE_REGION";
const protectedPolicy = "Production customer data must survive regional failures.";

export function ProtectedAction({
  result,
  interventions,
  report,
  loading,
  onAttempt,
  onGuard,
  onOpenTrace,
  onOpenForensics
}: Props) {
  const verdict = buildVerdict(result, interventions, report);
  const decisiveRuns = interventions.filter((item) => item.decision_changed);
  const groundPaths =
    report?.ground_provenance.map((item) => (Array.isArray(item.path) ? item.path.map(String).join(" -> ") : "")).filter(Boolean) ?? [];

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center bg-teal/15 text-teal" style={{ borderRadius: 10 }}>
            <Shield className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-white">Protected Action Review</h1>
            <p className="text-sm text-slate-400">We analyze memory to prevent harmful or unjustified actions.</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="command-button" onClick={onAttempt} disabled={loading}>
            <Play className="h-4 w-4" />
            Submit for Review
          </button>
          <button type="button" className="secondary-button" onClick={onGuard} disabled={loading || !result}>
            <ShieldCheck className="h-4 w-4" />
            Run MemoryIR Guard
          </button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_1fr_1.1fr]">
        <section className="panel p-4">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <Database className="h-4 w-4" />
            Attempted Mutation
          </div>
          <div className="mt-4 space-y-4">
            <div>
              <div className="text-xs font-semibold uppercase text-slate-500">Write request</div>
              <p className="mt-1.5 border border-line bg-panel2 px-3 py-2 font-mono text-sm leading-6 text-rose" style={{ borderRadius: 8 }}>
                {requestedMutation}
              </p>
            </div>
            <div>
              <div className="text-xs font-semibold uppercase text-slate-500">Protected policy</div>
              <p className="mt-1 text-sm leading-6 text-slate-300">{protectedPolicy}</p>
            </div>
            <div className="border-t border-line pt-4 text-sm leading-6 text-slate-400">
              Without a causal check, this write ships on the agent's word alone — no proof it actually respects the deployment constraint.
            </div>
          </div>
        </section>

        <section className="panel p-4">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <Search className="h-4 w-4" />
            Agent Proposal
          </div>
          <div className="mt-4 space-y-4">
            <div>
              <div className="text-xs font-semibold uppercase text-slate-500">Proposed decision</div>
              <p className="mt-1.5 inline-flex border border-teal/40 bg-teal/10 px-3 py-1 text-lg font-semibold text-teal" style={{ borderRadius: 8 }}>
                {result?.decision ?? "Pending"}
              </p>
            </div>
            <div>
              <div className="text-xs font-semibold uppercase text-slate-500">Answer</div>
              <p className="mt-1 min-h-16 text-sm leading-6 text-slate-300">
                {result?.answer ?? "Submit the proposed action to create an agent trace."}
              </p>
            </div>
            <div className="border-t border-line pt-4 text-xs text-slate-500">
              {result ? `Trace ${result.trace_id}` : "Awaiting submission"}
            </div>
          </div>
        </section>

        <section className={`border p-4 ${verdict.blocked ? "border-rose/40 bg-rose/[0.07]" : "border-line bg-panel"}`} style={{ borderRadius: 14 }}>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            {verdict.blocked ? <AlertTriangle className="h-4 w-4 text-rose" /> : <ShieldCheck className="h-4 w-4 text-teal" />}
            MemoryIR Verdict
          </div>
          <div className="mt-4 flex items-start justify-between gap-3">
            <div>
              <div className={`text-3xl font-semibold ${verdict.blocked ? "text-rose" : "text-white"}`}>{verdict.label}</div>
              <p className="mt-2 text-sm leading-6 text-slate-300">{verdict.reason}</p>
            </div>
            <div
              className={`inline-flex items-center gap-1 border px-2 py-1 text-xs font-semibold ${
                verdict.blocked ? "border-rose/40 text-rose" : "border-line text-slate-400"
              }`}
              style={{ borderRadius: 999 }}
            >
              {verdict.blocked ? <AlertTriangle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
              {verdict.badge}
            </div>
          </div>
          <div className="mt-5 grid gap-2 text-sm sm:grid-cols-2">
            <Evidence label="Protected memory" value={verdict.protectedMemory} />
            <Evidence label="Ground path" value={groundPaths.join(", ") || "Pending"} />
          </div>
        </section>
      </div>

      {result ? (
        <div className="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
          <RetrievalPanel retrieved={result.retrieved} />
          <section className="panel p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Why MemoryIR Blocks</h2>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <Evidence label="Requested write" value="POSTGRES_SINGLE_REGION" />
              <Evidence label="Causal decision" value={result.decision} />
              <Evidence
                label="Changed under ablation"
                value={decisiveRuns.map((item) => item.target_display_id).filter(Boolean).join(", ") || "Run guard"}
              />
            </div>
            {report ? (
              <div className="mt-5 border-t border-line pt-4">
                <FaithfulnessScore report={report} />
              </div>
            ) : (
              <p className="mt-5 border-t border-line pt-4 text-sm leading-6 text-slate-400">
                The guard runs counterfactual removals over retrieved and ancestor memories. A write is blocked when protected memory is causal, not merely retrieved.
              </p>
            )}
            <div className="mt-5 flex flex-wrap gap-2">
              <button type="button" className="secondary-button" onClick={onOpenTrace}>
                <Search className="h-4 w-4" />
                Open Trace
              </button>
              <button type="button" className="secondary-button" onClick={onOpenForensics} disabled={!report}>
                <ShieldCheck className="h-4 w-4" />
                Open Forensics
              </button>
            </div>
          </section>
        </div>
      ) : null}

      <InterventionMatrix interventions={interventions} />
    </div>
  );
}

function Evidence({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-line bg-panel2 p-3" style={{ borderRadius: 10 }}>
      <div className="text-xs font-semibold uppercase text-slate-500">{label}</div>
      <div className="mt-1 min-h-6 text-sm font-semibold leading-5 text-slate-100">{value}</div>
    </div>
  );
}

function buildVerdict(
  result: QueryResult | null,
  interventions: Intervention[],
  report: AttributionReport | null
) {
  if (!result) {
    return {
      blocked: false,
      label: "Ready",
      badge: "armed",
      reason: "The protected action has not been evaluated yet.",
      protectedMemory: "M2 / M7"
    };
  }

  if (!report) {
    return {
      blocked: false,
      label: "Unverified",
      badge: "trace only",
      reason: "The agent produced a decision, but MemoryIR has not run the causal guard yet.",
      protectedMemory: result.retrieved.map((item) => item.display_id).join(", ")
    };
  }

  const causalDisplays = new Set([
    ...report.influential_memories,
    ...report.ground_provenance.flatMap((item) => [String(item.retrieved ?? ""), String(item.ancestor ?? "")])
  ]);
  const protectedMemory = ["M2", "M7"].filter((item) => causalDisplays.has(item)).join(" -> ");
  const hasProtectedCause = protectedMemory.length > 0;
  const conflictsWithRequest = result.decision === "COCKROACHDB";
  const blocked = hasProtectedCause && conflictsWithRequest;
  const changed = interventions.find((item) => item.decision_changed && item.target_display_id === "M7");

  return {
    blocked,
    label: blocked ? "Blocked" : "Allowed",
    badge: blocked ? "write stopped" : "no causal conflict",
    reason: blocked
      ? `MemoryIR found protected memory ${protectedMemory} causally changed the decision${changed?.counterfactual_decision ? ` to ${changed.counterfactual_decision}` : ""}. The requested single-region write is rejected.`
      : "No protected causal memory changed the decision under intervention.",
    protectedMemory: protectedMemory || "None"
  };
}
