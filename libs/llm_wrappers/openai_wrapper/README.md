## gundy_ai OpenAI Wrapper

Secure OpenAI client with retries, structured logging, and streaming support.

### Install (from Git subdirectory)

```bash
pip install "git+https://github.com/gundy27/ai-utils.git#subdirectory=libs/llm_wrappers/openai_wrapper"
```

### Usage

```python
from gundy_ai.llm.openai_wrapper import OpenAIClient

client = OpenAIClient()
stream = client.chat_stream(model="gpt-4o-mini", messages=[{"role": "user", "content": "Hello"}])
for chunk in stream:
    print(chunk, end="")
```

See `.env.example` for configuration.
