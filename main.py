import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.routers import get_routers

app = FastAPI(title="실업급여 RAG QA")
for router in get_routers():
    app.include_router(router)


@app.exception_handler(Exception)
def upstream_error(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": f"{type(exc).__name__}: {exc}"})


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
