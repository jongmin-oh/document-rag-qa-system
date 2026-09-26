# 모델 선정

> 결론: 임베딩은 OpenRouter의 **pplx-embed-v1-4b**(`perplexity/pplx-embed-v1-4b`), 답변 생성과 질의 재작성은 Gemini API의
> **Gemini 3.7 Flash**(`gemini-3.7-flash`, thinking `low`)를 쓴다. (확인일: 2026-09-26)

## 1. 임베딩: pplx-embed-v1-4b

정부 문서 검색에는 다국어 종합 점수보다 **한국어 검색 성능**이 직접적인 기준이다. Korean-MTEB v2의 Dense 검색 평균에서
pplx-embed-v1-4b가 82.79점으로 1위였고, 서비스와 가까운 PublicHealthQA 89.54점, LawIRKo 76.44점을 기록해 후보로 골랐다.
이는 Qwen3-Embedding-4B의 평균 81.37점보다 높고 법령 검색은 사실상 동률이다.

- OpenRouter 모델 ID는 `perplexity/pplx-embed-v1-4b`다. Judge와 API 키·엔드포인트를 공유해 별도 서빙이 필요 없다.
- 가격은 입력 $0.03/M 토큰, 입력 한도는 32,000토큰이다. 네이티브 2,560차원 벡터를 L2 정규화해 코사인 검색에 쓴다.
- 모델이 별도 instruction을 요구하지 않으므로 질의는 그대로, 문서는 제목 경로와 본문을 함께 임베딩한다.
- Perplexity 단일 제공이라 제공자별 양자화 편차는 없지만 장애 시 대체 제공자가 없다. OpenAI SDK의 재시도를 적용한다.

### Gold Set 검증 (Gemini Embedding 2에서 변경)

이전 임베딩 `gemini-embedding-2`(3,072차원, $0.20/M)와 같은 청킹·하이브리드 조건, 같은 재작성 질의(이전 리포트에 저장된
Gemini 3.8 Flash 재작성 결과)로 검색만 비교했다. 재작성 질의를 고정해 임베딩 차이만 남겼다.

| 임베딩 | Recall@1 | Recall@5 | Hit@5 | Coverage@5 | Recall@10 |
|---|---:|---:|---:|---:|---:|
| gemini-embedding-2 | 0.490 | 0.769 | 0.972 | 0.799 | 0.885 |
| pplx-embed-v1-4b | 0.443 | 0.811 | 1.000 | 0.824 | 0.875 |

- Recall@5는 문항 단위로 5개 개선, 2개 악화다. 36문항이라 차이가 작고 Recall@1은 오히려 낮아, "확실히 낫다"보다
  **동등 이상**으로 판단한다.
- 품질이 떨어지지 않으면서 가격이 약 1/7이라 채택했다.
- Korean-MTEB v2에 없는 Qwen3-Embedding-8B와는 비교하지 않았다. 장애나 품질 열세가 확인되면 OpenRouter 안에서
  Qwen3-Embedding으로 전환할 수 있다. 모델 교체 시 문서 전체를 다시 임베딩한다.

## 2. 답변 생성 LLM: Gemini 3.7 Flash

정부 문서 RAG에서는 범용 지식보다 **검색 문서에만 근거해 답하는 능력**을 우선한다. 이를 직접 측정하는 FACTS Grounding
리더보드에서 Gemini 3.7 Flash가 6위여서 후보로 골랐고, Gold Set 비교로 채택했다.

- 답변 생성과 검색 전 질의 재작성(`chunking_strategy.md` 4절 H4)에 같은 모델을 쓴다.
- Gemini API로 직접 호출하고 temperature 0, seed 42, thinking `low`, JSON Schema 구조화 출력(`{answerable, answer}`)을 쓴다.
- 가격은 입력 $0.75/M, 출력 $3.75/M 토큰이다. 질문당 재작성·답변 2회 호출로 약 1센트 미만이다.

### Gold Set 비교 (Gemma 4 31B에서 변경)

처음에는 FACTS Grounding 80.7%로 최상위권이고 단가가 낮은(입력 $0.09/M, 출력 $0.34/M) OpenRouter의 Gemma 4 31B를 채택했다.
Gold Set으로 다시 측정하자 근거 충실도가 이전 Gemini 3.8 Flash보다 낮아 바꿨다.

LLM 차이만 보려고 검색 결과를 고정했다. 답변 비교는 이전 리포트에 저장된 top-5를 그대로 넣었고, 검색 비교는 pplx 임베딩에
각 모델의 재작성 질의를 넣었다. Judge는 모두 같은 `openai/gpt-6-sol`과 rubric이다(점수 평균은 full·partial 36문항).

| 지표 | Gemini 3.8 Flash (low) | Gemma 4 31B (thinking 끔) | Gemma 4 31B (thinking 켬) | **Gemini 3.7 Flash (low)** |
|---|---:|---:|---:|---:|
| Correctness | 4.000 | 3.944 | 4.056 | **4.306** |
| Completeness | 3.222 | 3.139 | 3.139 | **3.500** |
| Faithfulness | 4.028 | 3.694 | 3.750 | **4.111** |
| Partial handling | 4.000 | 3.056 | 3.667 | **4.167** |
| Clarity | 4.417 | 4.528 | **4.639** | 4.417 |
| Answerability accuracy | 0.976 | 0.976 | 0.951 | **1.000** |
| 재작성 → 검색 Recall@5 | 0.811 | 0.726 | 0.737 | 0.807 |
| 응답 시간 중앙값 (재작성 / 답변) | – | 1.3초 / 5.2초 | 15.5초 / 29.0초 | 2.3초 / 3.2초 |

- Gemma(thinking 끔)는 자료에 없는 내용을 단정하고(KIN-31 "퇴직금을 받아도 아무 문제 없다") 모르는 부분을 밝히지 않아
  faithfulness와 partial handling이 떨어졌다. 재작성에서도 질문을 문서 용어("구직급여 수급자격 인정")로 바꾸지 못했다.
- Gemma의 thinking은 켜기·끄기만 되고 단계 조절(`effort`)은 무시됐다. 켜면 partial handling이 회복되지만 여전히 Gemini보다
  낮고, 응답 시간이 질문당 중앙값 약 45초로 서비스에 쓸 수 없다.
- Gemini 3.7 Flash는 문항 단위로 3.8 대비 correctness 13개 개선·3개 악화, completeness 10개 개선·2개 악화다. faithfulness는
  11개 개선·9개 악화로 비슷하다. 3.8과의 차이는 실행 간 변동 폭 근처이므로 "3.8 이상이고 가격이 같다"로 판단한다.
- 조건마다 한 번씩 실행했다. Gemma와의 차이는 커서 결론이 바뀌지 않지만, 작은 차이는 경향으로만 읽는다.

**OpenRouter 대신 Gemini API를 쓰는 이유**: OpenRouter에서 ZDR 조건을 만족하는 Gemini 제공자는 Google Vertex뿐인데,
Vertex 엔드포인트는 `temperature`를 지원하지 않는다. Gemini API로 직접 호출하면 temperature 0과 thinking `low`를
이전 기준선과 같게 지정할 수 있다.

## 3. 주의할 점

- **데이터 보안**: 임베딩·Judge 요청(OpenRouter)은 ZDR과 데이터 수집 거부를 강제하지만, 재작성·답변 요청(Gemini API 직접
  호출)에는 ZDR이 적용되지 않는다. 사용자 질문이 Google로 직접 전송되므로 운영 전 유료 등급의 데이터 처리 조건과 기관 보안
  정책의 허용 여부를 확인한다. 두 경로 모두 외부 전송 자체는 발생한다.
- **모델 수명**: Gemini 3.7 Flash는 3.8보다 이전 세대(2026-08 출시)다. 지원 종료가 공지되면 3.8 등 후속 모델을 같은 방식으로
  비교해 옮긴다.
- **Judge 모델**: 답변 모델과 분리해 OpenRouter의 `openai/gpt-6-sol`을 쓴다. 처음 쓴 `openai/gpt-5.4-mini`에서 판단력을 우선해 상위 모델로 바꿨다. 교체 전후 비교는 `evaluation.md` 4절.
- **영어 벤치마크의 한계**: FACTS Grounding과 Korean-MTEB는 1차 선별 근거다. Gemma 4 31B는 FACTS 최상위권이었지만 이
  Gold Set에서는 재현되지 않았다. 최종 선택은 프로젝트 Gold Set으로 한다.

## 참고

- [Korean-MTEB v2 리더보드](https://github.com/OnAnd0n/ko-embedding-leaderboard)
- [pplx-embed-v1-4b – OpenRouter](https://openrouter.ai/perplexity/pplx-embed-v1-4b), [모델 카드](https://huggingface.co/perplexity-ai/pplx-embed-v1-4b)
- [FACTS Grounding Leaderboard](https://www.kaggle.com/benchmarks/google/facts-grounding)
- [Gemini API 가격](https://ai.google.dev/gemini-api/docs/pricing)
- [OpenRouter GPT-6 Sol](https://openrouter.ai/openai/gpt-6-sol), [OpenRouter Structured Outputs](https://openrouter.ai/docs/guides/features/structured-outputs)
