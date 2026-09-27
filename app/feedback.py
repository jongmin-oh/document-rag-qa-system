import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Literal

import boto3
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field, model_validator

from app.tasks.qa import AskResponse

logger = logging.getLogger(__name__)

FeedbackRating = Literal["helpful", "not_helpful"]
FeedbackReason = Literal["incorrect", "missing", "source", "unclear", "other"]


class FeedbackRequest(BaseModel):
    interaction_id: str = Field(min_length=36, max_length=36)
    rating: FeedbackRating
    reason: FeedbackReason | None = None
    comment: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def require_reason_for_negative_feedback(self):
        if self.rating == "not_helpful" and self.reason is None:
            raise ValueError("도움이 되지 않은 이유를 선택해 주세요")
        return self


def _table():
    table_name = os.environ.get("FEEDBACK_TABLE_NAME")
    if not table_name:
        raise RuntimeError("FEEDBACK_TABLE_NAME 환경 변수가 설정되지 않았습니다")
    return boto3.resource("dynamodb").Table(table_name)


def record_interaction(interaction_id: str, question: str, response: AskResponse) -> None:
    """질문 응답 기록을 저장한다. 저장 장애가 사용자 답변을 막아서는 안 된다."""
    now = datetime.now(timezone.utc)
    item = {
        "interaction_id": interaction_id,
        "created_at": now.isoformat(),
        "expires_at": int((now + timedelta(days=90)).timestamp()),
        "question": question,
        "answerable": response.answerable,
        "answer": response.answer,
        # DynamoDB는 Python float를 받지 않으므로 인용 객체는 JSON 문자열로 보관한다.
        "citations": json.dumps(
            [citation.model_dump(mode="json") for citation in response.citations],
            ensure_ascii=False,
        ),
        "model_version": response.model_version,
        "feedback_status": "pending",
    }
    try:
        _table().put_item(Item=item)
    except Exception:
        logger.exception("interaction feedback seed 저장 실패", extra={"interaction_id": interaction_id})


def save_feedback(feedback: FeedbackRequest) -> None:
    now = datetime.now(timezone.utc).isoformat()
    try:
        _table().update_item(
            Key={"interaction_id": feedback.interaction_id},
            UpdateExpression=(
                "SET feedback_status = :status, feedback_rating = :rating, "
                "feedback_reason = :reason, feedback_comment = :comment, feedback_at = :at"
            ),
            ConditionExpression="attribute_exists(interaction_id)",
            ExpressionAttributeValues={
                ":status": "review_needed" if feedback.rating == "not_helpful" else "accepted",
                ":rating": feedback.rating,
                ":reason": feedback.reason or "",
                ":comment": feedback.comment.strip(),
                ":at": now,
            },
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            raise KeyError(feedback.interaction_id) from exc
        raise
