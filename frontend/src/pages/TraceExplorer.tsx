import { Play, Search } from "lucide-react";
import { FormEvent, useState } from "react";
import type { AttributionReport, Intervention, Memory, QueryResult } from "../api";
import { AttributionPanel } from "../components/AttributionPanel";
import { InterventionMatrix } from "../components/InterventionMatrix";
import { MemoryGraph } from "../components/MemoryGraph";
import { RetrievalPanel } from "../components/RetrievalPanel";

type Props = {
  memories: Memory[];
  result: QueryResult | null;
  interventions: Intervention[];
  report: AttributionReport | null;
  loading: boolean;
  onQuery: (query: string) => Promise<void>;
  onInvestigate: () => Promise<void>;
};

export function TraceExplorer({
  memories,
  result,
  interventions,
  report,
  loading,
  onQuery,
  onInvestigate
}: Props) {
  const [query, setQuery] = useState("Which database architecture best satisfies the project requirements?");

  async function submit(event: FormEvent) {
    event.preventDefault();
    await onQuery(query);
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-white">Agent Trace</h1>
          <p className="text-sm text-slate-400">Retrieval, response, claims, and counterfactual sensitivity.</p>
        </div>
        <button type="button" className="command-button" onClick={onInvestigate} disabled={loading || !result}>
          <Play className="h-4 w-4" />
          Investigate
        </button>
      </div>

      <form className="panel flex flex-col gap-3 p-4 md:flex-row" onSubmit={submit}>
        <label className="flex flex-1 items-center gap-2 border border-line bg-panel2 px-3" style={{ borderRadius: 10 }}>
          <Search className="h-4 w-4 flex-none text-slate-500" />
          <input
            className="h-11 min-w-0 flex-1 bg-transparent text-slate-100 outline-none"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <button type="submit" className="command-button" disabled={loading}>
          <Search className="h-4 w-4" />
          Query
        </button>
      </form>

      {result ? (
        <>
          <div className="grid gap-4 xl:grid-cols-[minmax(260px,1fr)_minmax(320px,1.2fr)_minmax(260px,1fr)]">
            <RetrievalPanel retrieved={result.retrieved} />
            <div className="panel p-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Agent</h2>
              <div className="mt-4 space-y-4">
                <div>
                  <div className="text-xs font-semibold uppercase text-slate-500">Question</div>
                  <p className="mt-1 text-sm leading-6 text-slate-300">{query}</p>
                </div>
                <div>
                  <div className="text-xs font-semibold uppercase text-slate-500">Answer</div>
                  <p className="mt-1 text-xl font-semibold text-white">{result.answer}</p>
                </div>
                <div>
                  <div className="text-xs font-semibold uppercase text-slate-500">Decision</div>
                  <p className="mt-1 inline-flex border border-teal/40 bg-teal/10 px-3 py-1 text-sm font-semibold text-teal" style={{ borderRadius: 8 }}>
                    {result.decision}
                  </p>
                </div>
                <div className="text-xs text-slate-500">Trace {result.trace_id}</div>
              </div>
            </div>
            <AttributionPanel claimed={result.claimed} report={report} />
          </div>

          <InterventionMatrix interventions={interventions} />

          <div className="panel p-4">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">Ground Provenance</h2>
            <MemoryGraph
              memories={memories}
              highlighted={report?.ground_provenance.flatMap((item) => [
                String(item.ancestor ?? ""),
                String(item.retrieved ?? "")
              ]) ?? ["M2", "M7"]}
            />
          </div>
        </>
      ) : (
        <div className="panel p-6 text-sm text-slate-400">
          Ask the agent a question to create a trace, then investigate what actually drove its answer.
        </div>
      )}
    </div>
  );
}
