# End-to-end 평가 체계

> 검색 품질과 최종 답변 품질을 분리해 진단한다. 검색 평가는 `retrieval.py`, 답변·거부·인용 평가는
> `answer.py`가 담당하며 두 평가 모두 같은 Gold Set과 운영 검색·답변 코드를 사용한다.

## 1. 평가 단위

`python -m app.tasks.eval.answer`는 Gold Set 41문항 전체에 실제 운영 경로인 질의 재작성 → 하이브리드 검색 →
답변 생성을 적용한다. API에는 노출하지 않는 trace에 재작성 질의, top-5 청크, 실제 인용 청크와 모델 버전을 남긴다.

## 2. 결정론적 지표

| 지표 | 정의 | 한계 |
|---|---|---|
| Answerability accuracy | `full`·`partial`은 답변, `none`은 거부했는지 | partial 답변의 내용 품질은 알 수 없음 |
| Refusal recall / False answer rate | `none`을 거부한 비율 / 잘못 답한 비율 | none이 5개라 원시 개수도 함께 봐야 함 |
| Citation integrity | 본문 `[n]`·`[n, m]`이 유효한 top-5 번호인지 | 인용이 주장을 지지하는지는 판단하지 않음 |
| Citation presence | 답변에는 인용이 있고 거부에는 인용이 없는지 | 인용의 품질은 판단하지 않음 |
| Gold evidence recall·precision·coverage | 실제 인용 청크와 Gold 근거 문자 구간의 겹침 | Gold에 등록하지 않은 정당한 대체 근거를 낮게 평가할 수 있음 |

## 3. 의미 지표

LLM Judge가 질문, Gold answerability, 참고 정답, Gold 근거, 생성 답변, 실제 인용 자료만 보고 0–4점으로 채점한다.

- Correctness: 참고 정답과 의미상 일치하는가
- Completeness: 문서로 답할 수 있는 핵심 항목을 빠짐없이 다뤘는가
- Faithfulness: 검증 가능한 주장이 실제 인용 자료로 뒷받침되는가
- Partial handling: `partial` 문항에서 자료 밖 부분을 밝히고 추측하지 않았는가

Judge 입력에 검색됐지만 인용하지 않은 청크는 넣지 않는다. 그래야 인용하지 않은 자료로 답변을 사후 정당화하지 않는다.

API의 citation 객체는 LLM이 별도 목록으로 중복 생성하지 않는다. 서버가 최종 답변 본문의 `[n]`·`[n, m]`을 파싱해
top-5 검색 결과와 연결한다. 따라서 본문이 인용 번호의 단일 기준이며, integrity는 잘못된 범위의 번호나 malformed 표기를
검출하는 방어 지표다. 파싱 후 사용자용 `answer`에서는 번호를 제거하고 출처 객체만 반환한다. 평가 trace에는 번호가 붙은
`annotated_answer`를 남겨 주장과 근거의 연결을 검증한다.

최초 평가 커밋 `4a6b284`는 단일 표기 `[n]`만 읽는 평가기 정규식 때문에 Citation integrity를 0.561로 잘못 기록했다.
원시 응답에는 `[1, 3]` 같은 묶음 표기가 있었으며 이를 올바르게 파싱하면 최초 실행도 41/41(1.000)이었다. 따라서 이후
리포트와 최초 리포트의 integrity 차이는 모델 품질 개선으로 해석하지 않는다. 이 수정에서 묶음 표기를 지원하는 공용 파서를
추가하고, LLM이 본문과 citation 배열을 중복 생성하던 잠재 오류원도 함께 제거했다.

## 4. 근거와 한계

- RAGAS는 검색 문맥, 답변 충실성, 답변 관련성을 분리해 평가한다: https://aclanthology.org/2024.eacl-demo.16/
- ARES는 context relevance, answer faithfulness, answer relevance를 별도 축으로 둔다: https://aclanthology.org/2024.naacl-long.20/
- ALCE는 citation correctness와 completeness를 평가한다: https://aclanthology.org/2023.emnlp-main.398/
- RGB는 근거가 없을 때 답하지 않는 negative rejection과 여러 근거를 합치는 information integration을 평가한다:
  https://arxiv.org/abs/2309.01431

답변 생성은 Gemini 3.8 Flash, Judge는 OpenRouter의 `openai/gpt-5.4-mini`를 쓴다. 다른 제공자·모델 계열로 분리해
동일 모델의 자기 선호 위험을 낮추고, JSON Schema structured output으로 rubric 결과를 강제한다. GPT-5.4 Mini를 고른
이유는 한국어 문장의 다단계 판단에 충분한 추론 성능과 평가 반복 비용의 균형이다. OpenRouter 모델 정보 확인일은
2026-09-25이며 가격은 입력 $0.75/M, 출력 $4.50/M 토큰이다.

모델을 분리해도 자동 Judge가 사람 평가를 대체하지는 않는다. 최종 분석에서는 유형별 표본을 사람이 같은 기준으로 채점해
Judge와의 불일치를 기록해야 한다. 문항 수가 41개이고 none은 5개뿐이므로 작은 차이를 일반화하지 않으며 하나의 종합
점수로 합치지 않는다.

## 5. 재현성

JSON 리포트에 코드 커밋과 dirty 상태, 설정 모델과 실제 응답 모델 버전, Judge 프롬프트 해시, 임베딩 모델·차원과 인덱스
해시, temperature와 seed 지원 여부를 기록한다. Gemini·OpenRouter API 호출 결과는 제공사 변경으로 완전히 결정론적이지
않을 수 있다.
