import { SendHorizontal } from "lucide-react";
import { FormEvent, useState } from "react";
import type { ForensicResponse, QueryResult } from "../api";

type Props = {
  result: QueryResult | null;
  forensic: ForensicResponse | null;
  loading: boolean;
  onInvestigate: (question: string) => Promise<void>;
};

export function Forensics({ result, forensic, loading, onInvestigate }: Props) {
  const [question, setQuestion] = useState("Why was M7 influential?");

  async function submit(event: FormEvent) {
    event.preventDefault();
    await onInvestigate(question);
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold text-ink">MemoryIR Investigator</h1>
        <p className="text-sm text-slate-600">CockroachDB Managed MCP forensic console.</p>
      </div>
      <form className="panel flex flex-col gap-3 p-4 md:flex-row" onSubmit={submit}>
        <input
          className="h-11 flex-1 border border-line px-3 outline-none focus:border-teal"
          style={{ borderRadius: 8 }}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          disabled={!result}
        />
        <button type="submit" className="command-button" disabled={loading || !result}>
          <SendHorizontal className="h-4 w-4" />
          Ask
        </button>
      </form>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
        <pre className="panel min-h-[420px] whitespace-pre-wrap p-5 text-sm leading-6 text-slate-800">
          {forensic?.answer ?? "Run an agent trace, then ask the investigator."}
        </pre>
        <div className="panel p-4">
          <h2 className="text-sm font-semibold uppercase text-slate-500">MCP Calls</h2>
          <div className="mt-3 space-y-2">
            {(forensic?.mcp_calls ?? []).map((call, index) => (
              <div key={index} className="border border-line bg-slate-50 p-3 text-sm" style={{ borderRadius: 8 }}>
                <div className="flex items-center justify-between gap-2">
                  <strong>{String(call.tool)}</strong>
                  <span className="text-xs uppercase text-teal">{String(call.status)}</span>
                </div>
                <div className="mt-1 text-xs text-slate-500">{forensic?.mode}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
