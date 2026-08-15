import { AlertTriangle, BarChart3, Database, GitBranch, Home as HomeIcon, Search, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import {
  AttributionReport,
  ForensicResponse,
  Intervention,
  Memory,
  QueryResult,
  consolidate,
  createMemory,
  getReport,
  investigate,
  listMemories,
  queryAgent,
  resetDemo,
  runInterventions
} from "./api";
import { Evaluation } from "./pages/Evaluation";
import { Forensics } from "./pages/Forensics";
import { Home } from "./pages/Home";
import { MemoryLab } from "./pages/MemoryLab";
import { PROTECTED_ACTION_QUERY, ProtectedAction } from "./pages/ProtectedAction";
import { TraceExplorer } from "./pages/TraceExplorer";

type Screen = "home" | "action" | "lab" | "trace" | "forensics" | "evaluation";

const screens = [
  { id: "home", label: "Home", icon: HomeIcon },
  { id: "action", label: "Protected Action", icon: AlertTriangle },
  { id: "lab", label: "Memory Lab", icon: Database },
  { id: "trace", label: "Agent Trace", icon: Search },
  { id: "forensics", label: "Forensics", icon: ShieldCheck },
  { id: "evaluation", label: "Evaluation", icon: BarChart3 }
] satisfies Array<{ id: Screen; label: string; icon: typeof HomeIcon }>;

export default function App() {
  const [screen, setScreen] = useState<Screen>("home");
  const [memories, setMemories] = useState<Memory[]>([]);
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [interventions, setInterventions] = useState<Intervention[]>([]);
  const [report, setReport] = useState<AttributionReport | null>(null);
  const [forensic, setForensic] = useState<ForensicResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    refreshMemories();
  }, []);

  async function withLoading(work: () => Promise<void>) {
    setLoading(true);
    setError(null);
    try {
      await work();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  async function refreshMemories() {
    await withLoading(async () => {
      setMemories(await listMemories());
    });
  }

  async function handleReset() {
    await withLoading(async () => {
      const result = await resetDemo();
      setMemories(result.memories);
      setQueryResult(null);
      setInterventions([]);
      setReport(null);
      setForensic(null);
    });
  }

  async function handleAdd(content: string) {
    await withLoading(async () => {
      await createMemory(content);
      setMemories(await listMemories());
    });
  }

  async function handleConsolidate(memoryIds: string[]) {
    await withLoading(async () => {
      await consolidate(memoryIds);
      setMemories(await listMemories());
    });
  }

  async function handleQuery(query: string, nextScreen: Screen = "trace") {
    await withLoading(async () => {
      const result = await queryAgent(query, 3);
      setQueryResult(result);
      setInterventions([]);
      setReport(null);
      setForensic(null);
      setScreen(nextScreen);
    });
  }

  async function handleInvestigate() {
    if (!queryResult) return;
    await withLoading(async () => {
      const runs = await runInterventions(queryResult.trace_id);
      const nextReport = await getReport(queryResult.trace_id);
      setInterventions(runs);
      setReport(nextReport);
    });
  }

  async function handleForensics(question: string) {
    if (!queryResult) return;
    await withLoading(async () => {
      const response = await investigate(queryResult.trace_id, question);
      setForensic(response);
    });
  }

  function launch() {
    setScreen("action");
    if (memories.length === 0) {
      void handleReset();
    }
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-line bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 md:flex-row md:items-center md:justify-between">
          <button type="button" className="flex items-center gap-3 text-left" onClick={() => setScreen("home")}>
            <div className="icon-button">
              <GitBranch className="h-4 w-4" />
            </div>
            <div>
              <div className="text-sm font-semibold uppercase text-slate-500">MemoryIR</div>
              <div className="text-base font-semibold text-ink">Forensics for persistent AI memory</div>
            </div>
          </button>
          <nav className="flex flex-wrap gap-2">
            {screens.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                className={`secondary-button ${screen === id ? "border-teal text-teal" : ""}`}
                onClick={() => setScreen(id)}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {error ? (
        <div className="mx-auto mt-4 max-w-7xl px-4">
          <div className="border border-rose bg-rose-50 p-3 text-sm text-rose" style={{ borderRadius: 8 }}>
            {error}
          </div>
        </div>
      ) : null}

      <main className="mx-auto max-w-7xl px-4 py-6">
        {screen === "home" ? <Home onLaunch={launch} /> : null}
        {screen === "action" ? (
          <ProtectedAction
            result={queryResult}
            interventions={interventions}
            report={report}
            loading={loading}
            onAttempt={() => handleQuery(PROTECTED_ACTION_QUERY, "action")}
            onGuard={handleInvestigate}
            onOpenTrace={() => setScreen("trace")}
            onOpenForensics={() => setScreen("forensics")}
          />
        ) : null}
        {screen === "lab" ? (
          <MemoryLab
            memories={memories}
            loading={loading}
            onReset={handleReset}
            onAdd={handleAdd}
            onConsolidate={handleConsolidate}
          />
        ) : null}
        {screen === "trace" ? (
          <TraceExplorer
            memories={memories}
            result={queryResult}
            interventions={interventions}
            report={report}
            loading={loading}
            onQuery={(query) => handleQuery(query)}
            onInvestigate={handleInvestigate}
          />
        ) : null}
        {screen === "forensics" ? (
          <Forensics
            result={queryResult}
            forensic={forensic}
            loading={loading}
            onInvestigate={handleForensics}
          />
        ) : null}
        {screen === "evaluation" ? <Evaluation /> : null}
      </main>
    </div>
  );
}
