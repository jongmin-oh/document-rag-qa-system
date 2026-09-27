"""운영에서 낮은 평가를 받은 답변을 개선 검토용 JSONL로 내보낸다."""

import argparse
import json
import os
from pathlib import Path

import boto3
from boto3.dynamodb.conditions import Attr

DEFAULT_OUTPUT = Path(__file__).resolve().parent / "data" / "feedback" / "review_needed.jsonl"


def export_review_needed(table_name: str, output: Path = DEFAULT_OUTPUT) -> int:
    table = boto3.resource("dynamodb").Table(table_name)
    kwargs = {"FilterExpression": Attr("feedback_status").eq("review_needed")}
    items = []
    while True:
        response = table.scan(**kwargs)
        items.extend(response.get("Items", []))
        if "LastEvaluatedKey" not in response:
            break
        kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    items.sort(key=lambda item: item.get("feedback_at", ""), reverse=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(item, ensure_ascii=False, default=str) + "\n" for item in items),
        encoding="utf-8",
    )
    return len(items)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", default=os.environ.get("FEEDBACK_TABLE_NAME"), help="DynamoDB 테이블 이름")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not args.table:
        parser.error("--table 또는 FEEDBACK_TABLE_NAME이 필요합니다")
    count = export_review_needed(args.table, args.output)
    print(f"{count}건을 {args.output}에 저장했습니다.")


if __name__ == "__main__":
    main()
