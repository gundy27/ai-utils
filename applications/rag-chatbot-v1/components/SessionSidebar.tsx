"use client";

import { Session } from "@/lib/types";

interface Props {
  sessions: Session[];
  currentSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onNewSession: () => void;
}

export default function SessionSidebar({
  sessions,
  currentSessionId,
  onSelectSession,
  onNewSession,
}: Props) {
  return (
    <div className="h-full flex flex-col bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={onNewSession}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
        >
          + New Chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {sessions.length === 0 ? (
          <div className="text-center text-gray-500 text-sm mt-8 px-4">
            No conversations yet. Start a new chat!
          </div>
        ) : (
          sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => onSelectSession(session.id)}
              className={`w-full text-left p-3 rounded-lg mb-2 transition-colors ${
                currentSessionId === session.id
                  ? "bg-blue-100 dark:bg-blue-900/50 border-2 border-blue-500"
                  : "bg-white dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700"
              }`}
            >
              <div className="font-medium text-sm truncate">
                Session {session.id.substring(8, 16)}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {session.message_count || session.messages.length} messages
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
