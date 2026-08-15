import { Play, ShieldCheck } from "lucide-react";

type Props = {
  onLaunch: () => void;
};

export function Home({ onLaunch }: Props) {
  return (
    <section className="grid min-h-[calc(100vh-96px)] place-items-center px-4 py-10">
      <div className="w-full max-w-5xl border border-ink bg-white p-8 shadow-sm" style={{ borderRadius: 8 }}>
        <div className="flex flex-col gap-8 md:flex-row md:items-end md:justify-between">
          <div className="max-w-2xl">
            <div className="mb-4 inline-flex items-center gap-2 border border-line bg-panel px-3 py-1 text-sm font-semibold text-teal" style={{ borderRadius: 8 }}>
              <ShieldCheck className="h-4 w-4" />
              MemoryIR
            </div>
            <h1 className="text-4xl font-semibold tracking-normal text-ink md:text-6xl">MemoryIR</h1>
            <p className="mt-4 text-xl leading-8 text-slate-700">
              Stop unsafe agent actions before they modify important data.
            </p>
            <p className="mt-3 text-2xl font-medium leading-9 text-ink">
              MemoryIR proves which persistent memories caused the decision, then blocks the risky write.
            </p>
          </div>
          <button type="button" className="command-button w-fit" onClick={onLaunch}>
            <Play className="h-4 w-4" />
            Launch Protected Demo
          </button>
        </div>
        <div className="mt-8 grid gap-3 border-t border-line pt-6 text-sm font-semibold text-slate-600 md:grid-cols-3">
          <span>CockroachDB Vector Index</span>
          <span>Managed MCP</span>
          <span>AWS Lambda</span>
        </div>
      </div>
    </section>
  );
}
