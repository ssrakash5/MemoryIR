import type { AttributionReport, ClaimedMemory } from "../api";
import { FaithfulnessScore } from "./FaithfulnessScore";

type Props = {
  claimed: ClaimedMemory[];
  report?: AttributionReport | null;
};

export function AttributionPanel({ claimed, report }: Props) {
  return (
    <div className="panel p-4">
      <h2 className="text-sm font-semibold uppercase text-slate-500">Claimed Provenance</h2>
      <div className="mt-3 space-y-3">
        {claimed.map((claim) => (
          <div key={claim.memory_id} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="font-semibold">{claim.display_id}</span>
              <span className="text-slate-500">rank {claim.claimed_rank}</span>
            </div>
            <div className="h-2 overflow-hidden bg-slate-200" style={{ borderRadius: 8 }}>
              <div
                className="h-full bg-cobalt"
                style={{ width: `${Math.max(20, 100 - (claim.claimed_rank - 1) * 28)}%` }}
              />
            </div>
            <p className="text-xs leading-4 text-slate-600">{claim.explanation}</p>
          </div>
        ))}
      </div>
      {report ? (
        <div className="mt-5 border-t border-line pt-4">
          <FaithfulnessScore report={report} />
        </div>
      ) : null}
    </div>
  );
}
