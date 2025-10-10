"use client";

import { useState } from "react";
import DocumentUpload from "@/components/DocumentUpload";
import ChatInterface from "@/components/ChatInterface";
import SessionSidebar from "@/components/SessionSidebar";
import StatsPanel from "@/components/StatsPanel";
import DocumentList from "@/components/DocumentList";
import { apiClient } from "@/lib/api";
import { Session, Message, DocumentIngestResponse } from "@/lib/types";

export default function Home() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSession, setCurrentSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [totalCost, setTotalCost] = useState(0);
  const [totalTokens, setTotalTokens] = useState(0);
  const [showUpload, setShowUpload] = useState(true);
  const [documentRefresh, setDocumentRefresh] = useState(0);

  const handleNewSession = () => {
    const newSession: Session = {
      id: `new_${Date.now()}`,
      messages: [],
    };
    setSessions([newSession, ...sessions]);
    setCurrentSession(newSession);
  };

  const handleSelectSession = (sessionId: string) => {
    const session = sessions.find((s) => s.id === sessionId);
    if (session) {
      setCurrentSession(session);
    }
  };

  const handleUploadComplete = (doc: DocumentIngestResponse) => {
    setShowUpload(false);
    setDocumentRefresh((prev) => prev + 1); // Trigger document list refresh
    alert(
      `Document uploaded!\n\nID: ${doc.document_id}\nChunks: ${doc.chunks_created}\nTokens: ${doc.total_tokens}\nCost: $${doc.estimated_cost_usd.toFixed(6)}`,
    );
  };

  const handleDocumentDelete = () => {
    setDocumentRefresh((prev) => prev + 1); // Trigger document list refresh
  };

  const handleSendMessage = async (message: string) => {
    if (!currentSession) {
      handleNewSession();
    }

    const userMessage: Message = {
      role: "user",
      content: message,
    };

    // Add user message immediately
    const session = currentSession || sessions[0];
    const updatedSession = {
      ...session,
      messages: [...session.messages, userMessage],
    };
    setCurrentSession(updatedSession);
    setSessions(
      sessions.map((s) => (s.id === session.id ? updatedSession : s)),
    );

    setIsLoading(true);

    try {
      const response = await apiClient.chat(
        message,
        session.id.startsWith("new_") ? undefined : session.id,
        "web_user",
        5,
        "gpt-4o-mini",
        true,
      );

      const assistantMessage: Message = {
        role: "assistant",
        content: response.answer,
        sources: response.sources,
        tokens: response.tokens_used,
        cost: response.cost_usd,
      };

      // Update session with real session ID if it was new
      const finalSession = {
        id: response.session_id,
        messages: [...updatedSession.messages, assistantMessage],
        message_count: updatedSession.messages.length + 1,
      };

      setCurrentSession(finalSession);
      setSessions(
        sessions.map((s) => (s.id === session.id ? finalSession : s)),
      );

      // Update totals
      setTotalCost((prev) => prev + response.cost_usd);
      setTotalTokens((prev) => prev + response.tokens_used);
    } catch (error) {
      alert(`Chat failed: ${error}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="h-screen flex flex-col">
      {/* Header */}
      <header className="bg-blue-600 text-white p-4 shadow-lg">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold">RAG Chatbot v1</h1>
          <div className="text-sm">
            Powered by gundy-ai • Extract → Chunk → Embed → Store → Chat
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Session Sidebar */}
        <div className="w-64 hidden md:block">
          <SessionSidebar
            sessions={sessions}
            currentSessionId={currentSession?.id || null}
            onSelectSession={handleSelectSession}
            onNewSession={handleNewSession}
          />
        </div>

        {/* Chat Area */}
        <div className="flex-1 flex flex-col">
          <div className="border-b border-gray-200 dark:border-gray-700">
            <div className="p-4">
              <button
                onClick={() => setShowUpload(!showUpload)}
                className="text-sm font-medium text-blue-600 hover:text-blue-800 dark:text-blue-400"
              >
                {showUpload ? "− Hide Upload" : "+ Upload Document"}
              </button>
            </div>

            {showUpload && (
              <div className="px-4 pb-4">
                <DocumentUpload onUploadComplete={handleUploadComplete} />
              </div>
            )}

            {/* Document List */}
            <div className="border-t border-gray-200 dark:border-gray-700">
              <DocumentList
                refreshTrigger={documentRefresh}
                onDelete={handleDocumentDelete}
              />
            </div>
          </div>

          <div className="flex-1 overflow-hidden">
            {!currentSession ? (
              <div className="flex items-center justify-center h-full text-gray-500">
                <div className="text-center">
                  <div className="text-4xl mb-4">👋</div>
                  <div className="text-xl">Welcome to RAG Chatbot</div>
                  <div className="text-sm mt-2">
                    Upload a document and start chatting!
                  </div>
                  <button
                    onClick={handleNewSession}
                    className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                  >
                    Start New Chat
                  </button>
                </div>
              </div>
            ) : (
              <ChatInterface
                messages={currentSession.messages}
                onSendMessage={handleSendMessage}
                isLoading={isLoading}
              />
            )}
          </div>
        </div>

        {/* Stats Panel */}
        <div className="w-80 hidden lg:block">
          <StatsPanel
            totalCost={totalCost}
            totalTokens={totalTokens}
            totalMessages={
              currentSession?.messages.filter((m) => m.role === "assistant")
                .length || 0
            }
          />
        </div>
      </div>
    </main>
  );
}
