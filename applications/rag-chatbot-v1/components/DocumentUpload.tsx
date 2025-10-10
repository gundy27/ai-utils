"use client";

import { useState } from "react";
import { apiClient } from "@/lib/api";
import { DocumentIngestResponse } from "@/lib/types";

interface Props {
  onUploadComplete: (doc: DocumentIngestResponse) => void;
}

export default function DocumentUpload({ onUploadComplete }: Props) {
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const handleFile = async (file: File) => {
    setUploading(true);
    try {
      const result = await apiClient.uploadDocument(file, {
        source: "ui_upload",
        uploaded_at: new Date().toISOString(),
      });
      onUploadComplete(result);
    } catch (error) {
      alert(`Upload failed: ${error}`);
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  return (
    <div className="w-full">
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
        />
        <label
          htmlFor="file-upload"
          className={uploading ? "cursor-not-allowed" : "cursor-pointer"}
        >
          {uploading ? (
            <div className="space-y-2">
              <div className="text-lg font-medium">Processing document...</div>
              <div className="text-sm text-gray-500">
                Extracting, chunking, and embedding
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="text-4xl">📄</div>
              <div className="text-lg font-medium">
                Drop a document or click to upload
              </div>
              <div className="text-sm text-gray-500">
                Supports TXT, PDF, DOCX, MD, CSV
              </div>
            </div>
          )}
        </label>
      </div>
    </div>
  );
}
