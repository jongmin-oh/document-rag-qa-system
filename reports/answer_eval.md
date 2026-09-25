# End-to-end 답변 평가 리포트

- 답변 실행: 2026-09-25T12:36:21+00:00 / 커밋 `3afff43` / dirty `false`
- 문항: 41개 / 답변 temperature 0 / Judge temperature API 기본값 / seed 42
- 답변 모델: `gemini-3.8-flash` / Judge: OpenRouter `openai/gpt-5.4-mini`
- 결정론적 지표: answerability, citation 형식, Gold 근거 좌표와 인용 청크의 일치
- 의미 지표: 참고 정답과 실제 인용 문맥을 이용한 0–4점 LLM Judge
- citation 객체는 답변 본문의 `[n]`·`[n, m]`을 서버가 파싱해 생성

## 전체

| 영역 | 지표 | 결과 |
|---|---|---:|
| 거부 | Answerability accuracy | 0.951 |
| 거부 | Answerable recall | 0.972 |
| 거부 | Refusal recall | 0.800 (4/5) |
| 거부 | False answer rate | 0.200 |
| 인용 | Citation integrity | 1.000 |
| 인용 | Citation presence | 1.000 |
| 인용 | Gold evidence recall | 0.763 |
| 인용 | Gold evidence precision | 0.763 |
| 인용 | Gold evidence coverage | 0.781 |
| 답변(0–4) | Correctness | 3.439 |
| 답변(0–4) | Completeness | 3.098 |
| 답변(0–4) | Faithfulness | 3.293 |
| 답변(0–4) | Partial handling | 3.389 |

## 그룹별

| 그룹 | 문항 | Answerability | Citation integrity | Correctness | Completeness | Faithfulness |
|---|---:|---:|---:|---:|---:|---:|
| factoid | 15 | 1.000 | 1.000 | 3.67 | 3.47 | 3.60 |
| multi_hop | 13 | 0.923 | 1.000 | 3.38 | 2.69 | 2.92 |
| procedural | 7 | 1.000 | 1.000 | 3.57 | 3.43 | 3.43 |
| summary | 1 | 1.000 | 1.000 | 4.00 | 4.00 | 4.00 |
| unanswerable | 5 | 0.800 | 1.000 | 2.60 | 2.40 | 3.00 |
| full | 18 | 1.000 | 1.000 | 3.78 | 3.39 | 3.22 |
| none | 5 | 0.800 | 1.000 | 2.60 | 2.40 | 3.00 |
| partial | 18 | 0.944 | 1.000 | 3.33 | 3.00 | 3.44 |

## 문항별

| id | Gold | 예측 | Citation | Evidence recall | 정답성 | 충실성 |
|---|---|---|---:|---:|---:|---:|
| KIN-01 | full | answer | 1 | 0.40 | 4 | 2 |
| KIN-02 | partial | answer | 1 | 1.00 | 4 | 3 |
| KIN-03 | partial | answer | 1 | 0.50 | 2 | 2 |
| KIN-04 | full | answer | 1 | 1.00 | 4 | 3 |
| KIN-05 | full | answer | 1 | 1.00 | 4 | 4 |
| KIN-06 | partial | answer | 1 | 1.00 | 4 | 4 |
| KIN-07 | full | answer | 1 | 1.00 | 4 | 4 |
| KIN-08 | full | answer | 1 | 1.00 | 4 | 4 |
| KIN-09 | full | answer | 1 | 0.00 | 3 | 3 |
| KIN-10 | full | answer | 1 | 0.57 | 4 | 3 |
| KIN-11 | partial | answer | 1 | 1.00 | 3 | 4 |
| KIN-12 | full | answer | 1 | 0.67 | 4 | 4 |
| KIN-13 | none | answer | 1 | - | 2 | 2 |
| KIN-14 | full | answer | 1 | 0.67 | 4 | 4 |
| KIN-15 | partial | answer | 1 | 0.80 | 4 | 4 |
| KIN-16 | full | answer | 1 | 0.67 | 3 | 3 |
| KIN-17 | full | answer | 1 | 1.00 | 4 | 4 |
| KIN-18 | full | answer | 1 | 0.67 | 4 | 3 |
| KIN-19 | full | answer | 1 | 0.33 | 4 | 2 |
| KIN-20 | none | refuse | 1 | - | 4 | 4 |
| KIN-21 | partial | answer | 1 | 1.00 | 4 | 4 |
| KIN-22 | full | answer | 1 | 0.33 | 3 | 2 |
| KIN-23 | full | answer | 1 | 0.50 | 4 | 4 |
| KIN-24 | partial | answer | 1 | 0.67 | 4 | 4 |
| KIN-25 | partial | answer | 1 | 1.00 | 3 | 4 |
| KIN-26 | full | answer | 1 | 1.00 | 4 | 3 |
| KIN-27 | full | answer | 1 | 0.75 | 3 | 2 |
| KIN-28 | full | answer | 1 | 1.00 | 4 | 4 |
| KIN-29 | partial | answer | 1 | 1.00 | 4 | 4 |
| KIN-30 | partial | answer | 1 | 1.00 | 4 | 4 |
| KIN-31 | partial | refuse | 1 | - | 2 | 4 |
| KIN-32 | none | refuse | 1 | - | 4 | 4 |
| KIN-33 | none | refuse | 1 | - | 1 | 4 |
| KIN-34 | partial | answer | 1 | 1.00 | 3 | 3 |
| KIN-35 | none | refuse | 1 | - | 2 | 1 |
| KIN-36 | partial | answer | 1 | 1.00 | 3 | 2 |
| KIN-37 | partial | answer | 1 | 0.67 | 4 | 4 |
| KIN-38 | partial | answer | 1 | 0.50 | 3 | 2 |
| KIN-39 | partial | answer | 1 | 0.50 | 3 | 4 |
| KIN-40 | partial | answer | 1 | 0.50 | 2 | 2 |
| KIN-41 | partial | answer | 1 | 1.00 | 4 | 4 |
