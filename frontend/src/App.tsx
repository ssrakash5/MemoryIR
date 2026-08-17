import { AlertTriangle, BarChart3, Database, LayoutDashboard, Search, Shield, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import {
  AttributionReport,
  ForensicResponse,
  Intervention,
  Memory,
  QueryResult,
  SystemHealth,
  consolidate,
  createMemory,
  getHealth,
  getReport,
  investigate,
  listMemories,
  queryAgent,
  resetDemo,
  runInterventions
} from "./api";
import { Dashboard } from "./pages/Dashboard";
import { Evaluation } from "./pages/Evaluation";
import { Forensics } from "./pages/Forensics";
import { MemoryLab } from "./pages/MemoryLab";
import { PROTECTED_ACTION_QUERY, ProtectedAction } from "./pages/ProtectedAction";
import { TraceExplorer } from "./pages/TraceExplorer";

type Screen = "dashboard" | "action" | "lab" | "trace" | "forensics" | "evaluation";

const screens = [
  { id: "dashboard", label: "Dashboard", shortLabel: "Dashboard", icon: LayoutDashboard },
  { id: "action", label: "Protected Action Review", shortLabel: "Action", icon: AlertTriangle },
  { id: "lab", label: "Memory Lab", shortLabel: "Memory", icon: Database },
  { id: "trace", label: "Agent Trace", shortLabel: "Trace", icon: Search },
  { id: "forensics", label: "Forensic Investigator", shortLabel: "Forensics", icon: ShieldCheck },
  { id: "evaluation", label: "Quality Benchmarks", shortLabel: "Quality", icon: BarChart3 }
] satisfies Array<{ id: Screen; label: string; shortLabel: string; icon: typeof LayoutDashboard }>;

export default function App() {
  const [screen, setScreen] = useState<Screen>("dashboard");
  const [memories, setMemories] = useState<Memory[]>([]);
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [interventions, setInterventions] = useState<Intervention[]>([]);
  const [report, setReport] = useState<AttributionReport | null>(null);
  const [forensic, setForensic] = useState<ForensicResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);

  useEffect(() => {
    refreshMemories();
    getHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
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
    <div className="flex min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-30 flex w-[96px] flex-col items-center gap-1 border-r border-line bg-bg/90 py-5 backdrop-blur">
        <button type="button" onClick={() => setScreen("dashboard")} className="mb-5 flex flex-col items-center gap-1.5" title="MemoryIR">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-teal to-[#4f3fd8] text-white shadow-lg shadow-teal/30">
            <Shield className="h-5 w-5" />
          </span>
          <span className="text-[11px] font-bold tracking-tight text-white">MemoryIR</span>
        </button>
        <nav className="flex flex-1 flex-col items-center gap-1.5">
          {screens.map(({ id, label, shortLabel, icon: Icon }) => (
            <button
              key={id}
              type="button"
              title={label}
              onClick={() => setScreen(id)}
              className={`flex w-[80px] flex-col items-center gap-1 py-2 transition ${
                screen === id ? "text-teal" : "text-slate-500 hover:text-slate-200"
              }`}
              style={{ borderRadius: 10 }}
            >
              <span
                className={`flex h-9 w-9 items-center justify-center rounded-xl ${
                  screen === id ? "bg-teal text-white shadow-md shadow-teal/30" : ""
                }`}
              >
                <Icon className="h-[18px] w-[18px]" />
              </span>
              <span className="whitespace-nowrap text-[10px] font-semibold leading-none">{shortLabel}</span>
            </button>
          ))}
        </nav>
        <HealthDot health={health} />
      </aside>

      <div className="flex-1 pl-[96px]">
        {error ? (
          <div className="mx-auto max-w-7xl px-6 pt-5">
            <div className="border border-rose/40 bg-rose/10 p-3 text-sm text-rose" style={{ borderRadius: 10 }}>
              {error}
            </div>
          </div>
        ) : null}

        <main className="mx-auto max-w-7xl px-6 py-7">
          {screen === "dashboard" ? <Dashboard onOpenAction={launch} health={health} /> : null}
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
    </div>
  );
}

function HealthDot({ health }: { health: SystemHealth | null }) {
  const live = !!health && health.provider !== "mock";
  const label = !health ? "Connecting…" : live ? `Live · ${health.provider} + ${health.database_backend}` : "Sandbox mode (mock provider)";
  return (
    <div className="group relative flex items-center justify-center pb-1" title={label}>
      <span className={`h-2.5 w-2.5 rounded-full ${live ? "bg-emerald shadow-[0_0_8px_1px_rgba(47,212,128,0.7)]" : "bg-slate-500"}`} />
    </div>
  );
}
