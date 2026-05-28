import os
# Force gRPC to use the stable OS-native DNS resolver instead of the custom ares resolver.
# This completely prevents intermittent "503 DNS server returned answer with no data" lookup errors on macOS/Docker.
os.environ["GRPC_DNS_RESOLVER"] = "native"

from langchain_google_vertexai import ChatVertexAI

_llm_instance = None

def get_vertex_llm() -> ChatVertexAI:
    """
    Единая точка инициализации модели Gemini через официальный Vertex AI бэкэнд.
    Строго использует инфраструктуру Google Cloud Platform.
    Возвращает синглтон-объект для предотвращения состояния гонки (race conditions)
    в многопоточной среде и эффективного повторного использования пула соединений.
    """
    global _llm_instance
    if _llm_instance is None:
        # Твой подтвержденный Project ID и стабильный регион
        PROJECT_ID = "project-0a1ece04-f585-4dd2-98a"
        LOCATION = "global"

        # Инициализируем модель строго по документации langchain-google-vertexai
        _llm_instance = ChatVertexAI(
            model="gemini-3.5-flash",  # Твоя новейшая модель из Vertex AI Model Garden
            project=PROJECT_ID,
            location=LOCATION,
            temperature=0.2,
            max_output_tokens=16384
        )
    return _llm_instance



