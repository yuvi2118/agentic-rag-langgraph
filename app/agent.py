from typing import TypedDict , Annotated
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
from pydantic import BaseModel

from app.config import get_settings

class AgentState(TypedDict):
    messages : Annotated[list , add_messages]
    intent : str
    search_query : str
    retrieved_chunks: list[dict]

class PlannerOutput(BaseModel):
    intent : str
    search_query : str

def planner_node(state : AgentState) -> dict:
    settings = get_settings()
    llm = ChatGroq(
        model = "openai/gpt-oss-120b", api_key= settings.groq_api_key
    )
    structured_llm = llm.with_structured_output(PlannerOutput)

    system_prompt = (
        "You are a routing assistant for a Kubernetes documentation chatbot. "
        "Given the conversation, decide:\n"
        "1. intent: 'conversational' if it's small talk/greetings with no real "
        "question, otherwise 'technical'.\n"
        "2. search_query: if intent is 'technical', rewrite the user's latest "
        "message into a standalone, self-contained search query using context "
        "from earlier messages if needed. If intent is 'conversational', return "
        "an empty string."
    )

    result = structured_llm.invoke(
        [{"role": "system", "content": system_prompt}] + state["messages"]
    )
    return {"intent": result.intent, "search_query": result.search_query}


from app.vectorstore import search , rerank 

CONFIDENCE_THRESHOLD = 0.3

def retriever_node(state: AgentState) -> dict:
    query = state["search_query"]

    candidates = search(query,top_k=15)
    reranked = rerank(query, candidates, top_n=5)
    return {"retrieved_chunks": reranked}


from tavily import TavilyClient

def web_search_node(state : AgentState) -> dict:
    settings = get_settings()
    client = TavilyClient(api_key=settings.tavily_api_key)

    query = state["search_query"]
    response = client.search(query=query, max_results=5)

    results = [
    {"text": r["content"], "source": r["url"], "relevance_score": r["score"]}

    for r in response["results"]]

    return {"retrieved_chunks": results}