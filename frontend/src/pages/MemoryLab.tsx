import { GitMerge, Plus, RotateCcw } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import type { Memory } from "../api";
import { MemoryCard } from "../components/MemoryCard";
import { MemoryGraph } from "../components/MemoryGraph";

type Props = {
  memories: Memory[];
  loading: boolean;
  onReset: () => Promise<void>;
  onAdd: (content: string) => Promise<void>;
  onConsolidate: (memoryIds: string[]) => Promise<void>;
};

export function MemoryLab({ memories, loading, onReset, onAdd, onConsolidate }: Props) {
  const defaultSelection = useMemo(
    () => memories.filter((memory) => ["M1", "M2", "M3"].includes(memory.display_id)).map((memory) => memory.memory_id),
    [memories]
  );
  const [selected, setSelected] = useState<string[]>(defaultSelection);
  const [content, setContent] = useState("");

  function toggle(memoryId: string) {
    setSelected((current) =>
      current.includes(memoryId) ? current.filter((id) => id !== memoryId) : [...current, memoryId]
    );
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!content.trim()) return;
    await onAdd(content.trim());
    setContent("");
  }

  const raw = memories.filter((memory) => memory.generation === 0);
  const derived = memories.filter((memory) => memory.generation > 0);
  const activeSelection = selected.length ? selected : defaultSelection;

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(360px,520px)]">
      <section className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-ink">Memory Lab</h1>
            <p className="text-sm text-slate-600">Ground memories and derived-memory lineage.</p>
          </div>
          <div className="flex gap-2">
            <button type="button" className="secondary-button" onClick={onReset} disabled={loading}>
              <RotateCcw className="h-4 w-4" />
              Reset
            </button>
            <button
              type="button"
              className="command-button"
              onClick={() => onConsolidate(activeSelection)}
              disabled={loading || activeSelection.length === 0}
            >
              <GitMerge className="h-4 w-4" />
              Consolidate
            </button>
          </div>
        </div>

        <form className="panel flex flex-col gap-3 p-4 md:flex-row" onSubmit={submit}>
          <textarea
            className="min-h-20 flex-1 resize-none border border-line bg-white p-3 text-sm outline-none focus:border-teal"
            style={{ borderRadius: 8 }}
            value={content}
            onChange={(event) => setContent(event.target.value)}
            placeholder="Add a raw memory"
          />
          <button type="submit" className="command-button self-start" disabled={loading}>
            <Plus className="h-4 w-4" />
            Add
          </button>
        </form>

        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase text-slate-500">Ground Memories</h2>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {raw.map((memory) => (
              <MemoryCard
                key={memory.memory_id}
                memory={memory}
                selected={activeSelection.includes(memory.memory_id)}
                onToggle={toggle}
              />
            ))}
          </div>
        </div>

        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase text-slate-500">Derived Memories</h2>
          <div className="grid gap-3 md:grid-cols-2">
            {derived.map((memory) => (
              <MemoryCard key={memory.memory_id} memory={memory} />
            ))}
          </div>
        </div>
      </section>

      <section className="panel p-4">
        <h2 className="mb-3 text-sm font-semibold uppercase text-slate-500">Lineage Graph</h2>
        <MemoryGraph memories={memories} highlighted={["M2", "M7"]} />
      </section>
    </div>
  );
}
