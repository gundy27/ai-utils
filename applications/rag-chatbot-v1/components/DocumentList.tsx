"use client";

import { useState, useEffect } from "react";
import { apiClient } from "@/lib/api";

interface Document {
  id: string;
  name: string;
  user_id: string;
  uploaded_at: string;
  status: string;
  chunks_count: number;
  file_size?: number;
  file_type?: string;
}

interface Props {
  refreshTrigger?: number;
  onDelete?: () => void;
}

export default function DocumentList({ refreshTrigger, onDelete }: Props) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    loadDocuments();
  }, [refreshTrigger]);

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const data = await apiClient.listDocuments("anonymous");
      setDocuments(data.documents || []);
    } catch (error) {
      console.error("Failed to load documents:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (docId: string, docName: string) => {
    if (
      !confirm(
        `Delete "${docName}"?\n\nThis will remove the document and all its vectors from the database.`,
      )
    ) {
      return;
    }

    setDeleting(docId);
    try {
      await apiClient.deleteDocument(docId);
      await loadDocuments();
      onDelete?.();
    } catch (error) {
      alert(`Delete failed: ${error}`);
    } finally {
      setDeleting(null);
    }
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return "Unknown size";
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    const mb = kb / 1024;
    return `${mb.toFixed(1)} MB`;
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString() + " " + date.toLocaleTimeString();
  };

  if (loading) {
    return (
      <div className="p-4 text-center text-gray-500">
        <div className="animate-spin text-2xl mb-2">⟳</div>
        <div className="text-sm">Loading documents...</div>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-semibold text-lg">
          Documents ({documents.length})
        </h3>
        <button
          onClick={loadDocuments}
          className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400"
        >
          ↻ Refresh
        </button>
      </div>

      {documents.length === 0 ? (
        <div className="text-center text-gray-500 py-8">
          <div className="text-4xl mb-2">📭</div>
          <div className="text-sm">No documents uploaded yet</div>
        </div>
      ) : (
        <div className="space-y-2 max-h-[400px] overflow-y-auto">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow"
            >
              <div className="flex justify-between items-start gap-2">
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate" title={doc.name}>
                    {doc.name}
                  </div>
                  <div className="text-xs text-gray-500 mt-1 space-y-1">
                    <div>
                      <span className="font-mono bg-gray-100 dark:bg-gray-700 px-1 rounded">
                        {doc.id.substring(0, 16)}...
                      </span>
                    </div>
                    <div>
                      {doc.chunks_count} chunks • {doc.file_type || "unknown"}
                    </div>
                    <div>{formatFileSize(doc.file_size)}</div>
                    <div className="text-gray-400">
                      {formatDate(doc.uploaded_at)}
                    </div>
                  </div>
                  <div className="mt-2">
                    <span
                      className={`inline-block px-2 py-0.5 text-xs rounded ${
                        doc.status === "completed"
                          ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                          : doc.status === "processing"
                            ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400"
                            : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
                      }`}
                    >
                      {doc.status}
                    </span>
                  </div>
                </div>

                <button
                  onClick={() => handleDelete(doc.id, doc.name)}
                  disabled={deleting === doc.id}
                  className="px-3 py-1 text-sm text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Delete document"
                >
                  {deleting === doc.id ? "..." : "🗑️"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
