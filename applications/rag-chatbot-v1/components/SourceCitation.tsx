"use client";

import { useState } from "react";
import { SourceChunk } from "@/lib/types";

interface Props {
  sources: SourceChunk[];
}

export default function SourceCitation({ sources }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold uppercase tracking-wide">
        Sources ({sources.length}):
      </div>
      {sources.map((source, idx) => (
        <div key={source.chunk_id} className="text-xs">
          <button
            onClick={() =>
              setExpanded(expanded === source.chunk_id ? null : source.chunk_id)
            }
            className="flex items-center gap-2 text-left hover:underline"
          >
            <span className="font-mono">
              [{idx + 1}] {source.chunk_id.substring(0, 20)}...
            </span>
            <span className="text-green-600 dark:text-green-400">
              {(source.score * 100).toFixed(1)}%
            </span>
          </button>

          {expanded === source.chunk_id && source.text && (
            <div className="mt-1 ml-4 p-2 bg-white dark:bg-gray-800 rounded text-xs">
              {source.text.substring(0, 300)}
              {source.text.length > 300 && "..."}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
