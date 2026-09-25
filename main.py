import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.tasks.index.build import client
from app.tasks.qa.ask import AskResponse, ask

app = FastAPI(title="실업급여 RAG QA")
gemini = client()


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


@app.post("/ask", response_model=AskResponse)
def post_ask(req: AskRequest) -> AskResponse:
    return ask(gemini, req.question)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
