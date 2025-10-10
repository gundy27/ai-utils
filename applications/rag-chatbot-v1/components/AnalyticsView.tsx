"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { Stats } from "@/lib/types";

interface Props {
  totalCost: number;
  totalTokens: number;
  totalMessages: number;
}

export default function AnalyticsView({
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
    <div className="h-full overflow-y-auto bg-white dark:bg-gray-800">
      <div className="max-w-6xl mx-auto p-8">
        <h1 className="text-3xl font-bold mb-8">Analytics Dashboard</h1>

        {/* Session Statistics */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <span>📊</span>
            <span>Session Statistics</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <StatCard
              label="Total Messages"
              value={totalMessages}
              icon="💬"
              color="blue"
            />
            <StatCard
              label="Total Tokens"
              value={totalTokens.toLocaleString()}
              icon="🎯"
              color="purple"
            />
            <StatCard
              label="Total Cost"
              value={`$${totalCost.toFixed(6)}`}
              icon="💰"
              color="green"
              highlight
            />
          </div>
        </div>

        {/* System Statistics */}
        {stats && (
          <div className="mb-8">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <span>⚡</span>
              <span>System Performance</span>
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard
                label="Vector Count"
                value={stats.vector_count.toLocaleString()}
                description="Total embeddings in database"
              />
              <MetricCard
                label="Parsers"
                value={stats.parsers_registered}
                description="Active document parsers"
              />
              <MetricCard
                label="Chunk Size"
                value={`${stats.chunk_max_tokens} tokens`}
                description="Maximum tokens per chunk"
              />
              <MetricCard
                label="Dimensions"
                value={stats.embedding_dimensions}
                description="Embedding vector size"
              />
            </div>
          </div>
        )}

        {/* Pipeline Information */}
        {stats && (
          <div>
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <span>🔧</span>
              <span>Pipeline Configuration</span>
            </h2>
            <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <InfoRow
                  label="Embedding Model"
                  value={stats.embedding_model}
                />
                <InfoRow
                  label="Supported File Types"
                  value={stats.supported_file_types.join(", ")}
                />
                <InfoRow
                  label="Parsers Registered"
                  value={`${stats.parsers_registered} active`}
                />
                <InfoRow label="Vector Database" value="ChromaDB" />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
  color,
  highlight = false,
}: {
  label: string;
  value: string | number;
  icon: string;
  color: "blue" | "purple" | "green";
  highlight?: boolean;
}) {
  const colorClasses = {
    blue: "bg-blue-50 dark:bg-blue-900/20 border-blue-500 text-blue-700 dark:text-blue-400",
    purple:
      "bg-purple-50 dark:bg-purple-900/20 border-purple-500 text-purple-700 dark:text-purple-400",
    green:
      "bg-green-50 dark:bg-green-900/20 border-green-500 text-green-700 dark:text-green-400",
  };

  return (
    <div
      className={`p-6 rounded-lg border-2 ${highlight ? "shadow-lg" : ""} ${colorClasses[color]}`}
    >
      <div className="flex items-center gap-3 mb-2">
        <span className="text-3xl">{icon}</span>
        <div className="text-sm font-medium opacity-80">{label}</div>
      </div>
      <div className="text-3xl font-bold">{value}</div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  description,
}: {
  label: string;
  value: string | number;
  description: string;
}) {
  return (
    <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
        {label}
      </div>
      <div className="text-2xl font-bold mb-1">{value}</div>
      <div className="text-xs text-gray-500">{description}</div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
        {label}
      </div>
      <div className="text-base font-semibold">{value}</div>
    </div>
  );
}
