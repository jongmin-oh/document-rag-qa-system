from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.index import client
from app.tasks.qa.ask import AskResponse, ask, generation_client

router = APIRouter()
embedding_client = client()
llm = generation_client()


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


@router.post("/ask", response_model=AskResponse)
def post_ask(req: AskRequest) -> AskResponse:
    return ask(embedding_client, req.question, llm)
