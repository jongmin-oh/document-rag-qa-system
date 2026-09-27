import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.index import client
from app.tasks.qa.ask import AskResponse, ask, generation_client

app = FastAPI(title="실업급여 RAG QA")
embedding_client = client()
llm = generation_client()


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


@app.exception_handler(Exception)
def upstream_error(_: Request, exc: Exception) -> JSONResponse:
    # /ask의 실패는 대부분 Gemini·OpenRouter 호출(429 재시도 소진, 스키마 불일치 등)이라 종류를 가리지 않고 502로 알린다.
    return JSONResponse(status_code=502, content={"detail": f"{type(exc).__name__}: {exc}"})


@app.post("/ask", response_model=AskResponse)
def post_ask(req: AskRequest) -> AskResponse:
    return ask(embedding_client, req.question, llm)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
