#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

STACK=document-rag-qa-system
REGION=ap-northeast-2

# 백엔드: 빌드 + 배포 (지침 문서를 Lambda 패키지에 포함)
sam build
sam deploy --no-confirm-changeset --no-fail-on-empty-changeset