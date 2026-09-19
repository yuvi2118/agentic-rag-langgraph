from datetime import datetime
from typing import TypedDict , Annotated
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
from pydantic import BaseModel
from app.config import configure_langsmith
configure_langsmith()

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

    today = datetime.now().strftime("%Y-%m-%d")

    system_prompt = (
        f"Today's date is {today}. "
        "You are a routing assistant for a Kubernetes documentation chatbot. "
        "Given the conversation, decide:\n"
        "1. intent: 'conversational' if it's small talk/greetings with no real "
        "question, otherwise 'technical'.\n"
        "2. search_query: if intent is 'technical', rewrite the user's latest "
        "message into a standalone, self-contained search query using context "
        "from earlier messages if needed, using today's actual date above for "
        "any relative time references (e.g. 'this month', 'recently'). If intent "
        "is 'conversational', return an empty string."
    )

    result = structured_llm.invoke(
        [{"role": "system", "content": system_prompt}] + state["messages"]
    )
    return {"intent": result.intent, "search_query": result.search_query}


from app.vectorstore import search , rerank 

CONFIDENCE_THRESHOLD = 0.5

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


from langchain_openai import ChatOpenAI

def responder_node(state: AgentState) -> dict:
    settings = get_settings()
    llm = ChatOpenAI(
        model= "gpt-4o-mini",api_key=settings.openai_api_key
    )

    if state.get("retrieved_chunks"):
        context_text = "\n\n".join(
            f"[Source: {c['source']}]\n{c['text']}" for c in state["retrieved_chunks"]
        )
        system_prompt = (
            "You are a helpful Kubernetes assistant. Answer the user's question "
            "using ONLY the context below. If the context doesn't contain the "
            "answer, say you don't know - do not make things up. Mention which "
            "source(s) you used.\n\n"
            f"Context:\n{context_text}"
        )

    else:
        system_prompt = (
            "You are a helpful Kubernetes assistant having a normal conversation. "
            "Respond naturally."
        )

    messages = [{"role": "system", "content": system_prompt}] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": response.content}]}

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver


def route_after_planner(state: AgentState) -> str:
    if state["intent"] == "conversational":
        return "responder"
    return "retriever"


def route_after_retriever(state: AgentState) -> str:
    top_score = state["retrieved_chunks"][0]["relevance_score"] if state["retrieved_chunks"] else 0
    if top_score < CONFIDENCE_THRESHOLD:
        return "web_search"
    return "responder"


graph = StateGraph(AgentState)

graph.add_node("planner", planner_node)
graph.add_node("retriever", retriever_node)
graph.add_node("web_search", web_search_node)
graph.add_node("responder", responder_node)

graph.add_edge(START, "planner")
graph.add_conditional_edges("planner", route_after_planner, {"retriever": "retriever", "responder": "responder"})
graph.add_conditional_edges("retriever", route_after_retriever, {"web_search": "web_search", "responder": "responder"})
graph.add_edge("web_search", "responder")
graph.add_edge("responder", END)

checkpointer = MemorySaver()
app_graph = graph.compile(checkpointer=checkpointer)