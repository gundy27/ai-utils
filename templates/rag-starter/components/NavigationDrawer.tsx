"use client";

import { useState } from "react";
import { Session, ViewType } from "@/lib/types";

interface Props {
  currentView: ViewType;
  onViewChange: (view: ViewType) => void;
  sessions: Session[];
  currentSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
}

export default function NavigationDrawer({
  currentView,
  onViewChange,
  sessions,
  currentSessionId,
  onSelectSession,
  onNewSession,
}: Props) {
  const [chatsExpanded, setChatsExpanded] = useState(true);

  const menuItems = [
    { id: "chat" as ViewType, label: "Chat", icon: "💬" },
    { id: "documents" as ViewType, label: "Documents", icon: "📄" },
    { id: "system" as ViewType, label: "System", icon: "⚙️" },
  ];

  return (
    <div className="h-full flex flex-col bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 w-[280px]">
      {/* Header with New Chat Button */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => {
            onNewSession();
            onViewChange("chat");
          }}
          className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition-colors flex items-center justify-center gap-2"
        >
          <span className="text-lg">+</span>
          <span>New Chat</span>
        </button>
      </div>

      {/* Navigation Menu */}
      <div className="flex-1 overflow-y-auto p-2">
        {/* Collapsible Chats Section */}
        <div className="mb-2">
          <button
            onClick={() => setChatsExpanded(!chatsExpanded)}
            className="w-full flex items-center justify-between p-3 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <div className="flex items-center gap-3">
              <span className="text-xl">💬</span>
              <span className="font-medium">Chats</span>
            </div>
            <span className="text-gray-500 text-sm">
              {chatsExpanded ? "▼" : "▶"}
            </span>
          </button>

          {/* Session List */}
          {chatsExpanded && (
            <div className="mt-1 ml-4 space-y-1">
              {sessions.length === 0 ? (
                <div className="text-center text-gray-500 text-sm py-4 px-2">
                  No conversations yet
                </div>
              ) : (
                sessions.map((session) => (
                  <button
                    key={session.id}
                    onClick={() => {
                      onSelectSession(session.id);
                      onViewChange("chat");
                    }}
                    className={`w-full text-left p-2 rounded-lg transition-colors text-sm ${
                      currentSessionId === session.id && currentView === "chat"
                        ? "bg-blue-100 dark:bg-blue-900/50 border border-blue-500"
                        : "hover:bg-gray-100 dark:hover:bg-gray-700"
                    }`}
                  >
                    <div className="truncate">
                      Session {session.id.substring(0, 8)}...
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {session.message_count || session.messages.length}{" "}
                      messages
                    </div>
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        {/* Other Menu Items */}
        <div className="space-y-1">
          {menuItems
            .filter((item) => item.id !== "chat")
            .map((item) => (
              <button
                key={item.id}
                onClick={() => onViewChange(item.id)}
                className={`w-full flex items-center gap-3 p-3 rounded-lg transition-colors ${
                  currentView === item.id
                    ? "bg-blue-100 dark:bg-blue-900/50 border border-blue-500 font-medium"
                    : "hover:bg-gray-100 dark:hover:bg-gray-800"
                }`}
              >
                <span className="text-xl">{item.icon}</span>
                <span>{item.label}</span>
              </button>
            ))}
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <div className="text-xs text-gray-500 text-center">
          RAG Chatbot v1
          <br />
          Powered by gundy-ai
        </div>
      </div>
    </div>
  );
}
