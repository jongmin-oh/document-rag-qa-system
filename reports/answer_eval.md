# End-to-end 답변 평가 리포트

- 답변 실행: 2026-09-25T14:39:56+00:00 / 커밋 `2297dc9` / dirty `false`
- 문항: 41개 / 답변 temperature 0 / Judge temperature API 기본값 / seed 42
- 답변 모델: `gemini-3.8-flash` / Judge: OpenRouter `openai/gpt-6-sol`
- 결정론적 지표: answerability, citation 형식, Gold 근거 좌표와 인용 청크의 일치
- 의미 지표: 참고 정답과 실제 인용 문맥을 이용한 0–4점 LLM Judge
- citation 객체는 답변 본문의 `[n]`·`[n, m]`을 서버가 파싱해 생성

## 전체

| 영역 | 지표 | 결과 |
|---|---|---:|
| 거부 | Answerability accuracy | 1.000 |
| 거부 | Answerable recall | 1.000 |
| 거부 | Refusal recall | 1.000 (5/5) |
| 거부 | False answer rate | 0.000 |
| 인용 | Citation integrity | 1.000 |
| 인용 | Citation presence | 1.000 |
| 인용 | Gold evidence recall | 0.727 |
| 인용 | Gold evidence precision | 0.819 |
| 인용 | Gold evidence coverage | 0.771 |
| 답변(0–4) | Correctness | 3.146 |
| 답변(0–4) | Completeness | 2.488 |
| 답변(0–4) | Faithfulness | 3.293 |
| 답변(0–4) | Partial handling | 2.778 |
| 답변(0–4) | Clarity | 3.634 |
| 가독성 | 평균 답변 길이(자) | 224 |
| 가독성 | 평균 문장 길이(자) | 67 |
| 가독성 | 80자 초과 문장 비율 | 0.227 |
| 가독성 | 인용 자료 원문 복사율 | 0.029 |
| 가독성 | 법조문식 표현 수(답변당) | 0.00 |

## 그룹별

| 그룹 | 문항 | Answerability | Citation integrity | Correctness | Completeness | Faithfulness | Clarity |
|---|---:|---:|---:|---:|---:|---:|---:|
| factoid | 15 | 1.000 | 1.000 | 3.40 | 2.73 | 3.47 | 3.73 |
| multi_hop | 13 | 1.000 | 1.000 | 2.92 | 2.15 | 3.15 | 3.54 |
| procedural | 7 | 1.000 | 1.000 | 2.86 | 2.00 | 3.29 | 3.57 |
| summary | 1 | 1.000 | 1.000 | 4.00 | 3.00 | 4.00 | 4.00 |
| unanswerable | 5 | 1.000 | 1.000 | 3.20 | 3.20 | 3.00 | 3.60 |
| full | 18 | 1.000 | 1.000 | 3.28 | 2.56 | 3.61 | 3.78 |
| none | 5 | 1.000 | 1.000 | 3.20 | 3.20 | 3.00 | 3.60 |
| partial | 18 | 1.000 | 1.000 | 3.00 | 2.22 | 3.06 | 3.50 |

## 문항별

| id | Gold | 예측 | Citation | Evidence recall | 정답성 | 완전성 | 충실성 | 이해 용이성 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| KIN-01 | full | answer | 1 | 0.40 | 2 | 2 | 3 | 4 |
| KIN-02 | partial | answer | 1 | 1.00 | 3 | 2 | 3 | 3 |
| KIN-03 | partial | answer | 1 | 0.50 | 2 | 2 | 2 | 3 |
| KIN-04 | full | answer | 1 | 1.00 | 4 | 3 | 4 | 4 |
| KIN-05 | full | answer | 1 | 1.00 | 4 | 3 | 4 | 4 |
| KIN-06 | partial | answer | 1 | 1.00 | 4 | 3 | 4 | 4 |
| KIN-07 | full | answer | 1 | 1.00 | 4 | 4 | 4 | 4 |
| KIN-08 | full | answer | 1 | 1.00 | 3 | 3 | 4 | 3 |
| KIN-09 | full | answer | 1 | 0.00 | 1 | 1 | 2 | 3 |
| KIN-10 | full | answer | 1 | 0.57 | 3 | 2 | 3 | 4 |
| KIN-11 | partial | answer | 1 | 0.50 | 2 | 1 | 2 | 3 |
| KIN-12 | full | answer | 1 | 1.00 | 4 | 3 | 4 | 4 |
| KIN-13 | none | refuse | 1 | - | 4 | 4 | 4 | 4 |
| KIN-14 | full | answer | 1 | 0.67 | 4 | 2 | 4 | 4 |
| KIN-15 | partial | answer | 1 | 0.80 | 2 | 2 | 2 | 3 |
| KIN-16 | full | answer | 1 | 0.67 | 2 | 2 | 3 | 3 |
| KIN-17 | full | answer | 1 | 0.33 | 4 | 4 | 4 | 4 |
| KIN-18 | full | answer | 1 | 0.67 | 4 | 2 | 4 | 4 |
| KIN-19 | full | answer | 1 | 0.33 | 2 | 2 | 4 | 3 |
| KIN-20 | none | refuse | 1 | - | 4 | 4 | 4 | 4 |
| KIN-21 | partial | answer | 1 | 1.00 | 3 | 2 | 3 | 4 |
| KIN-22 | full | answer | 1 | 0.33 | 3 | 2 | 3 | 4 |
| KIN-23 | full | answer | 1 | 0.50 | 3 | 2 | 3 | 4 |
| KIN-24 | partial | answer | 1 | 0.67 | 4 | 3 | 4 | 4 |
| KIN-25 | partial | answer | 1 | 1.00 | 2 | 2 | 2 | 4 |
| KIN-26 | full | answer | 1 | 1.00 | 4 | 3 | 4 | 4 |
| KIN-27 | full | answer | 1 | 0.75 | 4 | 2 | 4 | 4 |
| KIN-28 | full | answer | 1 | 1.00 | 4 | 4 | 4 | 4 |
| KIN-29 | partial | answer | 1 | 1.00 | 3 | 2 | 3 | 3 |
| KIN-30 | partial | answer | 1 | 1.00 | 2 | 2 | 3 | 4 |
| KIN-31 | partial | answer | 1 | 0.67 | 3 | 2 | 3 | 3 |
| KIN-32 | none | refuse | 1 | - | 4 | 4 | 3 | 4 |
| KIN-33 | none | refuse | 1 | - | 2 | 2 | 2 | 3 |
| KIN-34 | partial | answer | 1 | 1.00 | 3 | 2 | 3 | 4 |
| KIN-35 | none | refuse | 1 | - | 2 | 2 | 2 | 3 |
| KIN-36 | partial | answer | 1 | 1.00 | 4 | 3 | 4 | 4 |
| KIN-37 | partial | answer | 1 | 0.33 | 4 | 3 | 4 | 4 |
| KIN-38 | partial | answer | 1 | 0.50 | 3 | 2 | 3 | 4 |
| KIN-39 | partial | answer | 1 | 0.50 | 4 | 3 | 4 | 4 |
| KIN-40 | partial | answer | 1 | 0.50 | 2 | 1 | 2 | 2 |
| KIN-41 | partial | answer | 1 | 1.00 | 4 | 3 | 4 | 3 |
