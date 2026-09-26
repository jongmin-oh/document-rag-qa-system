# Eval Harness

> 결론: 평가는 **Gold Set 고정 → 검색 평가 → 답변 평가 → 리포트 → 커밋 기록** 다섯 단계로 돌린다. 변경을 비교할 때는
> **바꾼 변수 하나만 남기고 나머지 입력을 고정**하고, **같은 Judge로** 채점하며, 평균과 함께 **문항 단위 개선·악화 수**를 본다.
> 지표 정의와 Judge 설계는 `evaluation.md`, 검색 지표는 `chunking_strategy.md` 4절에 있다. 이 문서는 절차만 다룬다.

## 1. 구성 요소

| 단계 | 명령 | 입력 | 출력 |
|---|---|---|---|
| Gold Set 빌드 | `python -m evaluation.gold.build` | `evaluation/data/gold/gold_set.yaml` (사람이 작성한 질문·참고 정답·근거 인용문) | `evaluation/data/processed/gold_set.jsonl` (근거를 canonical text 문자 구간으로 변환) |
| 인덱스 빌드 | `python -m preprocessing.index.build` | 청크 | `app/data/processed/embeddings.*` |
| 검색 평가 | `python -m evaluation.retrieval` | Gold Set(none 제외 36문항), 인덱스 | `evaluation/reports/retrieval.{json,md}` |
| 답변 평가 | `python -m evaluation.answer` | Gold Set 41문항, 인덱스 | `evaluation/reports/answer_eval.{json,md}` |
| 재채점 | `python -m evaluation.answer --judge-only` | 저장된 `evaluation/reports/answer_eval.json` | 같은 답변에 Judge 점수와 결정론 지표만 다시 계산 |

## 2. 실행 단계

### Step 1. 입력 고정

- **Gold Set**: 근거를 청크 ID가 아닌 문자 구간으로 적어, 청킹·임베딩을 바꿔도 같은 정답지로 채점한다(`gold_set.md`).
- **모델·설정**: 모델 ID, temperature 0, seed 42를 코드(`app/config.py`)에 고정한다. 제공사가 결정론을 보장하지 않으므로
  실제 응답 모델 버전을 리포트에 남긴다.
- **인덱스**: 임베딩 설정과 인덱스가 다르면 실행을 막는다(`index.build.load_index`). 리포트에 인덱스 해시를 남긴다.

### Step 2. 검색 평가

운영과 같은 질의 재작성 → 하이브리드 검색(임베딩 + BM25, RRF)으로 top-k를 뽑고, Gold 근거 구간을 얼마나 덮는지 잰다.

- 지표: Hit·Recall·Coverage·Precision@1/3/5/10. 주 지표는 답변에 넘기는 수와 같은 Recall@5.
- 답할 수 없는(none) 문항은 근거가 없어 뺀다.
- 문항별 재작성 질의와 top-10을 저장한다. 이 질의는 뒤의 임베딩 비교에서 입력으로 재사용한다(3.2).

### Step 3. 답변 평가

운영 경로 전체(재작성 → 검색 → 답변 생성 → citation 파싱)를 실행하고 두 층으로 채점한다.

1. **결정론 지표**: answerability, citation integrity·presence, Gold 근거와 인용 청크의 겹침, 가독성(문장 길이, 원문 복사율 등).
2. **LLM Judge**: 참고 정답과 실제 인용 자료만 보고 5개 축을 1–5점으로 채점한다. Judge 점수는 full·partial 문항만
   평균하고, none 문항은 거부 지표로만 판정한다.

문항마다 재작성 질의, top-5, 답변 원문, 인용, Judge의 근거(`reason`, `unsupported_claims`, `missing_points`)를 trace로 저장한다.
이 trace가 재채점(`--judge-only`)과 LLM 비교(3.2)의 입력이 된다.

### Step 4. 리포트

- **JSON**: 문항별 trace 전체와 `meta`(코드 커밋, dirty 여부, 설정·응답 모델 버전, Judge 프롬프트 해시, 임베딩 모델·차원,
  인덱스 해시, temperature, seed). 재채점하면 `judge_run_at`·`judge_git_commit`이 추가된다.
- **Markdown**: 전체 요약, 그룹별(질문 유형·answerability) 요약, 문항별 표.

### Step 5. 커밋 기록

1. 코드 변경을 먼저 커밋한다(`feat:`/`fix:`).
2. 작업 트리가 깨끗한 상태에서 평가를 돌려 리포트의 `git_dirty`가 false가 되게 한다.
3. 리포트를 따로 커밋한다(`data:`). 리포트가 어느 코드로 생성됐는지 커밋 단위로 추적된다.
4. 결정을 `decision/*.md`에 "무엇이 바뀌었고 왜"로 기록한다.

검색 평가와 답변 평가를 연달아 돌리면 먼저 쓴 리포트 때문에 두 번째 리포트가 `dirty true`가 된다. 이때 바뀐 파일이 리포트뿐이면
커밋 메시지에 그 사실을 적는다.

## 3. 변경 비교 절차

### 3.1 가설

무엇을 왜 바꾸는지, 어떤 지표가 어느 방향으로 움직일지를 먼저 적는다. 예: "LLM을 Gemma에서 Gemini 3.7 Flash로 바꾸면 자료에
없는 내용을 덜 단정해 faithfulness와 partial handling이 오른다."

### 3.2 바꾼 변수만 남기기

전체 파이프라인을 다시 돌리면 재작성·검색·생성의 변동이 모두 섞인다. 바꾼 단계의 **앞 단계 출력을 저장된 값으로 고정**한다.

| 바꾼 것 | 고정하는 입력 | 비교 방법 |
|---|---|---|
| Judge (모델, rubric, 척도) | 답변 | 비교할 모든 조건의 저장된 답변을 `--judge-only`로 재채점 |
| 답변 LLM, 답변 프롬프트 | 검색 결과 | 기준 리포트에 저장된 top-5를 그대로 넣어 답변만 생성하고 채점 |
| 임베딩 모델 | 재작성 질의 | 기준 리포트에 저장된 재작성 질의로 검색만 실행 |
| 재작성 모델·프롬프트 | 임베딩, 인덱스 | 검색 평가 |
| 청킹 | Gold 근거(문자 구간) | 검색 평가. 근거가 청크와 무관해 같은 정답지로 비교된다 |

고정 비교로 효과를 확인한 뒤, 전체 파이프라인을 돌려 실제 운영 조합의 리포트를 만든다.

### 3.3 같은 Judge로만 비교

Judge를 바꾸면 이전 리포트의 점수와 비교하지 않는다. 기준선 답변도 새 Judge로 재채점한다. 같은 답변을 Judge 모델만 바꿔
채점했을 때 두 모델의 점수가 완전히 일치한 비율은 41~54%였다(`evaluation.md` 4절).

### 3.4 판정

- **평균과 문항 단위 변화를 함께 본다.** 평균이 올라도 개선·악화 문항 수가 비슷하면 효과로 보지 않는다.
- **변동 폭과 비교한다.** 측정된 변동:
  - 검색: seed 고정 후 같은 코드 3회 실행에서 Recall@5 0.769~0.783
  - Judge: 글자가 같은 거부 답변(KIN-33)이 실행에 따라 faithfulness 5 또는 3
- **결정론 지표는 원시 개수로 본다.** none이 5문항이라 1문항이 거부 지표를 20%p 움직인다.
- **채택 기준**: 방향이 일관되고(문항 단위 개선이 악화보다 뚜렷하게 많음), 원인을 문항 수준에서 설명할 수 있어야 한다.
  Judge 점수 0.1~0.3 정도의 차이는 경향으로만 기록한다.

### 3.5 원인 분석

점수가 움직인 문항을 골라 Judge의 `unsupported_claims`·`missing_points`, 재작성 질의, 가독성 지표를 대조한다. 예를 들어
Gemma의 검색 하락은 재작성 질의를 비교해 "문서 용어로 바꾸지 못함"으로, 답변 하락은 Judge 근거를 보고 "자료에 없는 단정"으로
설명했다.

### 3.6 기록

비교표와 판정 이유를 해당 `decision/*.md`에 남긴다. 채택하지 않은 변경은 코드에서 되돌리고, 문서에는 무엇을 시도했고 왜
채택하지 않았는지만 적는다.

## 4. 적용 사례

| 변경 | 비교 방법 | 결과 | 결정 |
|---|---|---|---|
| Judge 척도 0–4 → 1–5, 점수별 기준 추가 | 기준선·H6·H6b 답변을 `--judge-only`로 재채점 | 기준을 넣기 전후로 같은 답변의 점수가 같은 문항은 축마다 25~28/41 | 채택 (`evaluation.md` 3절) |
| none 문항을 Judge 평균에서 제외 | 저장된 점수로 재집계 | none 5문항이 모두 5점이라 평균을 부풀림 | 채택 |
| 거부 문구에서 1350 고정 안내 제거 | 전체 답변 평가 | 거부 4문항 모두 중립 문구 사용. Judge 평균에는 영향 없음(none 제외) | 채택 |
| 임베딩 Gemini Embedding 2 → pplx | 저장된 재작성 질의로 검색 | Recall@5 0.769 → 0.811 (개선 5, 악화 2) | 채택: 동등 이상, 가격 약 1/7 (`models.md` 1절) |
| LLM Gemini 3.8 Flash → Gemma 4 31B | 저장된 top-5로 답변 | faithfulness 4.028 → 3.694, partial handling 4.000 → 3.056 | 되돌림 |
| Gemma thinking 켬 | 같은 방법 + 응답 시간 | partial handling 3.667로 회복, 질문당 중앙값 약 45초 | 채택 안 함 |
| LLM → Gemini 3.7 Flash | 같은 방법 + 응답 시간 | faithfulness 4.111, partial handling 4.167, 답변 중앙값 3.2초 | 채택 (`models.md` 2절) |

## 5. 한계

- **고정 입력 비교가 명령으로 없다.** 3.2의 LLM·임베딩 비교는 저장된 리포트를 읽는 임시 스크립트로 했다. 단일 명령으로
  재현하려면 답변 평가에 "저장된 top-5 사용", 검색 평가에 "저장된 재작성 질의 사용" 옵션이 필요하다.
- **조건마다 한 번씩 실행했다.** 반복 실행으로 조건별 분산을 재지 않았다. 변동 폭은 3.4의 관측값뿐이다.
- **Judge와 답변 프롬프트가 충돌한다.** 답변 프롬프트는 "최종 판단은 고용센터가 한다"는 안내를 요구하지만, Judge는 이를
  인용 자료에 없는 주장으로 보고 faithfulness를 깎는다(KIN-12, 18, 34, 37).
- **사람 채점과 대조하지 않았다.** Judge 점수의 Human Alignment는 설계 의도일 뿐 측정값이 없다.
- **검색 평가와 답변 평가가 재작성을 따로 호출한다.** 같은 커밋에서도 1~2문항은 두 리포트의 top-5가 다를 수 있다.

## 6. 회귀 방지 설계 (미구현)

CI에 연동한다면 비용과 변동을 고려해 지표를 두 종류로 나눈다.

- **게이트(실패 시 머지 차단)**: `pytest`, 결정론 지표. citation integrity 1.000 유지, answerability accuracy와 false answer rate는
  기준 리포트 대비 1문항 이상 악화 시 실패, 검색 Recall@5는 기준에서 변동 폭(약 0.015)을 넘게 떨어지면 실패.
- **추세(차단하지 않음)**: Judge 점수. 실행마다 변동이 있어 게이트로 쓰면 오탐이 잦다. 기준 리포트와의 문항별 차이를 PR 코멘트로 남긴다.
- **실행 조건**: 검색·답변·프롬프트·설정(`app/tasks/qa`, `app/config.py`)이 바뀐 PR에서만 전체 평가를 돌린다. 답변 평가 한 번에
  Gemini 82회, 임베딩 41회, Judge 41회를 호출한다.
