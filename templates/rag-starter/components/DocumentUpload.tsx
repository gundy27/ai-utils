"use client";

import { useState } from "react";
import { apiClient } from "@/lib/api";
import { DocumentIngestResponse } from "@/lib/types";

interface FileStatus {
  file: File;
  status: "pending" | "processing" | "success" | "failed";
  result?: DocumentIngestResponse;
  error?: string;
}

interface Props {
  onUploadComplete: (doc: DocumentIngestResponse) => void;
  userId?: string;
}

export default function DocumentUpload({
  onUploadComplete,
  userId = "web_user",
}: Props) {
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [fileStatuses, setFileStatuses] = useState<FileStatus[]>([]);
  const [currentFileIndex, setCurrentFileIndex] = useState(0);

  const handleFiles = async (files: FileList) => {
    const fileArray = Array.from(files);
    const initialStatuses: FileStatus[] = fileArray.map((file) => ({
      file,
      status: "pending",
    }));

    setFileStatuses(initialStatuses);
    setCurrentFileIndex(0);
    setUploading(true);

    // Process files sequentially
    for (let i = 0; i < fileArray.length; i++) {
      setCurrentFileIndex(i);

      // Update status to processing
      setFileStatuses((prev) =>
        prev.map((fs, idx) =>
          idx === i ? { ...fs, status: "processing" } : fs,
        ),
      );

      try {
        const result = await apiClient.uploadDocument(
          fileArray[i],
          {
            source: "ui_upload",
            uploaded_at: new Date().toISOString(),
          },
          userId,
        );

        // Update status to success
        setFileStatuses((prev) =>
          prev.map((fs, idx) =>
            idx === i ? { ...fs, status: "success", result } : fs,
          ),
        );

        onUploadComplete(result);
      } catch (error) {
        // Update status to failed
        setFileStatuses((prev) =>
          prev.map((fs, idx) =>
            idx === i ? { ...fs, status: "failed", error: String(error) } : fs,
          ),
        );
      }
    }

    setUploading(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
    }
  };

  const clearStatuses = () => {
    setFileStatuses([]);
    setCurrentFileIndex(0);
  };

  const successCount = fileStatuses.filter(
    (fs) => fs.status === "success",
  ).length;
  const failedCount = fileStatuses.filter(
    (fs) => fs.status === "failed",
  ).length;

  return (
    <div className="w-full space-y-4">
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          dragActive
            ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
            : "border-gray-300 dark:border-gray-600"
        } ${uploading ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
        onDragEnter={() => setDragActive(true)}
        onDragLeave={() => setDragActive(false)}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        <input
          type="file"
          id="file-upload"
          className="hidden"
          onChange={handleChange}
          accept=".txt,.pdf,.docx,.md,.csv,.log"
          disabled={uploading}
          multiple
        />
        <label
          htmlFor="file-upload"
          className={uploading ? "cursor-not-allowed" : "cursor-pointer"}
        >
          {uploading ? (
            <div className="space-y-2">
              <div className="text-lg font-medium">
                Processing {currentFileIndex + 1} of {fileStatuses.length}...
              </div>
              <div className="text-sm text-gray-500">
                Extracting, chunking, and embedding
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="text-4xl">📄</div>
              <div className="text-lg font-medium">
                Drop documents or click to upload
              </div>
              <div className="text-sm text-gray-500">
                Supports TXT, PDF, DOCX, MD, CSV • Multiple files supported
              </div>
            </div>
          )}
        </label>
      </div>

      {/* Progress and Status Display */}
      {fileStatuses.length > 0 && (
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-semibold text-sm">
              Upload Progress ({successCount + failedCount} /{" "}
              {fileStatuses.length})
            </h3>
            {!uploading && (
              <button
                onClick={clearStatuses}
                className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400"
              >
                Clear
              </button>
            )}
          </div>

          <div className="space-y-2 max-h-48 overflow-y-auto">
            {fileStatuses.map((fileStatus, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2 bg-white dark:bg-gray-800 rounded text-sm"
              >
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <span className="text-lg">
                    {fileStatus.status === "success" && "✅"}
                    {fileStatus.status === "failed" && "❌"}
                    {fileStatus.status === "processing" && "⏳"}
                    {fileStatus.status === "pending" && "⏸️"}
                  </span>
                  <span className="truncate font-medium">
                    {fileStatus.file.name}
                  </span>
                </div>
                <div className="text-xs text-gray-500 ml-2">
                  {fileStatus.status === "success" &&
                    fileStatus.result &&
                    `${fileStatus.result.chunks_created} chunks`}
                  {fileStatus.status === "failed" && "Failed"}
                  {fileStatus.status === "processing" && "Processing..."}
                  {fileStatus.status === "pending" && "Queued"}
                </div>
              </div>
            ))}
          </div>

          {/* Summary */}
          {!uploading && fileStatuses.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
              <div className="text-sm">
                <span className="text-green-600 dark:text-green-400 font-semibold">
                  ✅ {successCount} succeeded
                </span>
                {failedCount > 0 && (
                  <>
                    <span className="mx-2">•</span>
                    <span className="text-red-600 dark:text-red-400 font-semibold">
                      ❌ {failedCount} failed
                    </span>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
