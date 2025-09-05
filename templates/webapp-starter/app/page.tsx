"use client";
import { useState } from "react";

export default function Page() {
  const [input, setInput] = useState("");
  const [output, setOutput] = useState("");
  const [streaming, setStreaming] = useState(false);

  const send = async (mode: "nonstream" | "stream") => {
    setOutput("");
    const payload = {
      model: "gpt-4o-mini",
      messages: [{ role: "user", content: input }],
    };
    if (mode === "nonstream") {
      const r = await fetch("/api/chat", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      const j = await r.json();
      setOutput(j.content ?? JSON.stringify(j));
    } else {
      setStreaming(true);
      const r = await fetch("/api/chat-stream", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      const reader = r.body?.getReader();
      if (!reader) return setStreaming(false);
      const decoder = new TextDecoder();
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        setOutput((o) => o + decoder.decode(value));
      }
      setStreaming(false);
    }
  };

  return (
    <main style={{ padding: 24, maxWidth: 720 }}>
      <h1>Chat</h1>
      <textarea
        rows={4}
        style={{ width: "100%" }}
        value={input}
        onChange={(e) => setInput(e.target.value)}
      />
      <div style={{ marginTop: 8 }}>
        <button
          onClick={() => send("nonstream")}
          disabled={!input || streaming}
        >
          Send
        </button>
        <button
          onClick={() => send("stream")}
          disabled={!input || streaming}
          style={{ marginLeft: 8 }}
        >
          Stream
        </button>
      </div>
      <pre
        style={{
          whiteSpace: "pre-wrap",
          background: "#111",
          color: "#0f0",
          padding: 12,
          marginTop: 16,
        }}
      >
        {output}
      </pre>
    </main>
  );
}
