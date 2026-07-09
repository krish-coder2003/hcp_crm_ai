from langchain_groq import ChatGroq

from app.config import settings


def get_chat_llm(temperature: float = 0.2):
    """Primary LLM used by the LangGraph agent to decide which tool to call.

    Uses Groq's gemma2-9b-it as required by the assignment. llama-3.3-70b-versatile
    is kept as a documented fallback (e.g. if gemma2-9b-it is deprecated/unavailable
    on your Groq account) - swap GROQ_MODEL in .env to use it.
    """
    return ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=temperature,
    )


def get_extraction_llm():
    """A low-temperature LLM instance used *inside* tools (log_interaction,
    edit_interaction, summarize_voice_note) for structured entity extraction /
    summarization sub-tasks, kept separate from the routing LLM above so its
    prompting can be tuned independently.
    """
    return ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=0,
    )
