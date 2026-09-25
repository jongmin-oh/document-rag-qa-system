"""청크 텍스트에서 인용 법령·조문을 추출한다."""

import re


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


REF_SEGMENT = re.compile(r"(?:\s*(?:제\d+조(?:의\d+)?|제\d+항|제\d+호|본문|단서|전단|후단|및|,|·))+")
REF_TOKEN = re.compile(r"제\d+조(?:의\d+)?(?:제\d+항)?(?:제\d+호)?|제\d+항(?:제\d+호)?|제\d+호")


def cited_laws(text: str) -> list[str]:
    """「법령」 뒤에 이어지는 조·항·호를 모두 펼친다.

    「고용보험법」 제45조제5항, 제46조제1항제1호 → 고용보험법 제45조제5항, 고용보험법 제46조제1항제1호
    「근로기준법」 제2조제1항제5호·제6호       → 근로기준법 제2조제1항제5호, 근로기준법 제2조제1항제6호
    조문 없이 인용되는 고시는 고시 이름만 남긴다.
    """
    t = normalize(text)
    t = re.sub(r"제\s+(\d)", r"제\1", t)  # 줄바꿈으로 갈라진 "제\n42조" 복원
    t = re.sub(r"(\d)\s+(조|항|호)", r"\1\2", t)
    refs: list[str] = []
    for m in re.finditer(r"「([^」]+)」", t):
        seg = REF_SEGMENT.match(t, m.end())
        if not seg:
            if m.group(1).endswith("고시") and m.group(1) not in refs:  # 조문 없이 인용되는 고시
                refs.append(m.group(1))
            continue
        art = para = ""
        for tok in REF_TOKEN.findall(seg.group(0)):
            a = re.match(r"제\d+조(?:의\d+)?", tok)
            p = re.search(r"제\d+항", tok)
            if a:
                art, para = a.group(0), p.group(0) if p else ""
                ref = tok
            elif p:
                para = p.group(0)
                ref = art + tok
            else:
                ref = art + para + tok
            if art:
                full = f"{m.group(1)} {ref}"
                if full not in refs:
                    refs.append(full)
    return refs
