# End-to-end 답변 평가 리포트

- 실행: 2026-09-25T07:56:53+00:00 / 커밋 `2894de5` / dirty `true`
- 문항: 41개 / 생성·Judge temperature 0
- 답변·Judge 모델: `gemini-3.8-flash` / 같은 모델 Judge 사용(한계는 `decision/evaluation.md`)
- 결정론적 지표: answerability, citation 형식, Gold 근거 좌표와 인용 청크의 일치
- 의미 지표: 참고 정답과 실제 인용 문맥을 이용한 0–4점 LLM Judge

## 전체

| 영역 | 지표 | 결과 |
|---|---|---:|
| 거부 | Answerability accuracy | 0.976 |
| 거부 | Answerable recall | 1.000 |
| 거부 | Refusal recall | 0.800 (4/5) |
| 거부 | False answer rate | 0.200 |
| 인용 | Citation integrity | 0.561 |
| 인용 | Citation presence | 0.878 |
| 인용 | Gold evidence recall | 0.745 |
| 인용 | Gold evidence precision | 0.784 |
| 인용 | Gold evidence coverage | 0.769 |
| 답변(0–4) | Correctness | 3.439 |
| 답변(0–4) | Completeness | 3.341 |
| 답변(0–4) | Faithfulness | 3.976 |
| 답변(0–4) | Partial handling | 3.944 |

## 그룹별

| 그룹 | 문항 | Answerability | Citation integrity | Correctness | Completeness | Faithfulness |
|---|---:|---:|---:|---:|---:|---:|
| factoid | 15 | 1.000 | 0.600 | 3.80 | 3.87 | 3.93 |
| multi_hop | 13 | 1.000 | 0.385 | 3.08 | 2.92 | 4.00 |
| procedural | 7 | 1.000 | 0.571 | 3.14 | 2.71 | 4.00 |
| summary | 1 | 1.000 | 1.000 | 4.00 | 3.00 | 4.00 |
| unanswerable | 5 | 0.800 | 0.800 | 3.60 | 3.80 | 4.00 |
| full | 18 | 1.000 | 0.389 | 3.17 | 3.00 | 4.00 |
| none | 5 | 0.800 | 0.800 | 3.60 | 3.80 | 4.00 |
| partial | 18 | 1.000 | 0.667 | 3.67 | 3.56 | 3.94 |

## 문항별

| id | Gold | 예측 | Citation | Evidence recall | 정답성 | 충실성 |
|---|---|---|---:|---:|---:|---:|
| KIN-01 | full | answer | 0 | 0.60 | 4 | 4 |
| KIN-02 | partial | answer | 1 | 1.00 | 4 | 4 |
| KIN-03 | partial | answer | 1 | 1.00 | 4 | 4 |
| KIN-04 | full | answer | 1 | 1.00 | 4 | 4 |
| KIN-05 | full | answer | 0 | 1.00 | 4 | 4 |
| KIN-06 | partial | answer | 0 | 1.00 | 4 | 4 |
| KIN-07 | full | answer | 0 | 1.00 | 4 | 4 |
| KIN-08 | full | answer | 1 | 1.00 | 3 | 4 |
| KIN-09 | full | answer | 0 | 0.00 | 1 | 4 |
| KIN-10 | full | answer | 1 | 0.57 | 3 | 4 |
| KIN-11 | partial | answer | 1 | 0.75 | 4 | 4 |
| KIN-12 | full | answer | 0 | 0.33 | 0 | 4 |
| KIN-13 | none | answer | 0 | - | 4 | 4 |
| KIN-14 | full | answer | 1 | 0.33 | 3 | 4 |
| KIN-15 | partial | answer | 0 | 0.80 | 3 | 4 |
| KIN-16 | full | answer | 1 | 0.67 | 3 | 4 |
| KIN-17 | full | answer | 0 | 1.00 | 4 | 4 |
| KIN-18 | full | answer | 0 | 0.67 | 4 | 4 |
| KIN-19 | full | answer | 0 | 0.33 | 2 | 4 |
| KIN-20 | none | refuse | 1 | - | 4 | 4 |
| KIN-21 | partial | answer | 0 | 1.00 | 3 | 3 |
| KIN-22 | full | answer | 1 | 0.33 | 3 | 4 |
| KIN-23 | full | answer | 0 | 0.50 | 3 | 4 |
| KIN-24 | partial | answer | 0 | 0.67 | 4 | 4 |
| KIN-25 | partial | answer | 1 | 1.00 | 4 | 4 |
| KIN-26 | full | answer | 0 | 1.00 | 4 | 4 |
| KIN-27 | full | answer | 0 | 0.75 | 4 | 4 |
| KIN-28 | full | answer | 1 | 1.00 | 4 | 4 |
| KIN-29 | partial | answer | 1 | 1.00 | 4 | 4 |
| KIN-30 | partial | answer | 1 | 1.00 | 4 | 4 |
| KIN-31 | partial | answer | 1 | 0.67 | 4 | 4 |
| KIN-32 | none | refuse | 1 | - | 4 | 4 |
| KIN-33 | none | refuse | 1 | - | 3 | 4 |
| KIN-34 | partial | answer | 1 | 1.00 | 4 | 4 |
| KIN-35 | none | refuse | 1 | - | 3 | 4 |
| KIN-36 | partial | answer | 0 | 1.00 | 2 | 4 |
| KIN-37 | partial | answer | 1 | 0.33 | 4 | 4 |
| KIN-38 | partial | answer | 1 | 0.50 | 4 | 4 |
| KIN-39 | partial | answer | 1 | 0.50 | 3 | 4 |
| KIN-40 | partial | answer | 0 | 0.50 | 3 | 4 |
| KIN-41 | partial | answer | 1 | 1.00 | 4 | 4 |
