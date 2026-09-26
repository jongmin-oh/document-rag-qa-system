# End-to-end 답변 평가 리포트

- 답변 실행: 2026-09-26T04:22:53+00:00 / 커밋 `ab0f680` / dirty `false`
- 문항: 41개 / 답변 temperature 0 / Judge temperature API 기본값 / seed 42
- 답변 모델: `gemini-3.8-flash` / Judge: OpenRouter `openai/gpt-6-sol`
- 결정론적 지표: answerability, citation 형식, Gold 근거 좌표와 인용 청크의 일치
- 의미 지표: 참고 정답과 실제 인용 문맥을 이용한 1–5점 LLM Judge. 평균은 full·partial 문항만 (none은 거부 지표로 판정)
- citation 객체는 답변 본문의 `[n]`·`[n, m]`을 서버가 파싱해 생성

## 전체

| 영역 | 지표 | 결과 |
|---|---|---:|
| 거부 | Answerability accuracy | 0.976 |
| 거부 | Answerable recall | 1.000 |
| 거부 | Refusal recall | 0.800 (4/5) |
| 거부 | False answer rate | 0.200 |
| 인용 | Citation integrity | 1.000 |
| 인용 | Citation presence | 1.000 |
| 인용 | Gold evidence recall | 0.703 |
| 인용 | Gold evidence precision | 0.796 |
| 인용 | Gold evidence coverage | 0.740 |
| 답변(1–5) | Correctness | 4.000 |
| 답변(1–5) | Completeness | 3.222 |
| 답변(1–5) | Faithfulness | 4.028 |
| 답변(1–5) | Partial handling | 4.000 |
| 답변(1–5) | Clarity | 4.417 |
| 가독성 | 평균 답변 길이(자) | 281 |
| 가독성 | 평균 문장 길이(자) | 74 |
| 가독성 | 80자 초과 문장 비율 | 0.370 |
| 가독성 | 인용 자료 원문 복사율 | 0.026 |
| 가독성 | 법조문식 표현 수(답변당) | 0.03 |

## 그룹별

| 그룹 | 문항 | Answerability | Citation integrity | Correctness | Completeness | Faithfulness | Clarity |
|---|---:|---:|---:|---:|---:|---:|---:|
| factoid | 15 | 1.000 | 1.000 | 4.20 | 3.67 | 4.00 | 4.60 |
| multi_hop | 13 | 1.000 | 1.000 | 3.92 | 3.00 | 4.08 | 4.38 |
| procedural | 7 | 1.000 | 1.000 | 3.57 | 2.71 | 3.86 | 4.00 |
| summary | 1 | 1.000 | 1.000 | 5.00 | 3.00 | 5.00 | 5.00 |
| unanswerable | 5 | 0.800 | 1.000 | - | - | - | - |
| full | 18 | 1.000 | 1.000 | 3.89 | 3.39 | 4.11 | 4.33 |
| none | 5 | 0.800 | 1.000 | - | - | - | - |
| partial | 18 | 1.000 | 1.000 | 4.11 | 3.06 | 3.94 | 4.50 |

## 문항별

| id | Gold | 예측 | Citation | Evidence recall | 정답성 | 완전성 | 충실성 | 이해 용이성 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| KIN-01 | full | answer | 1 | 0.40 | 3 | 3 | 4 | 5 |
| KIN-02 | partial | answer | 1 | 1.00 | 4 | 4 | 4 | 4 |
| KIN-03 | partial | answer | 1 | 0.50 | 3 | 3 | 3 | 4 |
| KIN-04 | full | answer | 1 | 1.00 | 4 | 5 | 4 | 5 |
| KIN-05 | full | answer | 1 | 1.00 | 4 | 4 | 5 | 5 |
| KIN-06 | partial | answer | 1 | 0.75 | 5 | 3 | 4 | 5 |
| KIN-07 | full | answer | 1 | 1.00 | 5 | 5 | 4 | 5 |
| KIN-08 | full | answer | 1 | 1.00 | 3 | 3 | 3 | 4 |
| KIN-09 | full | answer | 1 | 0.00 | 3 | 2 | 4 | 3 |
| KIN-10 | full | answer | 1 | 0.43 | 4 | 3 | 4 | 4 |
| KIN-11 | partial | answer | 1 | 0.50 | 3 | 2 | 3 | 4 |
| KIN-12 | full | answer | 1 | 0.67 | 5 | 3 | 5 | 5 |
| KIN-13 | none | answer | 1 | - | 5 | 5 | 5 | 4 |
| KIN-14 | full | answer | 1 | 0.67 | 2 | 2 | 3 | 3 |
| KIN-15 | partial | answer | 1 | 0.80 | 4 | 3 | 5 | 4 |
| KIN-16 | full | answer | 1 | 0.67 | 3 | 3 | 4 | 3 |
| KIN-17 | full | answer | 1 | 0.33 | 5 | 5 | 4 | 5 |
| KIN-18 | full | answer | 1 | 0.67 | 5 | 3 | 4 | 5 |
| KIN-19 | full | answer | 1 | 0.33 | 3 | 3 | 4 | 5 |
| KIN-20 | none | refuse | 1 | - | 5 | 4 | 5 | 4 |
| KIN-21 | partial | answer | 1 | 1.00 | 4 | 3 | 3 | 5 |
| KIN-22 | full | answer | 1 | 0.33 | 4 | 4 | 5 | 4 |
| KIN-23 | full | answer | 1 | 0.50 | 4 | 3 | 4 | 5 |
| KIN-24 | partial | answer | 1 | 0.67 | 4 | 3 | 3 | 5 |
| KIN-25 | partial | answer | 1 | 1.00 | 4 | 3 | 3 | 5 |
| KIN-26 | full | answer | 1 | 1.00 | 4 | 3 | 5 | 4 |
| KIN-27 | full | answer | 1 | 0.75 | 4 | 3 | 3 | 4 |
| KIN-28 | full | answer | 1 | 1.00 | 5 | 4 | 5 | 4 |
| KIN-29 | partial | answer | 1 | 1.00 | 5 | 4 | 5 | 5 |
| KIN-30 | partial | answer | 1 | 1.00 | 4 | 3 | 5 | 5 |
| KIN-31 | partial | answer | 1 | 0.67 | 4 | 3 | 4 | 4 |
| KIN-32 | none | refuse | 1 | - | 5 | 4 | 5 | 4 |
| KIN-33 | none | refuse | 1 | - | 5 | 4 | 5 | 4 |
| KIN-34 | partial | answer | 1 | 0.50 | 4 | 3 | 5 | 4 |
| KIN-35 | none | refuse | 1 | - | 4 | 4 | 5 | 4 |
| KIN-36 | partial | answer | 1 | 1.00 | 4 | 3 | 4 | 4 |
| KIN-37 | partial | answer | 1 | 0.67 | 5 | 3 | 5 | 5 |
| KIN-38 | partial | answer | 1 | 0.50 | 5 | 3 | 3 | 5 |
| KIN-39 | partial | answer | 1 | 0.50 | 4 | 3 | 5 | 4 |
| KIN-40 | partial | answer | 1 | 0.50 | 3 | 3 | 3 | 4 |
| KIN-41 | partial | answer | 1 | 1.00 | 5 | 3 | 4 | 5 |
