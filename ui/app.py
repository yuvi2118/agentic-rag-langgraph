import uuid

import chainlit as cl
import httpx

BACKEND_URL = "http://localhost:8000/query"


@cl.on_chat_start
async def start():
    cl.user_session.set("thread_id", str(uuid.uuid4()))
    await cl.Message(content="Hi! Ask me anything about Kubernetes.").send()


@cl.on_message
async def main(message: cl.Message):
    thread_id = cl.user_session.get("thread_id")
    msg = cl.Message(content="🤔 Thinking...")
    await msg.send()

    first_chunk = True
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "POST", BACKEND_URL, json={"q": message.content, "thread_id": thread_id}
        ) as response:
            async for chunk in response.aiter_text():
                if first_chunk:
                    msg.content = ""
                    first_chunk = False
                await msg.stream_token(chunk)

    await msg.update()
