import { SendHorizontal, ShieldCheck } from "lucide-react";
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
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-white">Forensic Investigator</h1>
          <p className="text-sm text-slate-400">CockroachDB Managed MCP forensic console.</p>
        </div>
        <span className="inline-flex items-center gap-1.5 border border-emerald/40 bg-emerald/10 px-2.5 py-1 text-xs font-semibold text-emerald" style={{ borderRadius: 999 }}>
          <ShieldCheck className="h-3.5 w-3.5" />
          Connected to CockroachDB Managed MCP
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="panel flex min-h-[480px] flex-col p-0">
          <div className="flex-1 space-y-4 overflow-y-auto p-5">
            {result ? (
              <ChatBubble align="right" text={`Why was ${result.decision === "COCKROACHDB" ? "M7" : "the claimed memory"} considered influential?`} />
            ) : null}
            <ChatBubblePanel>
              {forensic?.answer ?? "Evaluate a protected action first, then ask the investigator why a memory mattered."}
            </ChatBubblePanel>
          </div>
          <form className="flex items-center gap-2 border-t border-line p-3" onSubmit={submit}>
            <input
              className="h-11 flex-1 border border-line bg-panel2 px-3 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-teal"
              style={{ borderRadius: 10 }}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask another question…"
              disabled={!result}
            />
            <button type="submit" className="command-button" disabled={loading || !result}>
              <SendHorizontal className="h-4 w-4" />
            </button>
          </form>
        </div>

        <div className="panel p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">MCP Calls</h2>
          <div className="mt-3 space-y-2">
            {(forensic?.mcp_calls ?? []).map((call, index) => (
              <div key={index} className="border border-line bg-panel2 p-3 text-sm" style={{ borderRadius: 10 }}>
                <div className="flex items-center justify-between gap-2">
                  <strong className="text-slate-200">{String(call.tool)}</strong>
                  <span className="text-xs uppercase text-teal">{String(call.status)}</span>
                </div>
                <div className="mt-1 text-xs text-slate-500">{forensic?.mode}</div>
              </div>
            ))}
            {!forensic ? <p className="text-xs text-slate-500">MCP calls will appear here once you ask a question.</p> : null}
          </div>
        </div>
      </div>
    </div>
  );
}

function ChatBubble({ align, text }: { align: "left" | "right"; text: string }) {
  return (
    <div className={`flex ${align === "right" ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] px-4 py-2.5 text-sm leading-6 ${
          align === "right" ? "bg-teal text-white" : "border border-line bg-panel2 text-slate-200"
        }`}
        style={{ borderRadius: 14 }}
      >
        {text}
      </div>
    </div>
  );
}

function ChatBubblePanel({ children }: { children: string }) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] whitespace-pre-wrap border border-line bg-panel2 px-4 py-3 text-sm leading-6 text-slate-300" style={{ borderRadius: 14 }}>
        {children}
      </div>
    </div>
  );
}
