# End-to-end 답변 평가 리포트

- 답변 실행: 2026-09-26T01:52:58+00:00 / 커밋 `4a06d77` / dirty `false`
- 문항: 41개 / 답변 temperature 0 / Judge temperature API 기본값 / seed 42
- 답변 모델: `gemini-3.8-flash` / Judge: OpenRouter `openai/gpt-6-sol`
- 결정론적 지표: answerability, citation 형식, Gold 근거 좌표와 인용 청크의 일치
- 의미 지표: 참고 정답과 실제 인용 문맥을 이용한 0–4점 LLM Judge
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
| 인용 | Gold evidence recall | 0.723 |
| 인용 | Gold evidence precision | 0.778 |
| 인용 | Gold evidence coverage | 0.755 |
| 답변(0–4) | Correctness | 3.000 |
| 답변(0–4) | Completeness | 2.585 |
| 답변(0–4) | Faithfulness | 3.220 |
| 답변(0–4) | Partial handling | 3.222 |
| 답변(0–4) | Clarity | 3.488 |
| 가독성 | 평균 답변 길이(자) | 277 |
| 가독성 | 평균 문장 길이(자) | 76 |
| 가독성 | 80자 초과 문장 비율 | 0.429 |
| 가독성 | 인용 자료 원문 복사율 | 0.015 |
| 가독성 | 법조문식 표현 수(답변당) | 0.00 |

## 그룹별

| 그룹 | 문항 | Answerability | Citation integrity | Correctness | Completeness | Faithfulness | Clarity |
|---|---:|---:|---:|---:|---:|---:|---:|
| factoid | 15 | 1.000 | 1.000 | 3.20 | 2.93 | 3.27 | 3.67 |
| multi_hop | 13 | 1.000 | 1.000 | 2.77 | 2.15 | 3.15 | 3.46 |
| procedural | 7 | 1.000 | 1.000 | 2.71 | 2.29 | 3.29 | 3.14 |
| summary | 1 | 1.000 | 1.000 | 4.00 | 3.00 | 3.00 | 3.00 |
| unanswerable | 5 | 0.800 | 1.000 | 3.20 | 3.00 | 3.20 | 3.60 |
| full | 18 | 1.000 | 1.000 | 3.06 | 2.56 | 3.33 | 3.50 |
| none | 5 | 0.800 | 1.000 | 3.20 | 3.00 | 3.20 | 3.60 |
| partial | 18 | 1.000 | 1.000 | 2.89 | 2.50 | 3.11 | 3.44 |

## 문항별

| id | Gold | 예측 | Citation | Evidence recall | 정답성 | 완전성 | 충실성 | 이해 용이성 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| KIN-01 | full | answer | 1 | 0.40 | 2 | 2 | 3 | 3 |
| KIN-02 | partial | answer | 1 | 1.00 | 3 | 3 | 3 | 4 |
| KIN-03 | partial | answer | 1 | 0.50 | 2 | 2 | 2 | 3 |
| KIN-04 | full | answer | 1 | 1.00 | 3 | 4 | 3 | 4 |
| KIN-05 | full | answer | 1 | 1.00 | 4 | 3 | 3 | 4 |
| KIN-06 | partial | answer | 1 | 0.75 | 3 | 3 | 3 | 4 |
| KIN-07 | full | answer | 1 | 1.00 | 4 | 4 | 4 | 4 |
| KIN-08 | full | answer | 1 | 1.00 | 3 | 3 | 3 | 3 |
| KIN-09 | full | answer | 1 | 0.00 | 2 | 1 | 3 | 2 |
| KIN-10 | full | answer | 1 | 0.43 | 3 | 2 | 3 | 4 |
| KIN-11 | partial | answer | 1 | 0.75 | 2 | 2 | 3 | 3 |
| KIN-12 | full | answer | 1 | 0.67 | 4 | 3 | 4 | 4 |
| KIN-13 | none | answer | 1 | - | 3 | 3 | 4 | 2 |
| KIN-14 | full | answer | 1 | 0.67 | 2 | 2 | 4 | 2 |
| KIN-15 | partial | answer | 1 | 0.80 | 3 | 2 | 4 | 3 |
| KIN-16 | full | answer | 1 | 0.67 | 2 | 2 | 3 | 3 |
| KIN-17 | full | answer | 1 | 0.33 | 3 | 4 | 3 | 4 |
| KIN-18 | full | answer | 1 | 0.67 | 3 | 2 | 4 | 4 |
| KIN-19 | full | answer | 1 | 0.33 | 2 | 2 | 3 | 3 |
| KIN-20 | none | refuse | 1 | - | 4 | 4 | 4 | 4 |
| KIN-21 | partial | answer | 1 | 1.00 | 2 | 2 | 2 | 4 |
| KIN-22 | full | answer | 1 | 0.33 | 3 | 2 | 3 | 4 |
| KIN-23 | full | answer | 1 | 0.50 | 3 | 3 | 3 | 4 |
| KIN-24 | partial | answer | 1 | 0.67 | 3 | 3 | 3 | 3 |
| KIN-25 | partial | answer | 1 | 1.00 | 4 | 4 | 4 | 4 |
| KIN-26 | full | answer | 1 | 1.00 | 4 | 2 | 3 | 4 |
| KIN-27 | full | answer | 1 | 0.75 | 4 | 2 | 4 | 4 |
| KIN-28 | full | answer | 1 | 1.00 | 4 | 3 | 4 | 3 |
| KIN-29 | partial | answer | 1 | 1.00 | 4 | 3 | 4 | 4 |
| KIN-30 | partial | answer | 1 | 1.00 | 3 | 2 | 4 | 4 |
| KIN-31 | partial | answer | 1 | 0.67 | 3 | 2 | 4 | 3 |
| KIN-32 | none | refuse | 1 | - | 4 | 4 | 4 | 4 |
| KIN-33 | none | refuse | 1 | - | 2 | 2 | 2 | 4 |
| KIN-34 | partial | answer | 1 | 1.00 | 3 | 2 | 3 | 4 |
| KIN-35 | none | refuse | 1 | - | 3 | 2 | 2 | 4 |
| KIN-36 | partial | answer | 1 | 1.00 | 2 | 2 | 3 | 2 |
| KIN-37 | partial | answer | 1 | 0.67 | 4 | 3 | 3 | 3 |
| KIN-38 | partial | answer | 1 | 0.50 | 3 | 2 | 3 | 4 |
| KIN-39 | partial | answer | 1 | 0.50 | 3 | 2 | 4 | 3 |
| KIN-40 | partial | answer | 1 | 0.50 | 2 | 2 | 2 | 4 |
| KIN-41 | partial | answer | 1 | 1.00 | 3 | 4 | 2 | 3 |
