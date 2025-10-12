"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { Settings, HealthStatus, Stats } from "@/lib/types";

interface Props {
  settings: Settings;
  onSettingsChange: (settings: Settings) => void;
}

export default function SystemView({ settings, onSettingsChange }: Props) {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadSystemInfo();
    const interval = setInterval(loadSystemInfo, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const loadSystemInfo = async () => {
    try {
      const [healthData, statsData] = await Promise.all([
        apiClient.checkHealth(),
        apiClient.getStats(),
      ]);
      setHealth(healthData);
      setStats(statsData);
    } catch (error) {
      console.error("Failed to load system info:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSettingChange = (key: keyof Settings, value: any) => {
    onSettingsChange({ ...settings, [key]: value });
  };

  return (
    <div className="h-full overflow-y-auto bg-white dark:bg-gray-800">
      <div className="max-w-4xl mx-auto p-8">
        <h1 className="text-3xl font-bold mb-8">System Configuration</h1>

        {/* Settings Panel */}
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6 mb-8">
          <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
            <span>⚙️</span>
            <span>Settings</span>
          </h2>

          <div className="space-y-6">
            {/* Model Selection */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Language Model
              </label>
              <select
                value={settings.model}
                onChange={(e) => handleSettingChange("model", e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="gpt-4o-mini">GPT-4o Mini (Fast, Cheap)</option>
                <option value="gpt-4o">GPT-4o (Balanced)</option>
                <option value="gpt-4">GPT-4 (Most Capable)</option>
                <option value="gpt-3.5-turbo">GPT-3.5 Turbo (Legacy)</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                Choose the model for chat responses
              </p>
            </div>

            {/* Top K Results */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Context Chunks (Top K): {settings.topK}
              </label>
              <input
                type="range"
                min="1"
                max="10"
                value={settings.topK}
                onChange={(e) =>
                  handleSettingChange("topK", parseInt(e.target.value))
                }
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>1 (Faster)</span>
                <span>10 (More Context)</span>
              </div>
            </div>

            {/* User ID */}
            <div>
              <label className="block text-sm font-medium mb-2">User ID</label>
              <input
                type="text"
                value={settings.userId}
                onChange={(e) => handleSettingChange("userId", e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="default_user"
              />
              <p className="text-xs text-gray-500 mt-1">
                Identifier for tracking sessions and documents
              </p>
            </div>

            {/* Streaming Toggle */}
            <div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.useStreaming}
                  onChange={(e) =>
                    handleSettingChange("useStreaming", e.target.checked)
                  }
                  className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                />
                <span className="text-sm font-medium">
                  Enable Streaming Responses
                </span>
              </label>
              <p className="text-xs text-gray-500 mt-1 ml-6">
                Stream responses in real-time for better UX and perceived
                performance
              </p>
            </div>
          </div>
        </div>

        {/* Health Status Panel */}
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
            <span>🏥</span>
            <span>Health Status</span>
          </h2>

          {isLoading ? (
            <div className="text-center py-8 text-gray-500">
              Loading system status...
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <HealthCard
                  label="API Gateway"
                  status={health?.api ?? false}
                  icon="🌐"
                />
                <HealthCard
                  label="Vector Store"
                  status={health?.vectorStore ?? false}
                  icon="🗄️"
                />
                <HealthCard
                  label="Parsers"
                  status={health?.parsers ?? false}
                  icon="📝"
                />
                <HealthCard
                  label="Embeddings"
                  status={health?.embeddings ?? false}
                  icon="🧮"
                />
              </div>

              {/* System Statistics */}
              {stats && (
                <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
                  <h3 className="text-lg font-semibold mb-4">
                    System Statistics
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    <StatCard
                      label="Total Vectors"
                      value={stats.vector_count.toLocaleString()}
                    />
                    <StatCard
                      label="Parsers Registered"
                      value={stats.parsers_registered}
                    />
                    <StatCard
                      label="Max Chunk Tokens"
                      value={stats.chunk_max_tokens}
                    />
                    <StatCard
                      label="Embedding Model"
                      value={stats.embedding_model}
                      small
                    />
                    <StatCard
                      label="Dimensions"
                      value={stats.embedding_dimensions}
                    />
                    <StatCard
                      label="File Types"
                      value={stats.supported_file_types.length}
                    />
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function HealthCard({
  label,
  status,
  icon,
}: {
  label: string;
  status: boolean;
  icon: string;
}) {
  return (
    <div
      className={`p-4 rounded-lg border-2 ${
        status
          ? "bg-green-50 dark:bg-green-900/20 border-green-500"
          : "bg-red-50 dark:bg-red-900/20 border-red-500"
      }`}
    >
      <div className="flex items-center gap-3">
        <span className="text-2xl">{icon}</span>
        <div>
          <div className="font-medium">{label}</div>
          <div
            className={`text-sm font-semibold ${
              status
                ? "text-green-700 dark:text-green-400"
                : "text-red-700 dark:text-red-400"
            }`}
          >
            {status ? "Healthy" : "Offline"}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  small = false,
}: {
  label: string;
  value: string | number;
  small?: boolean;
}) {
  return (
    <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
        {label}
      </div>
      <div
        className={`font-semibold ${small ? "text-sm" : "text-lg"} truncate`}
      >
        {value}
      </div>
    </div>
  );
}
