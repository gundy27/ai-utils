from gundy_ai.llm import OpenAIClient


def main() -> None:
    client = OpenAIClient()
    stream = client.chat_stream(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Tell me a short joke about databases."}],
    )
    for chunk in stream:
        print(chunk, end="")
    print()


if __name__ == "__main__":
    main()
