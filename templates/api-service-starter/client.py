import json
import sys
import warnings

import httpx

# Suppress LibreSSL warning from urllib3 v2 on macOS system Python (match by message)
warnings.filterwarnings(
    "ignore",
    message=".*urllib3 v2 only supports OpenSSL.*",
)


def post_chat(prompt: str, session_id: str | None = None) -> None:
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
    }
    if session_id:
        payload["session_id"] = session_id
    r = httpx.post("http://127.0.0.1:8001/chat", json=payload, timeout=30)
    r.raise_for_status()
    print(json.dumps(r.json(), indent=2))


def stream_chat(prompt: str, session_id: str | None = None) -> None:
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
    }
    if session_id:
        payload["session_id"] = session_id
    with httpx.stream(
        "POST", "http://127.0.0.1:8001/chat/stream", json=payload, timeout=None
    ) as r:
        r.raise_for_status()
        for chunk in r.iter_text():
            if chunk:
                print(chunk, end="")
    print()


if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Say hi"
    mode = sys.argv[2] if len(sys.argv) > 2 else "stream"
    sess = sys.argv[3] if len(sys.argv) > 3 else "demo-session"
    if mode == "stream":
        stream_chat(prompt, sess)
    else:
        post_chat(prompt, sess)
