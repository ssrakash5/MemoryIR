import { Database, GitBranch, SquareCheckBig } from "lucide-react";
import type { Memory } from "../api";

type Props = {
  memory: Memory;
  selected?: boolean;
  onToggle?: (memoryId: string) => void;
};

export function MemoryCard({ memory, selected = false, onToggle }: Props) {
  const Icon = memory.memory_type === "consolidated" ? GitBranch : Database;
  return (
    <button
      type="button"
      onClick={() => onToggle?.(memory.memory_id)}
      className={`w-full border bg-white p-3 text-left transition ${
        selected ? "border-teal ring-2 ring-teal/20" : "border-line hover:border-teal"
      }`}
      style={{ borderRadius: 8 }}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="inline-flex min-w-0 items-center gap-2 text-sm font-semibold text-ink">
          <Icon className="h-4 w-4 flex-none text-teal" />
          <span className="truncate">{memory.display_id}</span>
        </span>
        {selected ? <SquareCheckBig className="h-4 w-4 flex-none text-teal" /> : null}
      </div>
      <p className="min-h-12 text-sm leading-5 text-slate-700">{memory.content}</p>
      <div className="mt-3 flex flex-wrap gap-2 text-[11px] font-semibold uppercase tracking-normal text-slate-500">
        <span>{memory.memory_type}</span>
        <span>Generation {memory.generation}</span>
      </div>
    </button>
  );
}
