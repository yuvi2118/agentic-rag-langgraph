from fastapi import FastAPI
from pydantic import BaseModel

from app.agent import app_graph

app = FastAPI()


class QueryRequest(BaseModel):
    q: str
    thread_id: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    config = {"configurable": {"thread_id": request.thread_id}}
    result = app_graph.invoke(
        {"messages": [{"role": "user", "content": request.q}]},
        config=config,
    )

    answer = result["messages"][-1].content
    sources = list({chunk["source"] for chunk in result.get("retrieved_chunks", [])})

    return QueryResponse(answer=answer, sources=sources)