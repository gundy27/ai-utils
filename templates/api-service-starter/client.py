import json
import sys
import warnings
import httpx

# Suppress LibreSSL warning from urllib3 v2 on macOS system Python (match by message)
warnings.filterwarnings(
    "ignore",
    message=".*urllib3 v2 only supports OpenSSL.*",
)


def post_chat(prompt: str) -> None:
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
    }
    r = httpx.post("http://127.0.0.1:8001/chat", json=payload, timeout=30)
    r.raise_for_status()
    print(json.dumps(r.json(), indent=2))


def stream_chat(prompt: str) -> None:
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
    }
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
    if mode == "stream":
        stream_chat(prompt)
    else:
        post_chat(prompt)
