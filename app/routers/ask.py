from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.index import client
from app.feedback import record_interaction
from app.tasks.qa.ask import AskResponse, ask, generation_client

router = APIRouter()
embedding_client = client()
llm = generation_client()


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


@router.post("/ask", response_model=AskResponse)
def post_ask(req: AskRequest) -> AskResponse:
    response = ask(embedding_client, req.question, llm)
    interaction_id = str(uuid4())
    response.interaction_id = interaction_id
    record_interaction(interaction_id, req.question, response)
    return response
