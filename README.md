# document-rag-qa-system

## Corpus

### 선정: 고용보험 실업급여(구직급여)

직접 실업급여를 받으면서 겪은 문제에서 출발했다. 주변에도 실업급여를 받는 친구가 많은데, 다들 "나도 받을 수 있나?", "받는 동안 뭘 해야 끊기지 않나?"를 제대로 이해하지 못해 헤매고 있었다. 정보가 법령, 기관 안내, 블로그에 흩어져 있고 금액·기준이 매년 바뀌어서 오래된 정보도 흔하다.

고용센터에 방문했을 때는 고령자분들이 특히 많았다. 인터넷 접근이 어려워 전화로 문의하거나, 센터가 멀어도 법령이 어렵고 스스로 찾아볼 방법을 몰라서 직접 찾아오는 경우가 많았다. 이 프로젝트는 그런 분들이 **어려운 법령과 안내문을 쉬운 말로, 근거와 함께** 확인할 수 있도록 조금이라도 돕는 것을 목표로 한다.

잘못 알면 수급을 놓치거나 부정수급이 될 수 있어서, **근거(citation)를 보여주고 모르면 답하지 않는 RAG**가 실제로 가치를 갖는 도메인이다. 답변에 출처 문서와 쪽 번호를 표시하면, 사용자가 고용센터나 상담센터(1350)에 문의할 때 그 근거를 그대로 보여줄 수도 있다.

- 범위: 일반 근로자의 **구직급여**. 자영업자·예술인·노무제공자 특례는 문서에 포함되어 있지만 주요 평가 대상은 아니다.
- 이 도메인은 LLM이 사전 지식으로 그럴듯하지만 틀린 답(예전 상한액, 폐지된 절차)을 만들기 쉬워서 hallucination을 관찰하기에도 적합하다.

### 구성

| 문서 | 발행 | 기준일 | 분량 | 역할 |
|---|---|---|---|---|
| 찾기 쉬운 생활법령정보 「실업급여」 | 법제처 | 2026-08-31 | 59쪽 | 제도·법 해설: 수급자격, 수급일수·금액, 연장급여, 부정수급, 근거 조문 |
| 취업드림수첩 (구직급여 수급자 안내 e북) | 고용노동부 | 2026-02 발행 | 35장(책자 약 68쪽) | 수급 중 실무: 실업인정, 재취업활동 인정 기준, 수급 중 유의사항 Q&A |

두 문서는 성격이 다르다. 생활법령은 "받을 수 있나, 얼마나"를, 수첩은 수급자가 실제로 받은 안내서로서 "받는 동안 무엇을 해야 하나"를 다룬다. 합계 약 100쪽이며 과제의 분량 조건(50쪽 이상)을 충족한다.

### 확보 방법 (재현성)

원본 PDF를 `preprocessing/data/raw/`에 포함했다. 출처 URL과 기준일은 `preprocessing/data/sources.json`에 기록했다.

### 라이선스 및 출처

- 생활법령정보: 출처 표시 조건으로 영리 목적을 포함한 자유 이용 허용, 내용 변경 금지. 원문은 수정하지 않고 저장하며, 청킹 등 가공은 인덱싱 단계에서만 수행한다. 출처: 법제처 찾기 쉬운 생활법령정보(https://www.easylaw.go.kr)
- 취업드림수첩: 고용노동부 저작물. 출처: 고용노동부 고용24(https://www.work24.go.kr)
- 두 문서 모두 법적 효력이 있는 유권해석이 아니다. 서비스 답변도 참고 정보로만 제공한다.

### 알려진 데이터 이슈

- **기준 시점 차이**: 수첩(2026-02)과 생활법령(2026-08-31)의 기준일이 달라 내용이 충돌할 수 있다. 답변에는 출처별 기준일을 함께 표시한다.
- **수첩 레이아웃**: PDF 한 장에 책자 2쪽이 좌우로 배치되어 있어 좌우를 분리해 추출해야 한다. citation에는 책자 인쇄 쪽 번호를 사용한다.
- **서식 페이지**: 수첩 1–10장은 실업인정 기록표, 달력 등 빈 서식이라 인덱싱에서 제외한다.
- **단일 발행처 편향**: 정부 공식 안내만 포함하므로 실제 심사 사례, 판례, 예외 처리 관행은 다루지 못한다.

## 실행

모델 선정 근거는 `decision/models.md`에 있다. `.env.example`을 `.env`로 복사하고 Gemini와 OpenRouter API 키를 넣는다.

```dotenv
GEMINI_API_KEY=<키>
OPENROUTER_API_KEY=<키>
```

Python 3.13에서 확인했다.

```bash
pip install -r requirements.txt
python -m preprocessing.ingest.build           # Markdown → canonical text, 청크
python -m preprocessing.index.build            # 청크 → pplx-embed-v1-4b 벡터 (검색은 LLM 질의 재작성 → 임베딩 + BM25 하이브리드)
python -m app.tasks.qa.ask "구직급여 하루 상한액은 얼마인가요?"   # CLI
python main.py                             # API 서버 (http://127.0.0.1:8000/docs)
python -m evaluation.gold.build            # Gold Set 인용문 → 근거 좌표 (decision/gold_set.md)
python -m evaluation.retrieval             # 검색 평가 → evaluation/reports/retrieval.md
python -m evaluation.answer                # 답변·거부·인용 평가 → evaluation/reports/answer_eval.md
python -m evaluation.answer --judge-only  # 저장된 동일 답변을 OpenRouter GPT Judge로 재채점
pytest tests
```

검색 평가는 Gold 근거의 회수율을, end-to-end 평가는 41문항 전체의 답변 가능성 판정, 거부, 실제 인용 청크와 Gold 근거의
일치, 답변 정확성·완전성·충실성을 측정한다. 지표 정의와 LLM Judge의 한계는 `decision/evaluation.md`에 기록했다.

### API

`POST /ask`

```json
// 요청
{"question": "구직급여 하루 상한액은 얼마인가요?"}

// 응답
{
  "answerable": true,
  "answer": "... 하루 최대 6만8,100원을 초과할 수 없습니다.",
  "citations": [
    {"n": 1, "chunk_id": "EL-0027", "source": "[생활법령 실업급여 | 2026-08-31 기준] 2. 구직급여 > ...", "page_start": 27, "page_end": 27, "score": 0.0328}
  ],
  "model_version": "gemini-3.7-flash"
}
```

- `answerable: false`: 검색된 자료에 답이 없어 응답 불가. 이때 `citations`는 비어 있다.
- `citations`: 답변 생성에 사용한 자료 목록. 내부 인용 번호는 사용자용 `answer`에서 제거한다.

## 시스템 아키텍처

```
[1회성, 사람 검수]  preprocessing/data/raw/*.pdf ──(preprocessing/pdf_to_markdown)──▶ preprocessing/data/markdown/*.md (커밋된 원본)

[Ingest]   Markdown ──(preprocessing/ingest)─┬─▶ canonical text (preprocessing/data/processed)
                                             └─▶ 제목 기반 청크 120개 (app/data/processed/chunks.structure.jsonl)
[Index]    청크 ──(preprocessing/index, pplx-embed-v1-4b)──▶ app/data/processed/embeddings.f32 (2560차원, L2 정규화)

[질의]     질문 ──▶ ① 질의 재작성 (Gemini 3.7 Flash)
                ──▶ ② 하이브리드 검색: 임베딩 코사인 + BM25(글자 2-gram) → RRF → top-5
                ──▶ ③ 답변 생성 (Gemini 3.7 Flash, 구조화 출력 {answerable, answer})
                ──▶ ④ 서버가 본문의 [n]을 파싱해 citation 객체 생성, 사용자용 답변에서 번호 제거
                ──▶ POST /ask 응답 (main.py, FastAPI)

[평가]     Gold Set(evaluation/data, 41문항, 근거 = canonical text 문자 구간)
             ├─ evaluation/retrieval: 검색만 실행 → Hit/Recall/Coverage/Precision@k
             └─ evaluation/answer: ①~④ 전체 실행 → 거부·인용 결정론 지표 + OpenRouter GPT Judge
```

`app/`은 배포 시 필요한 API·검색·답변 생성·인덱스 로딩 코드와 런타임 데이터만 가진다. `preprocessing/`은 PDF 변환,
청킹·인덱스 생성과 관련 데이터를, `evaluation/`은 Gold Set·평가 코드·평가 리포트를 가진다. 앱은 두 오프라인 패키지를
import하지 않고, 전처리가 만든 `app/data/processed/` 안의 청크와 임베딩 세 파일만 읽는다.

- 벡터 DB 없이 120개 벡터를 전수 비교한다. 순수 Python으로 검색 한 번에 약 10ms라 별도 설치가 필요 없다.
- 앱용 청크·인덱스(`app/data/processed/`)와 평가용 Gold Set(`evaluation/data/processed/`)이 커밋되어 있어
  ingest와 index를 다시 돌리지 않아도 질의·평가를 실행할 수 있다.

## 기술 스택과 선정 근거

| 구성 | 선택 | 근거 |
|---|---|---|
| 언어·서버 | Python, FastAPI | Pydantic 스키마가 곧 Request/Response 정의와 OpenAPI 문서(`/docs`)가 된다 |
| PDF 추출 | pdfplumber (1회성 초안) | 좌표·글꼴 정보로 제목과 표를 추정. 이후는 검수된 Markdown만 읽는다 |
| 임베딩 | OpenRouter `perplexity/pplx-embed-v1-4b` | Korean-MTEB v2 Dense 검색 1위. Gold Set 검색에서 이전 Gemini Embedding 2와 동등 이상이면서 가격은 약 1/7 (`decision/models.md`) |
| 답변·재작성 LLM | Gemini API `gemini-3.7-flash` (thinking low) | FACTS Grounding 6위. Gold Set에서 Gemma 4 31B보다 근거 충실도·partial 처리가 높고, Gemini 3.8 Flash와 같은 가격에 정답성·완전성이 높음 (`decision/models.md`) |
| Judge | OpenRouter `openai/gpt-6-sol` | 답변 모델과 다른 개발사 모델로 자기 선호 편향을 줄이고, JSON Schema structured output으로 채점 형식 강제. 재채점이 41회 호출뿐이라 비용보다 판단력을 우선해 상위 모델 사용 |
| 키워드 검색 | 직접 구현한 BM25 (글자 2-gram) | 형태소 분석(kiwipiepy)보다 Recall@5가 높았고(0.691 vs 0.605) 의존성이 없다 |
| 프레임워크 | 사용 안 함 (LangChain·LlamaIndex 미사용) | 파이프라인이 재작성 → 검색 → 생성 세 단계라 직접 구현해도 짧고, 각 단계를 평가 trace로 그대로 노출할 수 있다 |

## Gold Set과 평가 지표

- 네이버 지식iN 실제 질문 41문항(full 18, partial 18, none 5). 유형은 factoid 15, multi_hop 13, procedural 7, summary 1, unanswerable 5.
  구축 방식, 판정 기준, **편향과 한계**는 `decision/gold_set.md`.
- 근거는 청크 ID가 아닌 canonical text의 문자 구간으로 표시해, 청킹 방식을 바꿔도 같은 Gold Set으로 비교한다.
- 지표 정의(검색 지표, 거부·인용 결정론 지표, Judge 1–5점 지표)와 각 지표의 한계는 `decision/evaluation.md`와
  `decision/chunking_strategy.md` 4절.
- LLM Judge 프롬프트를 신뢰성·일관성·Human Alignment 측면에서 어떻게 설계했는지와 그 약점은 `decision/evaluation.md` 3절
  "Judge 프롬프트 설계 배경".
- 평가 실행 단계와 변경 비교 절차(무엇을 고정하고 어떻게 판정하는지)는 `decision/eval_harness.md`.
- 재현성: 리포트 JSON에 커밋과 dirty 여부, 모델 ID와 응답 모델 버전, seed(42), temperature, Judge 프롬프트 해시,
  인덱스 해시를 기록한다.

## 핵심 설계 결정과 Trade-off

| 결정 | 얻은 것 | 대가 |
|---|---|---|
| PDF → 사람이 검수한 Markdown을 원본으로 | 파싱 오류가 평가에 섞이지 않고, 청킹 규칙이 단순해진다 | PDF가 개정되면 변환·검수를 다시 해야 한다. 검수자가 놓친 오류는 남는다 |
| 문서 구조(절·Q&A) 기반 청킹 + 제목 경로 접두어 | 고정 길이 대비 Recall@5 0.595 → 0.643 | factoid는 크게 올랐지만 multi_hop은 거의 그대로 |
| 임베딩 + BM25 하이브리드 (RRF) | Recall@5 0.643 → 0.691, 일반적인 청크가 top-k를 차지하는 현상 감소 | Hit@5 1문항 하락 |
| LLM 질의 재작성 | Recall@5 0.691 → 0.788 (seed 도입 후 3회 0.769~0.783). 구어와 문서 용어의 차이를 메운다 | 질문마다 LLM 호출 1회 추가(응답 지연 증가), 두 가지를 묻는 질문을 한쪽으로 좁히기도 함 |
| 인용 번호를 답변 본문에서 파싱 (LLM이 별도 목록을 만들지 않음) | 본문과 citation 목록이 어긋날 수 없다 | 사용자용 답변에서는 번호를 지우므로, 어느 문장이 어느 출처인지는 응답에 남지 않는다 |
| 거부를 구조화 출력 `answerable`로 판정 | 거부 여부를 결정론적으로 채점할 수 있다 | 판정이 LLM 한 번에 달려 있어 인접 주제 질문(KIN-13)에 답해 버리는 경우가 있다 |
| Judge를 답변과 다른 개발사 모델로 | 자기 선호 편향 감소 | Judge 호출 비용이 추가되고, temperature는 요청 호환성 문제로 지정하지 않는다(API 기본값) |

실험 과정과 조건별 결과는 `decision/chunking_strategy.md` 4절에 있다.

## Part C 개선 실험 보고서

### Hypothesis

한 번에 한 변수만 바꾸고, 앞 단계의 출력을 고정해 다음 다섯 가설을 검증했다. 검색 실험은 근거가 있는 Gold Set 36문항,
답변 실험은 전체 41문항을 사용했다.

1. **하이브리드 검색**: dense 검색에 글자 2-gram BM25를 RRF로 결합하면 정확한 제도 용어를 보완해 Recall@5가 오른다.
2. **답변 재생성 평가 플로우**: 저장된 top-5 검색 결과를 고정하고 답변만 다시 생성하면, 검색 변동을 섞지 않고 프롬프트와
   답변 LLM의 효과를 비교할 수 있다. 이는 사용자용 "다시 생성" 기능이 아니라 Eval Harness의 비교 절차다.
3. **임베딩 모델 변경**: 한국어 검색 벤치마크가 높은 `pplx-embed-v1-4b`로 바꾸면 검색 품질을 유지하거나 높이면서 비용을
   줄일 수 있다.
4. **가독성 프롬프트**: 법조문을 그대로 나열하지 않고 사실 추출과 쉬운 표현을 분리하면, 정확성을 크게 해치지 않으면서
   답변 길이·문장 길이·원문 복사율을 낮추고 Clarity를 높일 수 있다.
5. **LLM 변경**: Gemini 3.7 Flash는 같은 검색 결과에서 Gemini 3.8 Flash 이상으로 정확하고, 문서에 없는 부분을 더 분명히
   밝혀 Correctness·Completeness·Partial handling이 오른다.

### Result

| 변경 | 고정한 조건 | Before → After | 문항 단위 결과 | 결정 |
|---|---|---|---|---|
| Dense → 하이브리드 검색 | 청크·제목·임베딩 | Recall@5 **0.643 → 0.691**, multi-hop 0.519 → 0.612 | 개선 6 / 악화 3 | 채택 |
| 답변 재생성 플로우 추가 | 저장된 top-5·동일 Judge | 프롬프트·LLM만 바꾼 답변을 독립 비교 가능 | 문항별 답변·Judge 근거 저장 | 채택 |
| Gemini Embedding 2 → pplx | 저장된 동일 재작성 질의 | Recall@5 **0.769 → 0.811**, Hit@5 0.972 → 1.000 | 개선 5 / 악화 2 | 품질 동등 이상·가격 약 1/7로 채택 |
| 기존 프롬프트 → H6 | 모델·검색 결과·Judge | 답변 길이 **380 → 224자**, 문장 길이 **81 → 67자**, 원문 복사율 **0.205 → 0.029**, Clarity **3.317 → 3.634** | H5는 효과 없어 롤백, H6 채택 | H6b로 정보 부족 안내 보완 |
| Gemini 3.8 → Gemini 3.7 | 저장된 top-5·동일 Judge | Correctness **4.000 → 4.306**, Completeness **3.222 → 3.500**, Partial handling **4.000 → 4.167** | Correctness 개선 13 / 악화 3, Completeness 개선 10 / 악화 2 | 같은 가격에서 3.8 이상으로 판단해 채택 |

답변 재생성 플로우는 그 자체로 사용자 품질 점수를 높이는 기능이 아니라, 나머지 실험의 인과관계를 더 명확하게 만드는
평가 기반이다. 답변 프롬프트나 LLM을 비교할 때 이전 리포트의 top-5를 그대로 넣고 답변만 새로 생성했으며, Judge를 바꾸면
기준선 답변도 같은 Judge로 다시 채점했다.

### Analysis

- **하이브리드 검색**은 여러 근거가 필요한 질문에서 효과가 컸고, 근거 없이 자주 검색되던 짧은 절 도입 청크 BK-0040의
  top-5 진입을 13문항에서 1문항으로 줄였다. 다만 Hit@5는 한 문항 하락해 모든 지표가 함께 좋아진 것은 아니다.
- **임베딩 변경**은 Recall@5와 Hit@5가 올랐지만 Recall@1은 0.490에서 0.443으로 낮아졌다. 36문항의 작은 차이이므로
  `pplx`가 확실히 우수하다고 단정하지 않고, 품질 동등 이상에 약 1/7의 가격이라는 운영상 이점을 합쳐 채택했다.
- **가독성 개선**에서는 첫 시도 H5(결론 먼저·상황 적용·용어 풀이)가 Clarity 3.317 → 3.293으로 나빠져 롤백했다. H6는
  사실 추출과 표현을 분리해 Clarity와 결정론적 가독성 지표를 개선했지만 Completeness 2.659 → 2.488, Partial handling
  3.333 → 2.778로 정보 누락이 늘었다. 그래서 H6b에서 모르는 부분을 모두 밝히고 최종 판단 주체를 안내하도록 보완했다.
  즉 짧게 만드는 것만을 성공으로 보지 않고 정확성·완전성·충실성과 함께 판단했다.
- **LLM 변경**은 처음 선택한 저가 Gemma 4 31B가 Gemini 3.8보다 Faithfulness(4.028 → 3.694)와 Partial handling
  (4.000 → 3.056)이 낮아 되돌린 뒤 Gemini 3.7을 비교한 결과다. Gemini 3.7은 3.8보다 Correctness와 Completeness가
  높았지만 Faithfulness의 문항별 개선 11 / 악화 9는 비슷했다. 조건별 실행이 한 번뿐이고 작은 차이는 Judge 변동 범위에
  가까워, "명확한 우위"가 아니라 **같은 가격에서 3.8 이상**으로 해석했다.

모든 비교는 평균뿐 아니라 개선·악화 문항과 실패 사례를 함께 확인했다. LLM과 Judge는 seed 42에서도 완전히 결정적이지 않고,
검색 36문항·거부 5문항의 작은 표본이므로 작은 차이는 경향으로만 해석한다. 현재 전체 운영 조합의 수치는
`evaluation/reports/retrieval.md`와 `evaluation/reports/answer_eval.md`, 상세 실험 조건은 `decision/chunking_strategy.md`, `decision/models.md`,
`decision/eval_harness.md`에 기록했다.

### Next Steps

- 고정 top-5 답변 재생성과 고정 재작성 질의 검색을 임시 절차가 아닌 CLI 옵션으로 만들어 비교 실험을 한 명령으로 재현한다.
- 각 조건을 반복 실행해 분산과 신뢰구간을 기록하고, 더 큰 Gold Set과 사람 채점 표본으로 작은 차이를 재검증한다.
- 하이브리드 검색의 RRF·BM25 설정을 별도 validation set에서 조정하고, Recall@1 하락 원인을 문항별로 분석한다.
- 답변 프롬프트와 Judge가 "최종 판단은 고용센터가 한다"는 안내를 서로 다르게 평가하는 충돌을 해소한다.
- Gemini 3.7의 지원 종료 전에 후속 모델을 같은 고정 입력·동일 Judge 조건으로 비교한다.

## 비용·컴퓨팅 제약

- GPU 없이 누구나 재현할 수 있도록 로컬 모델 대신 API 모델을 썼다. 인덱싱 비용은 청크 120개에 0.05달러 미만이다.
- Gold Set 전체 평가 한 번에 질문당 Gemini 2회(재작성·답변), Perplexity 임베딩 1회, OpenRouter Judge 1회를 호출한다.
  Gemini 3.7 Flash는 입력 $0.75/M, 출력 $3.75/M 토큰으로 질문당 약 1센트 미만이다. Gemma 4 31B는 약 1/10 가격이었지만 근거 충실도가 낮아 바꿨다.
- OpenRouter 요청(임베딩·Judge)은 ZDR과 데이터 수집 거부를 강제하지만, Gemini API 직접 호출(재작성·답변)에는 ZDR이 적용되지 않는다.
  실제 사용자 질문을 받기 전 유료 등급의 데이터 처리 조건과 기관 보안 정책을 확인해야 한다.
- 청크가 120개라 벡터 DB를 두지 않았다. 문서가 수만 청크로 늘면 벡터 DB로 바꾼다.
- 질의 재작성 대신 청크마다 예상 질문을 미리 생성해 색인하는 방식(doc2query)은 질의 시 호출이 없지만, 측정 비용 때문에 비교하지 않았다.

## 한계

- **Corpus 범위**: 정부 공식 안내 2종만 담아 실제 심사 사례, 판례, 예외 처리 관행은 답할 수 없다. 두 문서의 기준일이 다르다.
- **평가 규모**: 41문항, 거부 문항 5개라 한 문항이 거부 지표를 20%p 움직인다. 작은 차이는 경향으로만 읽는다.
- **Judge 검증**: Judge 점수를 사람 채점과 대조하지 않았다. 신뢰성·일관성은 설계로 다뤘지만 사람과의 정합성은 측정되지 않았다.
- **비결정성**: temperature 0과 seed 42를 지정하지만 Gemini·OpenRouter는 완전한 결정론을 보장하지 않는다. 리포트에 문항별 재작성 질의와 실제 응답 모델을 남겨 추적한다.
- **단일 턴**: 이전 대화를 참고하지 않는다.

## 알려진 이슈

- **KIN-13 오답변**: 답이 없는 질문(같은 회사 지원+면접 횟수)에 인접 규정("동일 사업장 반복 지원 불인정")을 근거로 답한다.
- **KIN-09 검색 실패**: 수급 신청 전 알바 소득 신고 질문은 검색 단계에서 근거를 거의 찾지 못한다.
- **검색 평가와 답변 평가의 재작성 질의가 일부 다를 수 있다**: 두 평가가 재작성을 따로 호출해, 같은 커밋에서도 1~2문항은 두 리포트의 top-5가 다를 수 있다.
- **LLM 구조화 출력 실패 시 500**: Gemini가 스키마에 맞는 응답을 주지 않으면 `/ask`가 오류를 반환한다. 재시도나 명시적인 오류 응답이 없다.
- **Streaming 미지원**.

## 향후 개선 과제

- 유형별 표본을 사람이 채점해 Judge와의 일치도 측정
- 임베딩 모델 비교(Qwen3-Embedding-8B)를 검색 지표로 확인 (`decision/models.md` 1절)
- 인접 주제 거부 강화: 답변 전에 "자료가 질문의 핵심에 직접 답하는가"를 따로 판정
- doc2query와 질의 재작성의 지연·Recall 비교
- Streaming 응답, 구조화 출력 실패 시 재시도
- 멀티턴 대화: 이전 대화를 반영한 질의 재작성
- CI 연동: 결정론 지표(거부, citation integrity)는 임계값 게이트로, Judge 점수는 추세로 관리 (`decision/eval_harness.md` 6절)
