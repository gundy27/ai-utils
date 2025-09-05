import os
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_chat_stream_mocks_openai(monkeypatch):
    os.environ["OPENAI_API_KEY"] = "test-key"

    # Mock OpenAI stream iterator
    fake_event = MagicMock()
    fake_event.choices = [MagicMock(delta=MagicMock(content="hi"))]
    fake_stream_ctx = MagicMock()
    fake_stream_ctx.__enter__.return_value = [fake_event, fake_event]
    fake_stream_ctx.__exit__.return_value = False

    with patch("gundy_ai.llm.openai_wrapper.OpenAI") as MockOpenAI:
        instance = MockOpenAI.return_value
        instance.chat.completions.create.return_value = fake_stream_ctx

        from gundy_ai.llm.openai_wrapper import OpenAIClient

        client = OpenAIClient()
        chunks = list(
            client.chat_stream(
                model="gpt-4o-mini", messages=[{"role": "user", "content": "h"}]
            )
        )
        assert "hi" in "".join(chunks)


@pytest.mark.integration
def test_integration_instantiation_requires_key():
    from gundy_ai.llm.openai_wrapper import OpenAIClient

    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set; skipping integration test")

    client = OpenAIClient()
    assert client is not None
