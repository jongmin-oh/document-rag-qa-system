from fastapi import APIRouter, HTTPException, Response, status

from app.feedback import FeedbackRequest, save_feedback

router = APIRouter()


@router.post("/feedback", status_code=status.HTTP_204_NO_CONTENT)
def post_feedback(feedback: FeedbackRequest) -> Response:
    try:
        save_feedback(feedback)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="평가할 답변을 찾을 수 없습니다") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
