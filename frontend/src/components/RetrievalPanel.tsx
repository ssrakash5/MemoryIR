import type { RetrievedMemory } from "../api";

type Props = {
  retrieved: RetrievedMemory[];
};

export function RetrievalPanel({ retrieved }: Props) {
  return (
    <div className="panel p-4">
      <h2 className="text-sm font-semibold uppercase text-slate-500">Retrieval</h2>
      <div className="mt-3 space-y-2">
        {retrieved.map((memory) => (
          <div key={memory.memory_id} className="border border-line bg-slate-50 p-3" style={{ borderRadius: 8 }}>
            <div className="flex items-center justify-between gap-2">
              <strong className="text-sm">#{memory.retrieval_rank} {memory.display_id}</strong>
              <span className="text-xs tabular-nums text-slate-500">{memory.vector_distance.toFixed(3)}</span>
            </div>
            <p className="mt-2 line-clamp-3 text-sm leading-5 text-slate-700">{memory.content}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
