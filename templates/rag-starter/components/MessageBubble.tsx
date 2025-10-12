"use client";

import { Message } from "@/lib/types";
import SourceCitation from "./SourceCitation";

interface Props {
  message: Message;
  isStreaming?: boolean;
}

export default function MessageBubble({ message, isStreaming = false }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-2 ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100"
        }`}
      >
        <div className="whitespace-pre-wrap">
          {message.content}
          {isStreaming && (
            <span className="inline-block ml-1 w-2 h-4 bg-current animate-pulse">
              ▊
            </span>
          )}
        </div>

        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-300 dark:border-gray-600">
            <SourceCitation sources={message.sources} />
          </div>
        )}

        {!isUser && (message.tokens || message.cost) && (
          <div className="mt-2 text-xs opacity-70">
            {message.tokens && <span>Tokens: {message.tokens}</span>}
            {message.tokens && message.cost && <span> • </span>}
            {message.cost && <span>Cost: ${message.cost.toFixed(6)}</span>}
          </div>
        )}
      </div>
    </div>
  );
}
