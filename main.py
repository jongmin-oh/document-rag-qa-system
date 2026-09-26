import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.index import client
from app.tasks.qa.ask import AskResponse, ask, generation_client

app = FastAPI(title="실업급여 RAG QA")
embedding_client = client()
llm = generation_client()


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


@app.post("/ask", response_model=AskResponse)
def post_ask(req: AskRequest) -> AskResponse:
    return ask(embedding_client, req.question, llm)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
