from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent import app_graph

app = FastAPI()


class QueryRequest(BaseModel):
    q: str
    thread_id: str


async def stream_answer(question: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}

    async for event in app_graph.astream_events(
        {"messages": [{"role": "user", "content": question}]},
        config=config,
        version="v2",
    ):
        is_token = event["event"] == "on_chat_model_stream"
        is_responder = event["metadata"].get("langgraph_node") == "responder"
        if is_token and is_responder:
            token = event["data"]["chunk"].content
            if token:
                yield token


@app.post("/query")
async def query(request: QueryRequest):
    return StreamingResponse(
        stream_answer(request.q, request.thread_id), media_type="text/plain"
    )
