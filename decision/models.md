# 모델 선정

> 결론: 임베딩은 **pplx-embed-v1-4b**(`perplexity/pplx-embed-v1-4b`), 답변 생성과 질의 재작성은 OpenRouter의
> **Gemma 4 31B**(`google/gemma-4-31b-it`)를 쓴다. (확인일: 2026-09-26)

## 1. 임베딩: pplx-embed-v1-4b

정부 문서 검색에는 다국어 종합 점수보다 **한국어 검색 성능**이 직접적인 기준이다. Korean-MTEB v2의 Dense 검색 평균에서
pplx-embed-v1-4b가 82.79점으로 1위였고, 서비스와 가까운 PublicHealthQA 89.54점, LawIRKo 76.44점을 기록해 채택했다.
이는 Qwen3-Embedding-4B의 평균 81.37점보다 높고 법령 검색은 사실상 동률이다.

- OpenRouter 모델 ID는 `perplexity/pplx-embed-v1-4b`다. 생성 LLM과 API 키·엔드포인트를 공유해 별도 서빙이 필요 없다.
- 가격은 입력 $0.03/M 토큰, 입력 한도는 32,000토큰이다. 네이티브 2,560차원 벡터를 L2 정규화해 코사인 검색에 쓴다.
- 모델이 별도 instruction을 요구하지 않으므로 질의는 그대로, 문서는 제목 경로와 본문을 함께 임베딩한다.
- Perplexity 단일 제공이라 제공자별 양자화 편차는 없지만 장애 시 대체 제공자가 없다. OpenAI SDK의 재시도를 적용한다.

### 검증 계획

Korean-MTEB v2는 커뮤니티 리더보드이고 Qwen3-Embedding-8B가 빠져 있다. 채택을 확정하기 전에 현재 Gold Set 검색 지표로
pplx-embed-v1-4b와 Qwen3-Embedding-8B를 같은 청킹·하이브리드 조건에서 비교한다. 모델 교체 시 문서 전체를 다시 임베딩해야 하며,
장애나 자체 평가 열세가 확인되면 OpenRouter 안에서 Qwen3-Embedding으로 전환한다.

## 2. 답변 생성 LLM: Gemma 4 31B

정부 문서 RAG에서는 범용 지식보다 **검색 문서에만 근거해 답하는 능력**을 우선했다. 이를 직접 측정하는 FACTS Grounding에서
Gemma 4 31B가 80.7%로 최상위권이어서 채택했다. 26B A4B(80.9%)와의 0.2%p 차이는 사실상 동등하다고 보고, 비용·속도보다
Dense 31B의 전반적인 답변 품질을 우선했다. OpenRouter 기준 단가는 입력 $0.09/M, 출력 $0.34/M 토큰으로 절대 비용도 낮다.

- 답변 생성과 검색 전 질의 재작성(`chunking_strategy.md` 4절 H4)에 같은 모델을 쓴다.
- 262,144 토큰 컨텍스트와 JSON Schema 구조화 출력을 지원해 현재 top-5 문맥과 `{answerable, answer}` 응답에 충분하다.
- 자체 GPU 대신 OpenRouter의 다중 제공자 라우팅·장애 전환을 사용한다. 요청마다 ZDR과 데이터 수집 거부를 강제한다.
- 제공자별 양자화·성능 차이가 생길 수 있다. 먼저 Gold Set 41문항을 다시 평가하고, 편차가 확인되면 검증된 제공자로 고정한다.
- temperature 0과 seed 42를 유지하고 실제 응답 모델을 평가 리포트에 기록한다. 제공사가 완전한 결정론을 보장하지는 않는다.

## 3. 주의할 점

- **데이터 보안**: OpenRouter의 ZDR은 제공자가 요청·응답을 보관하지 않게 하지만 외부 전송 자체를 막지는 않는다. 운영 전 기관 보안 정책의 허용 여부를 별도로 확인한다.
- **Judge 모델**: 답변 모델과 분리해 OpenRouter의 `openai/gpt-6-sol`을 쓴다. 처음 쓴 `openai/gpt-5.4-mini`에서 판단력을 우선해 상위 모델로 바꿨다. 교체 전후 비교는 `evaluation.md` 4절.
- **영어 벤치마크의 한계**: FACTS는 실제 한국어 정부 문서·다중 청크 조건을 대신하지 못한다. 채택 근거는 1차 선별이며 최종 품질은 프로젝트 Gold Set으로 확인한다.

## 참고

- [Korean-MTEB v2 리더보드](https://github.com/OnAnd0n/ko-embedding-leaderboard)
- [pplx-embed-v1-4b – OpenRouter](https://openrouter.ai/perplexity/pplx-embed-v1-4b), [모델 카드](https://huggingface.co/perplexity-ai/pplx-embed-v1-4b)
- [FACTS Grounding Leaderboard](https://www.kaggle.com/benchmarks/google/facts-grounding)
- [Gemma 4 31B – OpenRouter](https://openrouter.ai/google/gemma-4-31b-it), [OpenRouter Structured Outputs](https://openrouter.ai/docs/guides/features/structured-outputs)
- [OpenRouter GPT-6 Sol](https://openrouter.ai/openai/gpt-6-sol), [OpenRouter Structured Outputs](https://openrouter.ai/docs/guides/features/structured-outputs)
