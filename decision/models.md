# 모델 선정

> 결론: 임베딩은 **Gemini Embedding 2**(`gemini-embedding-2`), 답변 생성은 **Gemini 3.8 Flash**(`gemini-3.8-flash`)를 쓴다.
> 두 모델 모두 Gemini API 키 하나로 쓸 수 있고, 정식 출시(GA) 모델 ID로 고정한다. (확인일: 2026-09-25)

## 1. 임베딩: Gemini Embedding 2

### 선정 기준

corpus가 청크 약 120개(약 10만 토큰)라 어떤 모델을 써도 인덱싱 비용은 0.05달러 미만이다. 그래서 비용이 아니라 **한국어 검색 품질, 재현성(버전 고정), 운영 편의**로 고른다. 로컬 모델 대신 외부 API를 쓰는 이유는 설치·GPU 없이 누구나 같은 결과를 재현할 수 있어서다.

### 후보 비교 (가격은 2026년 7월 기준)

| 모델 | 가격(1M 토큰) | 최대 입력 | 근거 |
|---|---|---|---|
| **Gemini Embedding 2** | $0.20 | 8,192 토큰 | 논문 기준 MMTEB(다국어) 69.9. 이전 gemini-embedding-001은 68.4, Voyage-3.5는 58.5 |
| gemini-embedding-001 | $0.15 | 2,048 토큰 | 이전 세대 GA 모델 |
| voyage-4 | $0.06 | 32,000 토큰 | 29개 데이터셋에서 Gemini 001·OpenAI 3-large보다 높다는 **벤더 자체 주장** |
| OpenAI text-embedding-3-large | $0.13 | 8,191 토큰 | 2024년 모델. Voyage 비교에서 14% 낮게 나옴 |

- **한국어 비교 자료가 없다.** 한국어 검색 리더보드(MTEB-ko-retrieval)는 오픈소스 모델만 다루고 상용 API는 빠져 있다. 그래서 다국어 벤치마크(MMTEB)로 1차 선정한다.
- 입력 한도(8,192 토큰)가 청크 크기(최대 약 1,500자)에 넉넉하다.

### 사용 방법

- Gemini Embedding 2는 `task_type` 파라미터가 없고, **질의와 문서를 프롬프트 접두어로 구분**한다.
  - 질의: `task: search result | query: {질문}`
  - 문서: `title: {제목} | text: {청크 본문}`
- 차원은 기본값 3,072를 그대로 쓴다. 청크가 120개뿐이라 저장·검색 비용이 문제가 되지 않는다.

### 확인 계획

Gold Set이 준비되면 비교 모델 1개(voyage-4 또는 text-embedding-3-large)와 **검색 지표만** 비교해, 벤치마크 점수로 고른 선택을 우리 데이터로 확인한다. 청킹·검색 실험(`chunking_strategy.md` 4절)은 임베딩 모델을 고정한 채 진행했다. 청킹과 임베딩을 동시에 바꾸면 효과를 구분할 수 없기 때문이다. 임베딩 모델 비교는 채택한 C_hybrid 위에서 한다.

## 2. 답변 생성 LLM: Gemini 3.8 Flash

- 답변 생성과 검색 전 질의 재작성(`chunking_strategy.md` 4절 H4)에 같은 모델을 쓴다.
- 모델 ID `gemini-3.8-flash`, 2026년 9월 GA. 입력 1,048,576 토큰, 출력 65,536 토큰.
- 가격(유료 등급, 1M 토큰): 입력 $0.75, 출력 $3.75 (2026년 12월 31일까지. 2027년부터 각각 $1.50, $7.50).
- Flash급을 고른 이유: 답변은 검색된 청크 몇 개만 근거로 하므로 최상위 모델이 필요하지 않고, Gold Set 전체를 반복 평가하는 비용과 속도가 중요하다.
- 재현성: temperature 0으로 고정하고, 응답의 `model_version`을 평가 리포트에 기록한다. thinking은 `low`/`medium`/`high`만 지원한다(`minimal` 불가).

## 3. 주의할 점

- **무료 등급 데이터 사용**: 무료 등급에서는 입력 내용이 Google 제품 개선에 쓰인다. 공개 문서만 다루므로 문제는 없지만, 실제 사용자 질문을 받는 운영 환경에서는 유료 등급을 써야 한다.
- **Judge 모델**: 답변 모델과 분리해 OpenRouter의 `openai/gpt-5.4-mini`를 쓴다. 구조화 출력 지원과 성능·비용 균형을 근거로 골랐으며, 사람 표본 평가로 자동 Judge와의 일치도를 별도 확인한다.
- **API 모델 변경**: GA 모델 ID도 제공사 사정으로 동작이 바뀔 수 있다. 평가 리포트에 모델 ID와 응답의 `model_version`을 함께 남긴다.

## 참고

- [Gemini Embedding 2 모델 문서](https://ai.google.dev/gemini-api/docs/models/gemini-embedding-2), [Embeddings 가이드](https://ai.google.dev/gemini-api/docs/embeddings)
- [Gemini Embedding 2 논문 (arXiv 2605.27295)](https://arxiv.org/html/2605.27295)
- [Gemini 3.8 Flash 모델 문서](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash), [Gemini API 가격](https://ai.google.dev/gemini-api/docs/pricing)
- [OpenRouter GPT-5.4 Mini](https://openrouter.ai/openai/gpt-5.4-mini), [OpenRouter Structured Outputs](https://openrouter.ai/docs/guides/features/structured-outputs)
- [Voyage 4 model family](https://blog.voyageai.com/2026/01/15/voyage-4/)
- [Embedding Model Pricing (TokenCost, 2026.7)](https://tokencost.app/embeddings)
- [Embedding Model Selection Guide – Korean benchmarks](https://www.data-dynamics.io/en/blog/embedding-model-guide)
