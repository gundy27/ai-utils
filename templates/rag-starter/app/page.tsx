"use client";

import { useState } from "react";
import NavigationDrawer from "@/components/NavigationDrawer";
import ChatInterface from "@/components/ChatInterface";
import DocumentsView from "@/components/DocumentsView";
import SystemView from "@/components/SystemView";
import { apiClient } from "@/lib/api";
import {
  Session,
  Message,
  DocumentIngestResponse,
  ViewType,
  Settings,
} from "@/lib/types";

export default function Home() {
  const [currentView, setCurrentView] = useState<ViewType>("chat");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSession, setCurrentSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStreamMessage, setCurrentStreamMessage] = useState("");
  const [settings, setSettings] = useState<Settings>({
    model: "gpt-4o-mini",
    topK: 5,
    chunkMaxTokens: 512,
    userId: "default_user",
    useStreaming: true,
  });

  const handleNewSession = () => {
    const newSession: Session = {
      id: `new_${Date.now()}`,
      messages: [],
    };
    setSessions([newSession, ...sessions]);
    setCurrentSession(newSession);
    setCurrentView("chat");
  };

  const handleSelectSession = (sessionId: string) => {
    const session = sessions.find((s) => s.id === sessionId);
    if (session) {
      setCurrentSession(session);
    }
  };

  const handleUploadComplete = (doc: DocumentIngestResponse) => {
    // Success feedback is now shown in the upload component's status display
    // No need for alert popup
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

    if (settings.useStreaming) {
      // Streaming mode
      setIsStreaming(true);
      setCurrentStreamMessage("");

      let sessionIdResult = "";
      let sourcesResult: SourceChunk[] = [];
      let fullResponse = "";

      try {
        await apiClient.chatStream(
          message,
          session.id.startsWith("new_") ? undefined : session.id,
          settings.userId,
          settings.topK,
          settings.model,
          // onChunk
          (delta) => {
            fullResponse += delta;
            setCurrentStreamMessage(fullResponse);
          },
          // onMetadata
          (metadata) => {
            sessionIdResult = metadata.session_id;
            sourcesResult = metadata.sources;
          },
          // onDone
          (stats) => {
            const assistantMessage: Message = {
              role: "assistant",
              content: fullResponse,
              sources: sourcesResult,
              tokens: stats.tokens_used,
              cost: stats.cost_usd,
            };

            const finalSession = {
              id: sessionIdResult,
              messages: [...updatedSession.messages, assistantMessage],
              message_count: updatedSession.messages.length + 1,
            };

            setCurrentSession(finalSession);
            setSessions(
              sessions.map((s) => (s.id === session.id ? finalSession : s)),
            );
            setCurrentStreamMessage("");
          },
          // onError
          (error) => {
            alert(`Chat failed: ${error}`);
            setCurrentStreamMessage("");
          },
        );
      } finally {
        setIsStreaming(false);
      }
    } else {
      // Non-streaming mode
      setIsLoading(true);

      try {
        const response = await apiClient.chat(
          message,
          session.id.startsWith("new_") ? undefined : session.id,
          settings.userId,
          settings.topK,
          settings.model,
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
      } catch (error) {
        alert(`Chat failed: ${error}`);
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleViewChange = (view: ViewType) => {
    setCurrentView(view);
  };

  const handleSettingsChange = (newSettings: Settings) => {
    setSettings(newSettings);
  };

  return (
    <main className="h-screen flex flex-col">
      {/* Header */}
      <header className="bg-blue-600 text-white p-4 shadow-lg">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold">RAG Chatbot</h1>
          <div className="text-sm">Powered by gundy-ai</div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Navigation Drawer */}
        <NavigationDrawer
          currentView={currentView}
          onViewChange={handleViewChange}
          sessions={sessions}
          currentSessionId={currentSession?.id || null}
          onSelectSession={handleSelectSession}
          onNewSession={handleNewSession}
        />

        {/* Main View Area */}
        <div className="flex-1 overflow-hidden">
          {currentView === "chat" && (
            <div className="h-full flex flex-col">
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
                  isStreaming={isStreaming}
                  streamMessage={currentStreamMessage}
                />
              )}
            </div>
          )}

          {currentView === "documents" && (
            <DocumentsView
              onUploadComplete={handleUploadComplete}
              userId={settings.userId}
            />
          )}

          {currentView === "system" && (
            <SystemView
              settings={settings}
              onSettingsChange={handleSettingsChange}
            />
          )}
        </div>
      </div>
    </main>
  );
}
