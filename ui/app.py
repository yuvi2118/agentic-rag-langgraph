import uuid

import chainlit as cl
import requests

BACKEND_URL = "http://localhost:8000/query"


@cl.on_chat_start
async def start():
    cl.user_session.set("thread_id", str(uuid.uuid4()))
    await cl.Message(content="Hi! Ask me anything about Kubernetes.").send()


@cl.on_message
async def main(message: cl.Message):
    thread_id = cl.user_session.get("thread_id")

    response = requests.post(
        BACKEND_URL, json={"q": message.content, "thread_id": thread_id}
    )
    data = response.json()

    answer = data["answer"]
    if data["sources"]:
        answer += f"\n\n**Sources:** {', '.join(data['sources'])}"

    await cl.Message(content=answer).send()
