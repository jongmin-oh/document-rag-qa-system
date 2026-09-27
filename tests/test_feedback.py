import json

import pytest
from pydantic import ValidationError

from app.feedback import FeedbackRequest, record_interaction, save_feedback
from app.tasks.qa import AskResponse, Citation


class FakeTable:
    def __init__(self):
        self.item = None
        self.update = None

    def put_item(self, *, Item):
        self.item = Item

    def update_item(self, **kwargs):
        self.update = kwargs


def test_negative_feedback_requires_reason():
    with pytest.raises(ValidationError):
        FeedbackRequest(interaction_id="a" * 36, rating="not_helpful")


def test_interaction_and_negative_feedback_are_linked(monkeypatch):
    table = FakeTable()
    monkeypatch.setattr("app.feedback._table", lambda: table)
    response = AskResponse(
        answerable=True,
        answer="답변",
        citations=[
            Citation(
                n=1,
                chunk_id="EL-1",
                source="공식 문서",
                page_start=1,
                page_end=1,
                score=0.123,
            )
        ],
        model_version="test-model",
        interaction_id="a" * 36,
    )

    record_interaction("a" * 36, "질문", response)
    assert table.item["question"] == "질문"
    assert json.loads(table.item["citations"])[0]["score"] == 0.123

    feedback = FeedbackRequest(
        interaction_id="a" * 36,
        rating="not_helpful",
        reason="source",
        comment="근거가 달라요",
    )
    save_feedback(feedback)
    values = table.update["ExpressionAttributeValues"]
    assert values[":status"] == "review_needed"
    assert values[":reason"] == "source"
