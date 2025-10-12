"use client";

import { useState, useEffect } from "react";
import { apiClient } from "@/lib/api";
import DocumentUpload from "@/components/DocumentUpload";
import { DocumentIngestResponse } from "@/lib/types";

interface Document {
  id: string;
  name: string;
  uploaded_at: string;
  status: string;
  chunks_count: number;
  file_size?: number;
  file_type?: string;
}

interface Props {
  onUploadComplete?: (doc: DocumentIngestResponse) => void;
  userId?: string;
}

export default function DocumentsView({
  onUploadComplete,
  userId = "web_user",
}: Props) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);

  useEffect(() => {
    loadDocuments();
  }, [userId]);

  const loadDocuments = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.listDocuments(userId);
      setDocuments(data.documents || []);
    } catch (err) {
      console.error("Failed to load documents:", err);
      setError("Failed to load documents.");
    } finally {
      setIsLoading(false);
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

    try {
      await apiClient.deleteDocument(docId);
      loadDocuments();
    } catch (err) {
      console.error("Failed to delete document:", err);
      alert("Failed to delete document. Please check console for details.");
    }
  };

  const handleUploadComplete = (doc: DocumentIngestResponse) => {
    setShowUpload(false);
    loadDocuments();
    onUploadComplete?.(doc);
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return "N/A";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="h-full overflow-y-auto bg-white dark:bg-gray-800">
      <div className="max-w-6xl mx-auto p-8">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">Document Management</h1>
          <button
            onClick={() => setShowUpload(!showUpload)}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition-colors flex items-center gap-2"
          >
            <span>{showUpload ? "−" : "+"}</span>
            <span>{showUpload ? "Hide Upload" : "Upload Document"}</span>
          </button>
        </div>

        {/* Upload Section */}
        {showUpload && (
          <div className="mb-8">
            <DocumentUpload
              onUploadComplete={handleUploadComplete}
              userId={userId}
            />
          </div>
        )}

        {/* Documents List */}
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <span>📄</span>
              <span>Uploaded Documents ({documents.length})</span>
            </h2>
            <button
              onClick={loadDocuments}
              className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-200 flex items-center gap-1"
              title="Refresh document list"
            >
              <span>↻</span>
              <span>Refresh</span>
            </button>
          </div>

          {isLoading ? (
            <div className="text-center py-12 text-gray-500">
              Loading documents...
            </div>
          ) : error ? (
            <div className="text-center py-12 text-red-500">{error}</div>
          ) : documents.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-4xl mb-4">📭</div>
              <div className="text-gray-500">
                No documents uploaded yet. Upload one to get started!
              </div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700">
                    <th className="text-left py-3 px-4 font-semibold text-sm">
                      Name
                    </th>
                    <th className="text-left py-3 px-4 font-semibold text-sm">
                      Type
                    </th>
                    <th className="text-left py-3 px-4 font-semibold text-sm">
                      Size
                    </th>
                    <th className="text-left py-3 px-4 font-semibold text-sm">
                      Chunks
                    </th>
                    <th className="text-left py-3 px-4 font-semibold text-sm">
                      Uploaded
                    </th>
                    <th className="text-left py-3 px-4 font-semibold text-sm">
                      Status
                    </th>
                    <th className="text-right py-3 px-4 font-semibold text-sm">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((doc) => (
                    <tr
                      key={doc.id}
                      className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                    >
                      <td className="py-4 px-4">
                        <div className="font-medium">{doc.name}</div>
                        <div className="text-xs text-gray-500 mt-0.5">
                          {doc.id.substring(0, 8)}...
                        </div>
                      </td>
                      <td className="py-4 px-4 text-sm">
                        {doc.file_type || "unknown"}
                      </td>
                      <td className="py-4 px-4 text-sm">
                        {formatFileSize(doc.file_size)}
                      </td>
                      <td className="py-4 px-4 text-sm">{doc.chunks_count}</td>
                      <td className="py-4 px-4 text-sm text-gray-500">
                        {new Date(doc.uploaded_at).toLocaleDateString()}
                        <br />
                        <span className="text-xs">
                          {new Date(doc.uploaded_at).toLocaleTimeString()}
                        </span>
                      </td>
                      <td className="py-4 px-4">
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-semibold ${
                            doc.status === "completed"
                              ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                              : doc.status === "processing"
                                ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400"
                                : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
                          }`}
                        >
                          {doc.status}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-right">
                        <button
                          onClick={() => handleDelete(doc.id, doc.name)}
                          className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-200 text-sm font-medium"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
