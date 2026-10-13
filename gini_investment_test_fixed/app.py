"""기니와 함께하는 투자 성향 탐색기 | 실행: streamlit run app.py

교육·자기 탐색용 간이 설문입니다. 금융투자상품 적합성 판단이나 개인별 투자자문이 아닙니다.
"""
from __future__ import annotations

import base64
from collections import defaultdict
from html import escape
from pathlib import Path

import streamlit as st

BASE = Path(__file__).resolve().parent
ASSETS = BASE / "assets"
DIMENSIONS = {
    "loss": ("손실 감내", "가격이 떨어졌을 때 얼마나 감당할 수 있는지"),
    "capacity": ("재무적 여력", "투자금 손실이 생활에 미치는 영향"),
    "horizon": ("투자 기간", "투자 자금을 사용하기까지 남은 시간"),
    "liquidity": ("유동성 필요", "돈을 빠르게 꺼내 써야 할 가능성"),
}

# 0~3점: 각 문항의 높은 점수는 '큰 위험을 받아들일 수 있는 상황'을 의미.
# 단, 유동성은 원 점수 자체가 아닌 '자금 묶어둘 수 있는 정도'로 역방향 코딩합니다.
QUESTIONS = [
    {"id":"loss1", "axis":"loss", "text":"투자한 100만 원이 한 달 만에 90만 원이 된다면?", "options":[
        "불안해서 가능한 한 빨리 투자금을 회수하고 싶어요.",
        "일단 기다리겠지만 손실이 더 커지면 정리할 것 같아요.",
        "투자 이유가 유효하다면 시간을 두고 지켜보겠어요.",
        "손실을 감당할 여유가 있다면 추가 투자도 검토하겠어요."], "scores":[0,1,2,3]},
    {"id":"capacity1", "axis":"capacity", "text":"투자할 돈을 일부 잃어도 생활비나 중요한 지출에 영향이 있나요?", "options":[
        "네. 생활비나 꼭 필요한 지출이 어려워질 수 있어요.",
        "생활에 부담이 생기고 계획을 크게 바꿔야 해요.",
        "생활비는 따로 있지만 저축 계획에는 영향이 있어요.",
        "생활비·비상자금과 분리된 여유자금이라 영향이 작아요."], "scores":[0,1,2,3]},
    {"id":"horizon1", "axis":"horizon", "text":"투자하려는 자금은 언제 사용할 예정인가요?", "options":[
        "1년 이내에 사용할 예정이에요.", "1~3년 사이에 필요할 수 있어요.",
        "3~5년 정도는 투자할 수 있어요.", "5년 이상 사용할 계획이 없어요."], "scores":[0,1,2,3]},
    {"id":"liquidity1", "axis":"liquidity", "text":"예상하지 못한 지출이 생겼을 때 투자금을 찾아야 할 가능성은?", "options":[
        "매우 높아요. 투자금 외에 쓸 돈이 거의 없어요.",
        "조금 높아요. 필요하면 투자금을 꺼내야 해요.",
        "낮은 편이에요. 다른 예비자금이 어느 정도 있어요.",
        "매우 낮아요. 별도의 비상자금을 충분히 마련했어요."], "scores":[0,1,2,3]},
    {"id":"loss2", "axis":"loss", "text":"가장 마음 편한 투자 결과는 어느 쪽인가요?", "options":[
        "수익이 적더라도 가격 변동이 매우 작은 결과",
        "낮은 변동성과 소폭의 수익을 기대하는 결과",
        "중간 정도 변동성을 감수하고 장기 수익을 기대하는 결과",
        "큰 변동성을 감수하고 높은 장기 수익 가능성을 추구하는 결과"], "scores":[0,1,2,3]},
    {"id":"capacity2", "axis":"capacity", "text":"앞으로 6개월간 소득이 줄면 투자금을 어떻게 해야 할까요?", "options":[
        "생활을 위해 대부분 인출해야 할 것 같아요.",
        "상당 부분 인출해야 할 수도 있어요.",
        "일부 조정은 필요하지만 대부분 유지할 수 있어요.",
        "다른 예비자금으로 대응해 투자금은 유지할 수 있어요."], "scores":[0,1,2,3]},
    {"id":"horizon2", "axis":"horizon", "text":"투자 성과가 기대보다 늦게 나타난다면 얼마나 기다릴 수 있나요?", "options":[
        "1년 이내에는 결과가 나야 해요.",
        "1~3년 정도는 기다릴 수 있어요.",
        "3~5년 정도는 기다릴 수 있어요.",
        "5년 넘게 장기적으로 지켜볼 수 있어요."], "scores":[0,1,2,3]},
    {"id":"liquidity2", "axis":"liquidity", "text":"투자상품을 고를 때 현금화의 편리함은 얼마나 중요한가요?", "options":[
        "언제든 바로 꺼낼 수 있어야 해요.",
        "가급적 며칠 안에 현금화할 수 있어야 해요.",
        "일정한 환매·매도 시간을 기다릴 수 있어요.",
        "오래 투자할 수 있어 즉시 현금화할 필요가 적어요."], "scores":[0,1,2,3]},
    {"id":"loss3", "axis":"loss", "text":"투자 시장이 크게 하락했을 때 더 가까운 생각은?", "options":[
        "이런 변동성을 겪고 싶지 않으니 안전한 곳으로 옮기고 싶어요.",
        "더 떨어질까 걱정되어 위험자산을 줄이고 싶어요.",
        "분산 투자하고 투자 목표를 점검하며 버텨볼 수 있어요.",
        "변동성을 감수할 수 있고 장기 관점에서 대응하겠어요."], "scores":[0,1,2,3]},
    {"id":"loss4", "axis":"loss", "text":"투자상품 설명서에서 가장 마음에 걸리는 문구는?", "options":[
        "원금이 보장되지 않습니다.",
        "가격이 오르내릴 수 있습니다.",
        "손실을 볼 수 있지만 장기간 보유할 계획입니다.",
        "시장 상황에 따라 큰 손실을 볼 수 있습니다."], "scores":[0,1,2,3]},
]

PRODUCTS = {
    "deposit": ("예금·적금", "예금자보호 대상 여부와 한도를 확인하고, 단기 필요자금을 관리하는 데 활용할 수 있어요.", "금리·중도해지 조건·예금자보호 적용 여부를 확인하세요."),
    "shortbond": ("단기 국채·단기채권형 상품", "비교적 짧은 투자 기간을 고려할 때 살펴볼 만한 채권 관련 선택지예요.", "채권·채권 ETF도 금리 변동, 신용위험 및 매매가격에 따라 손실이 발생할 수 있어요."),
    "govbond": ("국공채·우량채권 / 채권 ETF", "손실 감내 범위와 투자 기간을 고려해 채권 중심의 자산을 공부해볼 수 있어요.", "회사채에는 신용위험이 있고, 금리 상승 시 채권 가격이 하락할 수 있어요."),
    "balanced": ("주식·채권 분산형 ETF", "서로 다른 자산을 함께 보유해 위험과 수익의 균형을 살펴볼 수 있어요.", "분산해도 원금 손실은 가능하며, ETF의 실제 구성·보수·추적오차를 확인하세요."),
    "equity": ("광범위한 주식시장 지수 ETF", "장기 투자와 가격 변동을 감내할 수 있을 때 탐색할 수 있는 선택지예요.", "주식시장 전체가 하락하면 큰 손실을 볼 수 있으며 장기 보유가 수익을 보장하지 않아요."),
    "reit": ("상장 리츠(REITs)", "부동산을 직접 소유하지 않고 관련 자산에 간접적으로 투자하는 방법을 비교할 수 있어요.", "리츠는 부동산·금리·공실·차입 부담 등에 민감하며 예금처럼 안전하지 않아요."),
}

st.set_page_config(page_title="기니의 투자 성향 탐색기", page_icon=str(ASSETS / "포인트.png"), layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
:root { color-scheme: light; }
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] { background: #fff !important; }
[data-testid="stMainBlockContainer"] { max-width: 1110px; padding-top: 1.5rem; padding-bottom: 3rem; }
[data-testid="stSidebar"], #MainMenu, footer { display: none; }
html, body, [class*="st-"] { font-family: 'Pretendard', 'Noto Sans KR', sans-serif; }
h1, h2, h3 { color: #172138; letter-spacing: -.035em; }
div[data-testid="stButton"] button { border-radius: 13px; min-height: 48px; font-weight: 650; border-color: #dce4f1; transition: .15s ease; }
div[data-testid="stButton"] button:hover { border-color: #2c6df2; transform: translateY(-1px); }
div[data-testid="stButton"] button[kind="primary"] { background:#2869e9; color:white; border-color:#2869e9; }
.gini-muted { color: #65728a; font-size: 1rem; line-height: 1.75; }
.gini-tag { display:inline-block; padding:7px 12px; border-radius:18px; background:#eaf2ff; color:#2368da; font-weight:700; font-size: .9rem; }
.gini-hero-title { font-size: clamp(1.9rem, 3.4vw, 3rem); font-weight:850; color:#172138; line-height:1.35; letter-spacing:-.055em; }
.gini-hero-title span { color: #2b6beb; }
.gini-panel { border:1px solid #e5eaf3; border-radius:22px; padding:22px 24px; background:#fff; margin:12px 0; }
.gini-softblue { background:#f0f7ff; } .gini-softcream { background:#fff8eb; } .gini-softmint { background:#edf9f1; }
.gini-item { border-radius:14px; background:white; border:1px solid #e9eaf0; padding:13px 15px; margin:10px 0; }
.gini-minor { font-size: .83rem; color:#7b869a; }
.gini-big { font-size:2rem; color:#2468e7; font-weight:850; }
.gini-step-title { font-weight:750; font-size:1.3rem; color:#172138; }
.gini-track { position:relative; height:146px; margin-top:12px; padding:0 4%; margin-bottom:15px; overflow:visible; }
.gini-line { position:absolute; top:81px; left:5%; right:5%; height:7px; border-radius:20px; background:#e5e9f1; }
.gini-linefill { position:absolute; top:81px; left:5%; height:7px; border-radius:20px; background:#8bb5ff; transition:width .2s ease; }
.gini-node { position:absolute; top:72px; transform:translateX(-50%); width:23px; height:23px; border-radius:50%; background:#d5d9e2; border:3px solid white; box-shadow:0 0 0 1px #dbe1eb; }
.gini-node.done { background:#75a6ff; } .gini-node.active { background:#276be8; }
.gini-marker { position:absolute; top:20px; width:46px; height:52px; object-fit:contain; transform:translateX(-50%); }
.gini-nodelabel { position:absolute; top:105px; transform:translateX(-50%); font-size: .72rem; color:#778298; white-space:nowrap; }
.gini-nodelabel.active { color:#1d54ac; font-weight:800; }
@media(max-width:700px){.gini-track{height:136px}.gini-nodelabel{font-size:.56rem}.gini-panel{padding:16px}.gini-marker{width:38px;height:45px;top:26px}}
</style>""", unsafe_allow_html=True)


def image_data(name: str) -> str:
    return base64.b64encode((ASSETS / name).read_bytes()).decode("ascii")


def mascot(name: str, width: int = 350) -> None:
    st.image(str(ASSETS / name), width=width)


def track(step: int) -> None:
    """0: 시작, 1..N: 문항, N+1: 결승. 질문 하나당 정확히 한 칸."""
    total = len(QUESTIONS) + 1
    parts = [f'<div class="gini-track"><div class="gini-line"></div><div class="gini-linefill" style="width:{90 * step / total:.4f}%"></div>']
    for i in range(total + 1):
        pos = 5 + 90 * i / total
        state = 'active' if i == step else ('done' if i < step else '')
        parts.append(f'<div class="gini-node {state}" style="left:{pos:.4f}%" title="{i}단계"></div>')
        # 모든 칸의 텍스트가 겹치지 않도록 시작/현재 문항/결승만 표시
        if i in (0, total) or (i == step and 0 < step < total):
            label = '시작' if i == 0 else ('결승점' if i == total else f'{i}/{len(QUESTIONS)} 문항')
            parts.append(f'<div class="gini-nodelabel {state}" style="left:{pos:.4f}%">{label}</div>')
    position = 5 + 90 * step / total
    parts.append(f'<img alt="현재 위치의 기니" class="gini-marker" style="left:{position:.4f}%" src="data:image/png;base64,{image_data("포인트.png")}"></div>')
    st.markdown(''.join(parts), unsafe_allow_html=True)


def reset() -> None:
    st.session_state.screen = 'cover'
    st.session_state.index = 0
    st.session_state.answers = {}
    st.session_state.show_details = False


def initialize() -> None:
    if 'screen' not in st.session_state: reset()


def get_stats(answers: dict) -> dict:
    scores = defaultdict(list)
    for q in QUESTIONS:
        if q['id'] in answers:
            chosen = answers[q['id']]
            scores[q['axis']].append(q['scores'][chosen])
    return {axis: {'count':len(scores[axis]), 'total':sum(q['axis']==axis for q in QUESTIONS),
                   'percent':round(100 * sum(scores[axis]) / (3*len(scores[axis]))) if scores[axis] else None,
                   'mean':sum(scores[axis])/len(scores[axis]) if scores[axis] else None}
            for axis in DIMENSIONS}


def evaluate(answers: dict) -> dict:
    s = get_stats(answers)
    loss, capacity = s['loss']['mean'], s['capacity']['mean']
    horizon, liquidity = s['horizon']['mean'], s['liquidity']['mean']
    # 손실감내와 재무적 여력 모두 필요: 어느 한쪽이 낮으면 공격형 분류를 제한.
    effective_risk = min(loss, capacity)
    short_or_urgent = horizon < 1.0 or liquidity < 1.0
    if short_or_urgent or effective_risk < 0.9:
        category = '안정 우선형'
        products = ['deposit', 'shortbond'] if not short_or_urgent else ['deposit']
    elif effective_risk < 1.8:
        category = '신중 균형형'
        products = ['deposit', 'govbond', 'balanced'] if horizon >= 1.5 and liquidity >= 1.3 else ['deposit','shortbond','govbond']
    elif effective_risk < 2.6 or horizon < 2.0 or liquidity < 1.5:
        category = '균형 성장형'
        products = ['govbond', 'balanced', 'equity'] if horizon >= 2.0 else ['shortbond','govbond','balanced']
    else:
        category = '적극 장기형'
        products = ['balanced','equity','reit']
    reasons = [
        f"손실 감내 문항의 평균은 {loss:.2f}/3점, 재무적 여력은 {capacity:.2f}/3점으로 나타났어요.",
        f"투자 기간과 유동성 대응 여력은 각각 {horizon:.2f}/3점, {liquidity:.2f}/3점이에요.",
        '짧은 투자 기간이나 당장 현금이 필요한 상황에서는 가격 변동 위험이 있는 상품을 우선 추천하지 않았어요.' if short_or_urgent else
        '손실을 감당할 의향뿐 아니라 실제 자금 여력을 함께 고려해 추천 범위를 정했어요.',
    ]
    return {'category':category, 'products':products, 'reasons':reasons, 'stats':s}


def show_stats(answers: dict, heading: str = '응답 경향 요약') -> None:
    stats = get_stats(answers)
    st.markdown(f'#### {heading}')
    for axis, (label, desc) in DIMENSIONS.items():
        item = stats[axis]
        if item['percent'] is None:
            st.caption(f'{label} · 답변 전 (0/{item["total"]}문항)')
            st.progress(0)
        else:
            st.caption(f'{label} · {item["percent"]}점/100점 · {item["count"]}/{item["total"]}문항')
            st.progress(item['percent']/100)
    st.caption('점수는 문항 선택을 0~100으로 환산한 응답 지표이며, 실제 수익률·확률·검사 정확도가 아닙니다. 유동성 항목은 높은 점수일수록 즉시 인출 필요가 낮다는 뜻이에요.')


def show_cover() -> None:
    track(0)
    left, right = st.columns([1.35,1], gap='large', vertical_alignment='center')
    with left:
        st.markdown('<span class="gini-tag">기니의 투자 성향 탐색기</span>',unsafe_allow_html=True)
        st.markdown('<div class="gini-hero-title"><span>기니와 함께</span><br>어떤 투자 상품이<br>잘 맞는지 알아봐요</div>',unsafe_allow_html=True)
        st.markdown('<p class="gini-muted">10가지 질문으로 나의 손실 감내 수준, 자금 여력, 투자 기간과 유동성 필요도를 살펴봐요.<br>기니가 투자상품의 특징과 유의점을 함께 알려줄게요!</p>',unsafe_allow_html=True)
        if st.button('테스트 시작하기 →',type='primary',use_container_width=True):
            st.session_state.screen='quiz'; st.rerun()
    with right:
        mascot('부자기니.png', width=390)
    st.markdown('')
    c1,c2,c3=st.columns(3)
    with c1: st.markdown('<div class="gini-panel gini-softblue"><b>나의 투자 성향 분석</b><p class="gini-muted">안정성·자금 여력·기간·유동성의 네 가지 관점</p></div>',unsafe_allow_html=True)
    with c2: st.markdown('<div class="gini-panel gini-softcream"><b>투자 상품 유형 제안</b><p class="gini-muted">예·적금, 채권, ETF, 리츠 등을 상황에 따라 비교</p></div>',unsafe_allow_html=True)
    with c3: st.markdown('<div class="gini-panel gini-softmint"><b>추천 이유까지 함께</b><p class="gini-muted">왜 추천했는지, 어떤 위험이 있는지 확인</p></div>',unsafe_allow_html=True)
    st.caption('이 서비스는 교육용 간이 탐색 도구입니다. 금융투자상품 적합성 평가, 투자자문 또는 수익 보장을 제공하지 않습니다.')


def show_quiz() -> None:
    idx=st.session_state.index
    q=QUESTIONS[idx]
    track(idx+1)
    a,b=st.columns([1.78,1],gap='large')
    with a:
        st.markdown('<span class="gini-tag">투자 성향 테스트</span>',unsafe_allow_html=True)
        st.markdown('## 기니와 함께 하나씩 골라봐요')
        st.caption('정답은 없어요. 나의 실제 상황과 더 가까운 답을 선택하세요.')
        st.progress((idx+1)/len(QUESTIONS), text=f'문항 {idx+1} / {len(QUESTIONS)} · {DIMENSIONS[q["axis"]][0]}')
        st.markdown(f'<p class="gini-step-title">{idx+1}. {escape(q["text"])}</p>',unsafe_allow_html=True)
        selected=st.session_state.answers.get(q['id'])
        for k, opt in enumerate(q['options']):
            button_label = ('✓  ' if selected==k else f'{"ABCD"[k]}.  ')+opt
            if st.button(button_label, key=f'option_{q["id"]}_{k}', type='primary' if selected==k else 'secondary', use_container_width=True):
                st.session_state.answers[q['id']]=k
                st.rerun()
        st.markdown('')
        prev, nxt=st.columns(2)
        with prev:
            if st.button('← 이전',use_container_width=True):
                if idx==0:
                    st.session_state.screen='cover'
                else:
                    st.session_state.index=idx-1
                st.rerun()
        with nxt:
            if st.button('결과 보기 →' if idx==len(QUESTIONS)-1 else '다음 →',type='primary',disabled=selected is None,use_container_width=True):
                if idx==len(QUESTIONS)-1:
                    st.session_state.screen='result'
                else:
                    st.session_state.index=idx+1
                st.rerun()
        st.caption('이전 버튼으로 돌아가 답변을 수정할 수 있어요. 선택을 바꾸면 분석 결과에도 반영됩니다.')
    with b:
        mascot('고민기니.png', width=260)
        st.markdown('<div class="gini-panel gini-softblue"><b>기니의 한마디</b><p class="gini-muted">다른 사람의 답이 아닌, 내 실제 상황을 기준으로 선택해 주세요. 결과는 마지막에 확인할 수 있어요.</p></div>',unsafe_allow_html=True)


def show_result() -> None:
    if len(st.session_state.answers)!=len(QUESTIONS):
        st.session_state.screen='quiz'; st.rerun()
    res=evaluate(st.session_state.answers)
    track(len(QUESTIONS)+1)
    left, right=st.columns([1,1.7],gap='large',vertical_alignment='center')
    with left: mascot('성공기니.png', width=385)
    with right:
        st.markdown('<span class="gini-tag">결승점 도착 · 분석 완료</span>',unsafe_allow_html=True)
        st.markdown('<div class="gini-hero-title"><span>기니의 추천 결과</span>가<br>나왔어요!</div>',unsafe_allow_html=True)
        st.markdown('<p class="gini-muted">이번 응답에서 나타난 투자 성향과 살펴볼 만한 상품 유형을 정리했어요.</p>',unsafe_allow_html=True)
        st.markdown(f'<div class="gini-panel gini-softblue"><b>당신의 투자 성향</b><div class="gini-big">{escape(res["category"])}</div><span class="gini-minor">자기 응답 기반 분류 · 공식 적합성 판정 아님</span></div>',unsafe_allow_html=True)
    c1,c2=st.columns([1.2,1],gap='large')
    with c1:
        st.markdown('### 추천 투자 상품 유형')
        for key in res['products']:
            title, desc, warning=PRODUCTS[key]
            with st.container(border=True):
                st.markdown(f'**{title}**')
                st.write(desc)
                st.caption(f'유의점 · {warning}')
        st.caption('상품명은 유형 예시일 뿐 특정 종목·금융회사를 추천하는 것이 아닙니다.')
    with c2:
        st.markdown('### 추천 근거')
        for i,reason in enumerate(res['reasons'],start=1):
            st.markdown(f'**{i}.** {reason}')
        st.markdown('')
        show_stats(st.session_state.answers)
    st.markdown('### 답변 상세 및 분석 기준')
    # st.expander의 Material Icon 렌더링이 일부 배포 환경에서 깨지는 현상을 피합니다.
    if 'show_details' not in st.session_state:
        st.session_state.show_details = False
    detail_label = '답변 상세 접기 ▲' if st.session_state.show_details else '내 답변 10개와 계산 기준 펼쳐보기 ▼'
    if st.button(detail_label, key='toggle_result_details', use_container_width=True):
        st.session_state.show_details = not st.session_state.show_details
        st.rerun()
    if st.session_state.show_details:
        with st.container(border=True):
            for i, q in enumerate(QUESTIONS, 1):
                opt = st.session_state.answers[q['id']]
                st.markdown(f'**{i}. {q["text"]}**')
                st.write(f'선택: {q["options"][opt]} (점수 {q["scores"][opt]}/3)')
                st.divider()
            st.markdown('**계산 방식**')
            st.write('각 차원의 선택지 점수(0~3)의 산술평균을 구해 100점 만점으로 환산합니다. 손실 감내 점수와 재무적 여력 점수 중 낮은 값을 실질 위험 수준으로 사용합니다. 투자 기간이 매우 짧거나 현금이 급하게 필요하면 안정 우선 분류를 적용합니다. 추천 유형은 코드에 정의된 규칙에 따라 결정됩니다.')
    st.info('투자 전에 비상자금 확보 여부, 원금 손실 가능성, 환금성, 수수료·세금 및 상품 설명서를 별도로 확인하세요. 이 설문은 간이 교육용이며 금융기관의 정식 투자자정보 확인 절차를 대신하지 않습니다.')
    p,n=st.columns(2)
    with p:
        if st.button('← 이전 답변 수정하기',use_container_width=True):
            st.session_state.index=len(QUESTIONS)-1
            st.session_state.screen='quiz';st.rerun()
    with n:
        if st.button('처음부터 다시 테스트하기',type='primary',use_container_width=True):
            reset();st.rerun()


initialize()
if st.session_state.screen=='cover':show_cover()
elif st.session_state.screen=='quiz':show_quiz()
else:show_result()
