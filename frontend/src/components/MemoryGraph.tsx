import { useMemo } from "react";
import ReactFlow, { Background, Controls, Edge, Node } from "reactflow";
import type { Memory } from "../api";

type Props = {
  memories: Memory[];
  highlighted?: string[];
};

export function MemoryGraph({ memories, highlighted = [] }: Props) {
  const { nodes, edges } = useMemo(() => buildGraph(memories, highlighted), [memories, highlighted]);
  return (
    <div className="h-[420px] min-h-[320px] overflow-hidden border border-line bg-slate-50" style={{ borderRadius: 8 }}>
      <ReactFlow nodes={nodes} edges={edges} fitView proOptions={{ hideAttribution: true }}>
        <Background color="#cbd5e1" gap={18} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

function buildGraph(memories: Memory[], highlighted: string[]): { nodes: Node[]; edges: Edge[] } {
  const byId = new Map(memories.map((memory) => [memory.memory_id, memory]));
  const byDisplay = new Map(memories.map((memory) => [memory.display_id, memory]));
  const edges: Edge[] = [];
  memories.forEach((memory) => {
    const inputIds = Array.isArray(memory.metadata.input_memory_ids)
      ? (memory.metadata.input_memory_ids as string[])
      : [];
    inputIds.forEach((parentId) => {
      if (byId.has(parentId)) {
        edges.push(edge(parentId, memory.memory_id));
      }
    });
  });

  const demoParents = ["M1", "M2", "M3"];
  const demoChild = byDisplay.get("M7");
  if (demoChild && edges.length === 0) {
    demoParents.forEach((displayId) => {
      const parent = byDisplay.get(displayId);
      if (parent) {
        edges.push(edge(parent.memory_id, demoChild.memory_id));
      }
    });
  }

  const generations = new Map<number, Memory[]>();
  memories.forEach((memory) => {
    generations.set(memory.generation, [...(generations.get(memory.generation) ?? []), memory]);
  });
  const nodes: Node[] = [];
  [...generations.entries()].forEach(([generation, group]) => {
    group
      .sort((left, right) => left.display_id.localeCompare(right.display_id, undefined, { numeric: true }))
      .forEach((memory, index) => {
        const isHot = highlighted.includes(memory.display_id) || highlighted.includes(memory.memory_id);
        nodes.push({
          id: memory.memory_id,
          position: { x: generation * 280, y: index * 105 + (generation % 2) * 35 },
          data: {
            label: (
              <div className="w-[190px]">
                <div className="flex items-center justify-between gap-2">
                  <strong>{memory.display_id}</strong>
                  <span className="text-[10px] uppercase text-slate-500">{memory.memory_type}</span>
                </div>
                <div className="mt-1 line-clamp-3 text-xs leading-4 text-slate-600">{memory.content}</div>
              </div>
            )
          },
          style: {
            border: `1px solid ${isHot ? "#0f766e" : "#cbd5e1"}`,
            background: isHot ? "#ecfdf5" : "#ffffff",
            borderRadius: 8,
            color: "#111827",
            padding: 10,
            width: 210
          }
        });
      });
  });
  return { nodes, edges };
}

function edge(source: string, target: string): Edge {
  return {
    id: `${source}-${target}`,
    source,
    target,
    animated: true,
    style: { stroke: "#0f766e", strokeWidth: 2 }
  };
}
