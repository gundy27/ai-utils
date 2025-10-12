"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { Stats } from "@/lib/types";

interface Props {
  totalCost: number;
  totalTokens: number;
  totalMessages: number;
}

export default function StatsPanel({
  totalCost,
  totalTokens,
  totalMessages,
}: Props) {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    loadStats();
    const interval = setInterval(loadStats, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const loadStats = async () => {
    try {
      const data = await apiClient.getStats();
      setStats(data);
    } catch (error) {
      console.error("Failed to load stats:", error);
      // Set default stats on error to prevent UI from breaking
      setStats({
        vector_count: 0,
        parsers_registered: 0,
        supported_file_types: [],
        chunk_max_tokens: 512,
        embedding_model: "unknown",
        embedding_dimensions: 1536,
      });
    }
  };

  return (
    <div className="h-full bg-gray-50 dark:bg-gray-900 border-l border-gray-200 dark:border-gray-700 p-4 overflow-y-auto">
      <h2 className="text-xl font-bold mb-6">Analytics</h2>

      <div className="space-y-6">
        {/* Session Stats */}
        <div>
          <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
            Session
          </h3>
          <div className="space-y-2">
            <StatItem label="Messages" value={totalMessages} />
            <StatItem
              label="Total Tokens"
              value={totalTokens.toLocaleString()}
            />
            <StatItem
              label="Total Cost"
              value={`$${totalCost.toFixed(6)}`}
              highlight
            />
          </div>
        </div>

        {/* System Stats */}
        {stats && (
          <div>
            <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
              System
            </h3>
            <div className="space-y-2">
              <StatItem
                label="Vectors"
                value={stats.vector_count.toLocaleString()}
              />
              <StatItem
                label="Embedding Model"
                value={stats.embedding_model}
                small
              />
              <StatItem
                label="Dimensions"
                value={stats.embedding_dimensions.toLocaleString()}
              />
              <StatItem
                label="Supported Types"
                value={stats.supported_file_types.join(", ")}
                small
              />
            </div>
          </div>
        )}

        {/* Pipeline Info */}
        {stats && (
          <div>
            <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
              Pipeline
            </h3>
            <div className="space-y-2">
              <StatItem label="Parsers" value={stats.parsers_registered} />
              <StatItem
                label="Max Chunk Tokens"
                value={stats.chunk_max_tokens}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatItem({
  label,
  value,
  highlight = false,
  small = false,
}: {
  label: string;
  value: string | number;
  highlight?: boolean;
  small?: boolean;
}) {
  return (
    <div
      className={`p-3 rounded-lg ${
        highlight
          ? "bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700"
          : "bg-white dark:bg-gray-800"
      }`}
    >
      <div className="text-xs text-gray-500 dark:text-gray-400">{label}</div>
      <div
        className={`font-semibold ${
          small ? "text-sm" : "text-lg"
        } ${highlight ? "text-blue-700 dark:text-blue-300" : ""}`}
      >
        {value}
      </div>
    </div>
  );
}
