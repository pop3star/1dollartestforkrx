#!/usr/bin/env python3
"""
워렌 버핏 $1 테스트 — Streamlit 웹 앱 (DART OpenAPI 버전)
EPS/DPS 데이터: 금융감독원 DART OpenAPI (OpenDartReader)
주가 데이터   : FinanceDataReader
실행: streamlit run warren_buffett_app.py
"""

import streamlit as st

st.set_page_config(
    page_title="워렌 버핏 $1 테스트",
    page_icon="💰",
    layout="wide",
)

# ── 패키지 자동 설치 ──────────────────────────────────────────
import subprocess, sys

def _pip(pkg):
    subprocess.run([sys.executable, "-m", "pip", "install", pkg, "-q"],
                   capture_output=True)

for _pkg, _imp in [
    ("finance-datareader", "FinanceDataReader"),
    ("plotly",             "plotly"),
    ("pandas",             "pandas"),
    ("numpy",              "numpy"),
    ("opendartreader",     "OpenDartReader"),
]:
    try:
        __import__(_imp)
    except ImportError:
        with st.spinner(f"{_pkg} 설치 중..."):
            _pip(_pkg)

import re, time, json
from datetime import datetime

try:
    import pandas as pd
    import numpy as np
    import FinanceDataReader as fdr
    import plotly.graph_objects as go
    import OpenDartReader as odr
    READY = True
except ImportError as e:
    st.error(
        f"패키지 로드 실패: {e}\n\n"
        "아래 명령어 실행 후 앱 재시작:\n"
        "`pip install finance-datareader plotly opendartreader`"
    )
    st.stop()

# pykrx: 선택적 의존성 (종목명 폴백용 — 없어도 DART로 대체)
try:
    from pykrx import stock as pyk
except Exception:
    pyk = None

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── 기본 레이아웃 ── */
[data-testid="stAppViewContainer"] { background: #0d1117; }
[data-testid="stSidebar"] { background: #161b22 !important; border-right: 1px solid #30363d; }
[data-testid="stMetric"] { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 14px 18px; }
[data-testid="stMetricValue"] { font-size: 1.8em !important; }

/* ── 커스텀 박스 ── */
.theory-box { background:#161b22; border:1px solid #30363d; border-left:4px solid #f0b429;
  border-radius:8px; padding:18px 22px; margin-bottom:14px; font-size:.88em; color:#8b949e; line-height:1.75; }
.warn-box { background:#1c1500; border:1px solid #4d3800; border-radius:8px;
  padding:14px 18px; font-size:.84em; color:#d4a017; line-height:1.7; }
.dart-box { background:#0d2137; border:1px solid #1f4f7a; border-left:4px solid #388bfd;
  border-radius:8px; padding:14px 18px; font-size:.84em; color:#8b949e; line-height:1.7; }
.guide-row { display:flex; gap:10px; flex-wrap:wrap; margin-top:10px; }
.guide-badge { border-radius:6px; padding:5px 12px; font-size:.82em; font-weight:600; white-space:nowrap; }
.badge-great  { background:#0f3a1f; color:#3fb950; border:1px solid #1a4731; }
.badge-pass   { background:#0d2137; color:#58a6ff; border:1px solid #1f4f7a; }
.badge-warn   { background:#1c1500; color:#f0b429; border:1px solid #4d3800; }
.badge-fail   { background:#3d1515; color:#f85149; border:1px solid #5a1f1f; }
code { background:#0d1117; color:#79c0ff; padding:2px 6px; border-radius:3px; font-size:.9em; }

/* ── 모바일 배너 (데스크탑에서는 숨김) ── */
.mobile-banner { display:none; background:#161b22; border:1px solid #388bfd;
  border-left:4px solid #388bfd; border-radius:8px; padding:13px 16px;
  margin-bottom:16px; font-size:.87em; color:#8b949e; line-height:1.7; }

/* ════ 모바일 반응형 (768px 이하) ════ */
@media screen and (max-width: 768px) {
  /* 모바일 배너 표시 */
  .mobile-banner { display:block !important; }

  /* 메트릭 카드 — 작게 */
  [data-testid="stMetric"] { padding:10px 12px; }
  [data-testid="stMetricValue"] { font-size:1.3em !important; }

  /* 박스 폰트 */
  .theory-box { font-size:.82em; padding:13px 15px; }
  .warn-box   { font-size:.80em; padding:11px 13px; }

  /* 컬럼 세로 스택 */
  div[data-testid="column"] {
    width:100% !important;
    min-width:100% !important;
    flex:0 0 100% !important;
  }

  /* 데이터 테이블 가로 스크롤 */
  [data-testid="stDataFrame"] { overflow-x:auto !important; }
  [data-testid="stDataFrame"] > div { overflow-x:auto !important; }

  /* 버튼 터치 영역 확보 */
  .stButton > button { min-height:44px; font-size:.95em; }

  /* 헤더 크기 조정 */
  h2 { font-size:1.3em !important; }
  h3 { font-size:1.1em !important; }

  /* 차트 높이 제한 */
  .js-plotly-plot .plotly { max-height:250px; }

  /* Expander 내부 패딩 */
  [data-testid="stExpander"] > div { padding:10px 12px !important; }

  /* 사이드바 토글 버튼 강조 */
  [data-testid="collapsedControl"] {
    background:#1f6feb !important;
    border-radius:8px !important;
  }
}

/* ════ 태블릿 (769~1024px) ════ */
@media screen and (min-width: 769px) and (max-width: 1024px) {
  [data-testid="stMetricValue"] { font-size:1.5em !important; }
  .theory-box { font-size:.85em; }
}
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
# DART 관련 함수
# ════════════════════════════════════════════════════════════════

@st.cache_resource(ttl=3600)
def init_dart(api_key: str):
    """DART 인스턴스 초기화 및 기업코드 목록 로드 (1시간 캐시)"""
    # import OpenDartReader as odr 시, odr 자체가 클래스이므로 odr(api_key) 로 직접 호출
    dart_inst = odr(api_key)
    codes = dart_inst.corp_codes   # DataFrame: corp_code, corp_name, stock_code, modify_date
    return dart_inst, codes


def ticker_to_corp_code(ticker: str, corp_codes: pd.DataFrame):
    """6자리 주식코드 → DART corp_code (8자리)"""
    row = corp_codes[corp_codes["stock_code"] == ticker]
    return row.iloc[0]["corp_code"] if not row.empty else None


def get_eps_dps_dart(ticker: str, year: int, dart_inst, corp_codes) -> dict | None:
    """사업보고서(11011) 전체계정에서 연간 EPS/DPS 조회 (연간 루프용)"""
    corp_code = ticker_to_corp_code(ticker, corp_codes)
    if not corp_code:
        return None
    try:
        fs = dart_inst.finstate_all(corp_code, str(year), "11011")
        if fs is not None and not (isinstance(fs, pd.DataFrame) and fs.empty):
            return _extract_eps_from_fs(fs)
    except Exception:
        pass
    return None


# ════════════════════════════════════════════════════════════════
# 공통 데이터 수집 함수
# ════════════════════════════════════════════════════════════════

def get_stock_name(ticker: str, corp_codes: pd.DataFrame = None) -> str:
    """종목명 조회 (DART corp_codes 우선, pykrx 폴백)"""
    if corp_codes is not None:
        row = corp_codes[corp_codes["stock_code"] == ticker]
        if not row.empty:
            return row.iloc[0]["corp_name"]
    if pyk is not None:
        try:
            n = pyk.get_market_ticker_name(ticker)
            return n if n else ticker
        except Exception:
            pass
    return ticker


def year_end_price(ticker: str, year: int) -> float | None:
    """해당 연도의 마지막 거래일 종가 (FinanceDataReader)"""
    try:
        df = fdr.DataReader(ticker, f"{year}-11-01", f"{year}-12-31")
        if df is not None and not df.empty:
            return float(df["Close"].iloc[-1])
    except Exception:
        pass
    return None


def get_month_end_price(ticker: str, year: int, month: int) -> float | None:
    """지정 연월의 마지막 거래일 종가 — 분기/월 기준 분석용"""
    import calendar as _cal
    last_day = _cal.monthrange(year, month)[1]
    try:
        df = fdr.DataReader(
            ticker,
            f"{year}-{month:02d}-01",
            f"{year}-{month:02d}-{last_day:02d}",
        )
        if df is not None and not df.empty:
            return float(df["Close"].iloc[-1])
    except Exception:
        pass
    return None


def _extract_eps_from_fs(fs: pd.DataFrame) -> dict | None:
    """재무제표 DataFrame에서 EPS/DPS 추출 — 공통 로직"""
    nm_col  = next((c for c in fs.columns if "account_nm"    in c.lower()), None)
    amt_col = next((c for c in fs.columns if "thstrm_amount" in c.lower()), None)
    if nm_col is None or amt_col is None:
        return None

    work_fs = fs
    if "fs_div" in fs.columns:
        cfs = fs[fs["fs_div"] == "CFS"]
        work_fs = cfs if not cfs.empty else fs

    def find(kws):
        for kw in kws:
            try:
                mask = work_fs[nm_col].astype(str).str.contains(kw, na=False, regex=False)
                rows = work_fs[mask]
                if rows.empty:
                    continue
                val = rows.iloc[0][amt_col]
                if pd.notna(val) and str(val).strip() not in ("", "-", "―"):
                    return float(str(val).replace(",", "").replace(" ", ""))
            except Exception:
                pass
        return None

    eps = find(["기본주당이익(손실)", "기본주당순이익(손실)",
                "기본주당이익", "기본주당순이익", "주당순이익", "주당이익", "주당손익"])
    dps = find(["주당배당금", "주당현금배당금", "현금배당금(주당)", "1주당 배당금"])
    if eps is not None:
        return {"EPS": eps, "DPS": dps or 0.0}
    return None


def get_eps_dps_latest(ticker: str, year: int,
                       dart_inst, corp_codes) -> tuple:
    """
    지정 연도 기준 최신 공시에서 EPS/DPS 조회.
    연간(11011) → 3분기(11014) → 반기(11012) → 1분기(11013) 순 시도.
    반환: (dict | None, label | None)
    """
    corp_code = ticker_to_corp_code(ticker, corp_codes)
    if not corp_code:
        return None, None

    attempts = [
        ("11011", f"{year}년 연간"),
        ("11014", f"{year}년 3분기(9개월)"),
        ("11012", f"{year}년 반기(6개월)"),
        ("11013", f"{year}년 1분기(3개월)"),
    ]
    for reprt_code, label in attempts:
        try:
            fs = dart_inst.finstate_all(corp_code, str(year), reprt_code)
            if fs is None or (isinstance(fs, pd.DataFrame) and fs.empty):
                continue
            result = _extract_eps_from_fs(fs)
            if result:
                return result, label
        except Exception:
            continue
    return None, None


def analyze_stock(
    ticker: str,
    start_year: int,
    end_year: int,
    end_month: int = 12,          # ← NEW: 종료 월 (1~12). 12이면 연말 기준
    dart_inst=None,
    corp_codes: pd.DataFrame = None,
    log_fn=None,
) -> dict | None:

    def log(msg):
        if log_fn:
            log_fn(msg)

    name = get_stock_name(ticker, corp_codes)
    log(f"[{ticker}] {name} — 주가 수집 중...")

    # ── 연말 주가 수집 (start_year ~ end_year-1, 차트용) ──────────
    price_by_year: dict[int, float] = {}
    for y in range(start_year, end_year):          # end_year 연말은 따로 처리
        p = year_end_price(ticker, y)
        if p:
            price_by_year[y] = p
        time.sleep(0.04)

    # ── 종료 시점 주가 (지정 연월 마지막 거래일) ─────────────────
    end_price = get_month_end_price(ticker, end_year, end_month)
    if end_price is None:
        end_price = year_end_price(ticker, end_year)   # 폴백: 연말가
    if end_price is not None:
        price_by_year[end_year] = end_price

    if len(price_by_year) < 3:
        log(f"[{ticker}] 주가 데이터 부족 ({len(price_by_year)}년) — 건너뜀")
        return None

    avail       = sorted(price_by_year)
    act_start   = avail[0]
    start_price = price_by_year[act_start]

    if end_price is None:
        log(f"[{ticker}] 종료 시점 주가 없음 — 건너뜀")
        return None

    log(f"[{ticker}] {name} — 재무 데이터 수집 중 ({act_start}~{end_year}.{end_month:02d})...")

    # ── EPS/DPS 수집 ───────────────────────────────────────────
    # 과거 연도: 사업보고서(11011) 연간 EPS
    # 마지막 연도(end_year-1): 연간 없으면 분기 공시 폴백
    fund_by_year: dict[int, dict] = {}
    latest_label: str | None = None

    for y in range(act_start, end_year):
        is_last = (y == end_year - 1)
        if dart_inst is not None and corp_codes is not None:
            if is_last:
                fd, lbl = get_eps_dps_latest(ticker, y, dart_inst, corp_codes)
                if fd:
                    latest_label = lbl
                    log(f"[{ticker}] {y}년 EPS 공시: {lbl}")
            else:
                fd = get_eps_dps_dart(ticker, y, dart_inst, corp_codes)
        else:
            fd = None
        if fd:
            fund_by_year[y] = fd
        time.sleep(0.2)

    if len(fund_by_year) < 3:
        log(f"[{ticker}] 재무 데이터 부족 ({len(fund_by_year)}개년) — 건너뜀")
        return None

    # ── $1 테스트 계산 ─────────────────────────────────────────
    total_retained = sum(v["EPS"] - v["DPS"] for v in fund_by_year.values())
    price_appr     = end_price - start_price

    # 분석 기간(연수): 소수점 지원 (예: 2010.12 → 2026.03 = 15.25년)
    n_years_frac = (end_year - act_start) + (end_month - 12) / 12
    n_years_frac = max(n_years_frac, 0.5)   # 최소 0.5년

    if total_retained > 0:
        dollar_ratio = price_appr / total_retained
        passed       = dollar_ratio >= 1.0
    else:
        dollar_ratio = None
        passed       = False

    price_cagr = (
        ((end_price / start_price) ** (1 / n_years_frac) - 1) * 100
        if n_years_frac > 0 and start_price > 0 else None
    )

    chart_data, cum = [], 0.0
    for y in sorted(price_by_year):
        fd = fund_by_year.get(y)
        if fd:
            ret_y = fd["EPS"] - fd["DPS"]
            cum  += ret_y
        else:
            ret_y = None
        label = f"{y}.{end_month:02d}" if y == end_year and end_month != 12 else str(y)
        chart_data.append({
            "year":         label,
            "close":        price_by_year.get(y),
            "price_change": round(price_by_year.get(y, start_price) - start_price, 0),
            "EPS":          fd["EPS"] if fd else None,
            "DPS":          fd["DPS"] if fd else None,
            "retained_eps": round(ret_y, 0) if ret_y is not None else None,
            "cum_retained": round(cum, 0),
        })

    end_label = f"{end_year}.{end_month:02d}" if end_month != 12 else str(end_year)
    status = "✅ 통과" if passed else (
        "❌ 미통과" if dollar_ratio is not None else "⚠️ 계산불가"
    )
    log(
        f"[{ticker}] {name} — $1 비율: "
        f"{'N/A' if dollar_ratio is None else f'{dollar_ratio:.2f}x'}  {status}"
    )

    return {
        "ticker":                 ticker,
        "name":                   name,
        "start_year":             act_start,
        "end_year":               end_year,
        "end_month":              end_month,
        "end_label":              end_label,
        "latest_eps_label":       latest_label,
        "years_analyzed":         round(n_years_frac, 2),
        "start_price":            round(start_price, 0),
        "end_price":              round(end_price, 0),
        "price_appreciation":     round(price_appr, 0),
        "price_appreciation_pct": round(price_appr / start_price * 100, 1) if start_price else None,
        "total_retained_eps":     round(total_retained, 0),
        "dollar_test_ratio":      round(dollar_ratio, 2) if dollar_ratio is not None else None,
        "passed":                 passed,
        "price_cagr":             round(price_cagr, 1) if price_cagr is not None else None,
        "data_years_count":       len(fund_by_year),
        "chart_data":             chart_data,
    }


# ════════════════════════════════════════════════════════════════
# HTML 다운로드용 템플릿
# ════════════════════════════════════════════════════════════════

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>워렌 버핏 $1 테스트</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Malgun Gothic',sans-serif;background:#0d1117;color:#e6edf3}
.hdr{background:linear-gradient(135deg,#1f6feb,#388bfd);padding:26px 36px;text-align:center}
.hdr h1{font-size:1.8em;font-weight:700;margin-bottom:5px}.hdr p{opacity:.85;font-size:.9em}
.hdr small{opacity:.6;font-size:.77em;display:block;margin-top:3px}
.wrap{max-width:1360px;margin:0 auto;padding:26px 16px}
.theory{background:#161b22;border:1px solid #30363d;border-left:4px solid #f0b429;border-radius:8px;padding:16px 20px;margin-bottom:22px}
.theory h3{color:#f0b429;margin-bottom:7px;font-size:.93em}
.theory p{color:#8b949e;line-height:1.65;font-size:.87em}
.formula{background:#0d1117;border:1px solid #30363d;border-radius:5px;padding:9px 15px;margin-top:9px;font-family:monospace;color:#79c0ff;font-size:.86em}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:11px;margin-bottom:24px}
.stat{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;text-align:center}
.stat-n{font-size:1.9em;font-weight:700;margin-bottom:3px}
.stat-l{color:#8b949e;font-size:.82em}
.c-pass{color:#3fb950}.c-fail{color:#f85149}.c-tot{color:#58a6ff}.c-rate{color:#f0b429}
.sec-title{font-size:1.05em;font-weight:600;margin-bottom:12px;border-bottom:1px solid #30363d;padding-bottom:7px}
.ctrl{display:flex;gap:7px;margin-bottom:11px;flex-wrap:wrap;align-items:center}
.search{background:#161b22;border:1px solid #30363d;color:#e6edf3;padding:6px 12px;border-radius:6px;font-size:.87em;width:185px}
.btn{background:#161b22;border:1px solid #30363d;color:#8b949e;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:.82em;transition:all .2s}
.btn:hover,.btn.on{background:#1f6feb;border-color:#388bfd;color:#fff}
.tbl-wrap{background:#161b22;border:1px solid #30363d;border-radius:8px;overflow:hidden;margin-bottom:24px;overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:.85em}
th{background:#1c2128;padding:9px 12px;text-align:left;color:#8b949e;font-weight:600;cursor:pointer;user-select:none;white-space:nowrap}
th:hover{color:#e6edf3}
td{padding:9px 12px;border-top:1px solid #21262d;cursor:pointer;transition:background .15s}
tr:hover td{background:#1c2128}
.b-pass{background:#0f3a1f;color:#3fb950;padding:2px 8px;border-radius:10px;font-size:.77em;font-weight:600;border:1px solid #1a4731}
.b-fail{background:#3d1515;color:#f85149;padding:2px 8px;border-radius:10px;font-size:.77em;font-weight:600;border:1px solid #5a1f1f}
.b-na{background:#1c2128;color:#8b949e;padding:2px 8px;border-radius:10px;font-size:.77em}
.r-hi{color:#3fb950;font-weight:600}.r-md{color:#f0b429;font-weight:600}.r-lo{color:#f85149;font-weight:600}
.p-pos{color:#3fb950}.p-neg{color:#f85149}.na{color:#484f58}
.detail{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin-bottom:24px;display:none}
.detail.on{display:block}
.d-hdr{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px}
.d-title{font-size:1.2em;font-weight:700}.d-sub{color:#8b949e;font-size:.84em;margin-top:3px}
.close-btn{background:#21262d;border:1px solid #30363d;color:#8b949e;padding:5px 10px;border-radius:5px;cursor:pointer;font-size:.81em}
.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:9px;margin-bottom:20px}
.metric{background:#0d1117;border:1px solid #21262d;border-radius:7px;padding:12px}
.m-lbl{color:#8b949e;font-size:.77em;margin-bottom:3px}.m-val{font-size:1.04em;font-weight:600}
.chart-box{position:relative;height:300px;margin-bottom:16px}
.ytbl{width:100%;border-collapse:collapse;font-size:.82em}
.ytbl th{background:#0d1117;padding:6px 10px;text-align:right;color:#8b949e}
.ytbl th:first-child{text-align:left}
.ytbl td{padding:6px 10px;border-top:1px solid #21262d;text-align:right}
.ytbl td:first-child{text-align:left}
.pos{color:#3fb950}.neg{color:#f85149}
footer{text-align:center;padding:16px;color:#484f58;font-size:.77em;border-top:1px solid #21262d}
</style></head><body>
<div class="hdr"><h1>💰 워렌 버핏 $1 테스트</h1>
<p>유보이익 1원당 주가 상승분 분석 — 국내 상장 주식</p>
<small>분석 기준일: __ANALYSIS_DATE__</small></div>
<div class="wrap">
<div class="theory"><h3>📚 $1 테스트란?</h3>
<p>워렌 버핏이 제시한 경영진 역량 평가 지표. 기업이 유보한 이익 1원이 시가총액을 최소 1원 이상 증가시켜야 합니다. 비율 ≥ 1 이면 자본을 효율적으로 재투자 중. 단독 지표로 투자 결정에 사용하지 마세요.</p>
<div class="formula">$1 테스트 비율 = 주가 상승분 ÷ 주당 누적 유보이익 (Σ EPS − Σ DPS) &nbsp;|&nbsp; ✅ 통과 기준: ≥ 1.0</div></div>
<div id="stats" class="stats"></div>
<div class="sec-title">📊 분석 결과</div>
<div class="ctrl">
<input type="text" class="search" id="q" placeholder="종목명·코드 검색..." oninput="render()">
<button class="btn on" id="f-all" onclick="setFilter('all',this)">전체</button>
<button class="btn" id="f-pass" onclick="setFilter('pass',this)">✅ 통과</button>
<button class="btn" id="f-fail" onclick="setFilter('fail',this)">❌ 미통과</button>
<button class="btn" onclick="setSort('ratio_d')">$1비율↓</button>
<button class="btn" onclick="setSort('cagr')">CAGR↓</button>
</div>
<div class="tbl-wrap"><table>
<thead><tr>
<th onclick="setSort('name')">종목명 ↕</th><th>코드</th><th>분석기간</th>
<th onclick="setSort('start')">시작가 ↕</th><th onclick="setSort('end')">현재가 ↕</th>
<th onclick="setSort('pct')">수익률 ↕</th><th onclick="setSort('cagr')">CAGR ↕</th>
<th onclick="setSort('retained')">누적유보EPS ↕</th>
<th onclick="setSort('ratio_d')">$1 비율 ↕</th><th>결과</th>
</tr></thead><tbody id="tbody"></tbody></table></div>
<div id="detail" class="detail">
<div class="d-hdr"><div><div id="d-title" class="d-title"></div><div id="d-sub" class="d-sub"></div></div>
<button class="close-btn" onclick="closeDetail()">✕ 닫기</button></div>
<div id="d-metrics" class="metrics"></div>
<div class="chart-box"><canvas id="d-chart"></canvas></div>
<div id="d-ytbl" style="overflow-x:auto"></div>
</div></div>
<footer>⚠️ 투자 권유 아님. 데이터: FinanceDataReader(주가), 금융감독원 DART OpenAPI(EPS/DPS)</footer>
<script>
const DATA=__DATA_JSON__;
let filter='all',sort='ratio_d',chart=null;
const N=(v,d=0)=>v==null?'<span class="na">N/A</span>':v.toLocaleString('ko-KR',{maximumFractionDigits:d});
const Pct=v=>v==null?'<span class="na">N/A</span>':`<span class="${v>=0?'p-pos':'p-neg'}">${v>=0?'+':''}${v.toFixed(1)}%</span>`;
const Ratio=r=>r==null?'<span class="na">N/A</span>':`<span class="${r>=2?'r-hi':r>=1?'r-md':'r-lo'}">${r.toFixed(2)}x</span>`;
function renderStats(){
  const t=DATA.length,p=DATA.filter(d=>d.passed).length,f=DATA.filter(d=>!d.passed&&d.dollar_test_ratio!=null).length;
  const na=DATA.filter(d=>d.dollar_test_ratio==null).length,rate=t-na>0?p/(t-na)*100:0;
  document.getElementById('stats').innerHTML=`
  <div class="stat"><div class="stat-n c-tot">${t}</div><div class="stat-l">분석 종목</div></div>
  <div class="stat"><div class="stat-n c-pass">${p}</div><div class="stat-l">✅ 통과</div></div>
  <div class="stat"><div class="stat-n c-fail">${f}</div><div class="stat-l">❌ 미통과</div></div>
  <div class="stat"><div class="stat-n c-rate">${rate.toFixed(0)}%</div><div class="stat-l">통과율</div></div>`;
}
function getData(){
  let d=[...DATA];
  const q=(document.getElementById('q')?.value||'').toLowerCase();
  if(q)d=d.filter(x=>x.name.toLowerCase().includes(q)||x.ticker.includes(q));
  if(filter==='pass')d=d.filter(x=>x.passed);
  if(filter==='fail')d=d.filter(x=>!x.passed&&x.dollar_test_ratio!=null);
  const sf={ratio_d:(a,b)=>(b.dollar_test_ratio??-999)-(a.dollar_test_ratio??-999),
    cagr:(a,b)=>(b.price_cagr??-999)-(a.price_cagr??-999),
    pct:(a,b)=>(b.price_appreciation_pct??-999)-(a.price_appreciation_pct??-999),
    name:(a,b)=>a.name.localeCompare(b.name,'ko'),
    retained:(a,b)=>(b.total_retained_eps??-999)-(a.total_retained_eps??-999),
    start:(a,b)=>b.start_price-a.start_price,end:(a,b)=>b.end_price-a.end_price};
  if(sf[sort])d.sort(sf[sort]);return d;
}
function render(){
  document.getElementById('tbody').innerHTML=getData().map(x=>`
  <tr onclick="showDetail('${x.ticker}')">
  <td><strong>${x.name}</strong></td><td style="color:#8b949e">${x.ticker}</td>
  <td style="color:#8b949e;font-size:.81em">${x.start_year}~${x.end_label}(${x.years_analyzed}y)</td>
  <td>${N(x.start_price)}원</td><td>${N(x.end_price)}원</td>
  <td>${Pct(x.price_appreciation_pct)}</td><td>${Pct(x.price_cagr)}</td>
  <td>${N(x.total_retained_eps)}원</td><td>${Ratio(x.dollar_test_ratio)}</td>
  <td>${x.dollar_test_ratio==null?'<span class="b-na">계산불가</span>':x.passed?'<span class="b-pass">✅ 통과</span>':'<span class="b-fail">❌ 미통과</span>'}</td>
  </tr>`).join('');
}
function setFilter(f,el){filter=f;document.querySelectorAll('#f-all,#f-pass,#f-fail').forEach(b=>b.classList.remove('on'));el.classList.add('on');render();}
function setSort(s){sort=s;render();}
function showDetail(ticker){
  const x=DATA.find(d=>d.ticker===ticker);if(!x)return;
  document.getElementById('d-title').textContent=x.name;
  document.getElementById('d-sub').textContent=`코드:${x.ticker} | 기간:${x.start_year}~${x.end_label}(${x.years_analyzed}년) | 재무확보:${x.data_years_count}개년`;
  const pstr=v=>v!=null?(v>=0?'+':'')+v.toFixed(1)+'%':'N/A';
  const ms=[['시작가',N(x.start_price)+'원'],['현재가',N(x.end_price)+'원'],
    ['주가상승분',N(x.price_appreciation)+'원 ('+pstr(x.price_appreciation_pct)+')'],
    ['CAGR',pstr(x.price_cagr)],['누적유보EPS',N(x.total_retained_eps)+'원'],
    ['💰 $1 비율',x.dollar_test_ratio!=null?x.dollar_test_ratio.toFixed(2)+'x':'N/A'],
    ['결과',x.dollar_test_ratio==null?'⚠️계산불가':x.passed?'✅통과':'❌미통과']];
  document.getElementById('d-metrics').innerHTML=ms.map(([l,v])=>`<div class="metric"><div class="m-lbl">${l}</div><div class="m-val">${v}</div></div>`).join('');
  if(chart)chart.destroy();
  const cd=x.chart_data||[];
  chart=new Chart(document.getElementById('d-chart').getContext('2d'),{
    type:'line',data:{labels:cd.map(c=>c.year),
    datasets:[{label:'누적 유보이익/주(원)',data:cd.map(c=>c.cum_retained),borderColor:'#f0b429',backgroundColor:'rgba(240,180,41,.07)',borderWidth:2,tension:.35,pointRadius:3},
    {label:'주가 상승분(원)',data:cd.map(c=>c.price_change),borderColor:'#58a6ff',backgroundColor:'rgba(88,166,255,.07)',borderWidth:2,tension:.35,pointRadius:3}]},
    options:{responsive:true,maintainAspectRatio:false,
    plugins:{legend:{labels:{color:'#e6edf3'}},tooltip:{callbacks:{label:c=>`${c.dataset.label}: ${c.parsed.y?.toLocaleString('ko-KR')}원`}}},
    scales:{x:{ticks:{color:'#8b949e'},grid:{color:'#21262d'}},y:{ticks:{color:'#8b949e',callback:v=>v.toLocaleString('ko-KR')+'원'},grid:{color:'#21262d'}}}}});
  const fn=v=>v!=null?v.toLocaleString('ko-KR'):'<span class="na">-</span>';
  document.getElementById('d-ytbl').innerHTML=`<table class="ytbl"><thead><tr><th style="text-align:left">연도</th><th>주가</th><th>EPS</th><th>DPS</th><th>유보EPS</th><th>누적유보EPS</th></tr></thead><tbody>
  ${cd.map(c=>`<tr><td>${c.year}</td><td>${fn(c.close)}</td><td>${fn(c.EPS)}</td><td>${fn(c.DPS)}</td>
  <td class="${c.retained_eps>0?'pos':c.retained_eps<0?'neg':''}">${fn(c.retained_eps)}</td>
  <td>${c.cum_retained.toLocaleString('ko-KR')}</td></tr>`).join('')}</tbody></table>`;
  const p=document.getElementById('detail');p.classList.add('on');p.scrollIntoView({behavior:'smooth'});
}
function closeDetail(){document.getElementById('detail').classList.remove('on');if(chart){chart.destroy();chart=null;}}
renderStats();render();
</script></body></html>"""


def build_html(results: list, analysis_date: str) -> str:
    return (HTML_TEMPLATE
            .replace("__DATA_JSON__",     json.dumps(results, ensure_ascii=False))
            .replace("__ANALYSIS_DATE__", analysis_date))


# ════════════════════════════════════════════════════════════════
# UI — 사이드바
# ════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 💰 워렌 버핏 $1 테스트")
    st.markdown("---")

    # ── DART API 키 ──────────────────────────────────────────
    # Streamlit Cloud Secrets → 환경변수 → 직접 입력 순으로 로드
    _secret_key = ""
    try:
        _secret_key = st.secrets.get("DART_API_KEY", "")
    except Exception:
        pass

    st.markdown("#### 🔑 DART API 키")
    _dart_input = st.text_input(
        label="금융감독원 DART API 키",
        type="password",
        value="",
        placeholder="비워두면 서버 기본 키 사용 / 직접 입력 시 대체",
        help="https://opendart.fss.or.kr 에서 무료 발급 (이메일 인증 즉시 사용 가능)",
    )
    # 직접 입력 우선, 없으면 서버 Secret 키 폴백
    dart_api_key = _dart_input if _dart_input else _secret_key

    if _secret_key and not _dart_input:
        st.caption("🔒 서버 기본 키 사용 중 — 직접 입력하면 해당 키로 대체됩니다.")
    elif _dart_input:
        st.caption("🔑 직접 입력한 API 키를 사용합니다.")

    if not dart_api_key:
        st.markdown("""<div class="dart-box">
🔑 <b>DART API 키 발급 방법</b><br>
① <a href="https://opendart.fss.or.kr" target="_blank" style="color:#58a6ff">opendart.fss.or.kr</a> 접속<br>
② 회원가입 → 인증키 신청<br>
③ 이메일 승인 후 키 복사<br>
④ 위 입력창에 붙여넣기<br>
<small style="color:#484f58">무료 · 하루 10,000건 제한</small>
</div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── 종목 코드 / 종목명 ─────────────────────────────────────
    st.markdown("#### 📋 종목 입력")
    ticker_input = st.text_area(
        label="종목코드 또는 종목명 (줄바꿈·쉼표·공백 모두 허용)",
        placeholder="005930\n삼성전자\n000660, SK하이닉스",
        height=130,
        help=(
            "6자리 종목코드 또는 종목명 혼합 입력 가능.\n"
            "예) 005930, 삼성전자, SK하이닉스\n"
            "정확한 이름을 모를 땐 아래 🔍 검색창을 이용하세요."
        ),
    )

    # ── 분석 기간 ─────────────────────────────────────────────
    st.markdown("#### 📅 분석 기간")
    col1, col2 = st.columns(2)
    with col1:
        start_year = st.number_input("시작 연도", min_value=2000,
                                     max_value=2035, value=2010, step=1)
    with col2:
        end_date_str = st.text_input(
            "종료 연월",
            value="2026.03",
            placeholder="2024 또는 2026.03",
            help="연도만 입력(예: 2024) 또는 연·월 입력(예: 2026.03). 월 기준 시 해당 월 마지막 거래일 종가와 최신 공시 재무 사용.",
        )

    # 종료 연도·월 파싱
    end_year, end_month, _date_ok = 2026, 3, False
    _m = re.match(r"^(\d{4})(?:\.(\d{1,2}))?$", end_date_str.strip())
    if _m:
        _ey = int(_m.group(1))
        _em = int(_m.group(2)) if _m.group(2) else 12
        if 2001 <= _ey <= 2040 and 1 <= _em <= 12:
            end_year, end_month, _date_ok = _ey, _em, True
    if not _date_ok:
        st.error("❌ 형식 오류: 연도(예: 2024) 또는 연·월(예: 2026.03) 형식으로 입력하세요.")

    if start_year >= end_year:
        st.error("시작연도 < 종료연도 이어야 합니다.")

    st.markdown("---")

    _run_disabled = (not dart_api_key) or (not _date_ok) or (start_year >= end_year)
    run_btn = st.button(
        "🚀 분석 시작",
        type="primary",
        use_container_width=True,
        disabled=_run_disabled,
    )
    if not dart_api_key:
        st.caption("⬆️ DART API 키를 먼저 입력하세요")

    st.markdown("---")
    st.markdown("""<div style="color:#8b949e;font-size:.8em;line-height:1.8">
<b>데이터 소스</b><br>
주가: FinanceDataReader<br>
EPS/DPS: DART OpenAPI<br><br>
<b>소요 시간</b><br>
종목당 약 1~2분<br><br>
⚠️ 투자 권유 아님
</div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
# UI — 메인
# ════════════════════════════════════════════════════════════════

st.markdown("## 💰 워렌 버핏 $1 테스트")

# ── 모바일 전용 배너 ──────────────────────────────────────────
st.markdown("""<div class="mobile-banner">
📱 <b>모바일 이용 안내</b><br>
화면 왼쪽 상단 <b>☰ 메뉴</b>를 열어 종목·기간을 입력한 뒤 분석을 시작하세요.<br>
분석이 완료되면 이 아래로 결과가 표시됩니다.
</div>""", unsafe_allow_html=True)

# ── $1 테스트 상세 설명 ───────────────────────────────────────
st.markdown("""<div class="theory-box">
<b style="color:#f0b429;font-size:1.04em">📚 워렌 버핏의 $1 테스트 — 기본 의의</b><br><br>

<b style="color:#e6edf3">💡 핵심 아이디어</b><br>
1984년 버크셔 해서웨이 주주서한에서 버핏이 명시적으로 제시한 <b>경영진 자본 배분 능력 평가 지표</b>입니다.
기업이 주주에게 배당하지 않고 내부에 유보한 이익 <b>1원</b>을 경영진이 재투자했을 때,
그 재투자가 효율적이라면 기업가치(주가)는 최소 <b>1원 이상</b> 올라야 한다는 논리입니다.<br><br>

<div style="background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:9px 15px;margin:8px 0;font-family:monospace;color:#79c0ff;font-size:.9em">
$1 비율 = 주가 상승분 ÷ 주당 누적 유보이익 &nbsp;|&nbsp; 유보이익 = Σ(EPS − DPS)
</div>

<b style="color:#e6edf3">🏦 왜 의미 있는가?</b><br>
재투자 수익률(ROIC)이 자본 비용을 지속적으로 상회하는 기업은 유보이익이 복리로 증폭됩니다.
반대로 비율이 1 미만이면 &ldquo;차라리 배당해서 주주가 직접 운용했으면 더 나았을 것&rdquo;이라는 의미이며,
경영진이 자본을 비효율적으로 집행하고 있다는 신호입니다.
10년 이상 장기 분석 시 경기 사이클의 노이즈가 평균화되어 경영진의 실질 역량이 드러납니다.<br><br>

<b style="color:#e6edf3">📊 해석 기준</b>
<div class="guide-row">
  <span class="guide-badge badge-great">≥ 2.0x &nbsp;탁월한 자본 배분</span>
  <span class="guide-badge badge-pass">1.0 ~ 2.0x &nbsp;✅ 통과 (효율적)</span>
  <span class="guide-badge badge-warn">0.5 ~ 1.0x &nbsp;미흡 (개선 필요)</span>
  <span class="guide-badge badge-fail">&lt; 0.5x &nbsp;❌ 자본 배분 실패</span>
</div>
</div>""", unsafe_allow_html=True)

st.markdown("""<div class="warn-box">
⚠️ <b>반론 및 한계 — 단독 판단 금지</b><br>
① <b>시작점 편의</b> — 분석 시작 연도의 주가 수준(고점·저점)에 결과가 민감하게 반응합니다.<br>
② <b>외부 요인 개입</b> — 금리·환율·시장 심리 등 경영진과 무관한 요소가 주가에 반영됩니다.<br>
③ <b>성장주 불리</b> — 성장주는 이익 실현 전 주가가 먼저 오르는 구조라 단기 비율이 낮게 나옵니다.<br>
④ <b>비현금 EPS 포함</b> — EPS에는 감가상각, 주식보상비용 등 현금이 수반되지 않는 항목이 포함됩니다.<br>
⑤ <b>DPS 미반영</b> — 공시 특성상 주당배당금 확인이 어려워 보수적으로 DPS=0으로 처리합니다.
</div>""", unsafe_allow_html=True)

st.markdown("")

# ── DART 초기화 ───────────────────────────────────────────────
dart_instance = None
corp_codes_df  = None

if dart_api_key:
    with st.spinner("DART 기업코드 목록 로드 중... (최초 1회, 약 10초)"):
        try:
            dart_instance, corp_codes_df = init_dart(dart_api_key)
            st.success(f"✅ DART 연결 성공 — 상장기업 {len(corp_codes_df[corp_codes_df['stock_code'].str.len() == 6])}개 확인")
        except Exception as e:
            st.error(f"❌ DART 초기화 실패: {e}\nAPI 키를 확인하세요.")
            dart_instance = None

# ── 종목 이름 검색 위젯 ────────────────────────────────────────
if dart_instance is not None and corp_codes_df is not None:
    _listed_df = corp_codes_df[corp_codes_df["stock_code"].str.len() == 6].copy()

    with st.expander("🔍 종목 이름으로 검색하여 추가", expanded=False):
        _sc1, _sc2 = st.columns([4, 1])
        with _sc1:
            _sq = st.text_input(
                "회사명 검색",
                placeholder="삼성, SK, 현대, NAVER …",
                key="name_search_query",
                label_visibility="collapsed",
            )
        with _sc2:
            st.markdown("<div style='padding-top:4px'></div>", unsafe_allow_html=True)

        if _sq:
            _hits = _listed_df[
                _listed_df["corp_name"].str.contains(_sq, case=False, na=False)
            ].head(20)

            if not _hits.empty:
                _opts = [
                    f"{r['corp_name']}  ({r['stock_code']})"
                    for _, r in _hits.iterrows()
                ]
                _sel = st.selectbox(
                    f"검색 결과 {len(_hits)}건",
                    _opts,
                    key="name_search_sel",
                )
                if st.button("➕ 분석 목록에 추가", key="name_add_btn", type="secondary"):
                    _code = _sel.split("(")[-1].rstrip(")")
                    _name = _sel.split("(")[0].strip()
                    if "extra_tickers" not in st.session_state:
                        st.session_state["extra_tickers"] = []
                    if _code not in st.session_state["extra_tickers"]:
                        st.session_state["extra_tickers"].append(_code)
                        st.success(f"✅ {_name} ({_code}) 추가됨")
                        st.rerun()
                    else:
                        st.info(f"'{_name}' 은(는) 이미 목록에 있습니다.")
            else:
                st.info(f"'{_sq}' 에 해당하는 상장 종목이 없습니다.")

        # ── 검색으로 추가된 목록 표시 ──────────────────────────
        _et = st.session_state.get("extra_tickers", [])
        if _et:
            st.markdown("**현재 추가된 종목:**")
            _chips = []
            for _c in _et:
                _row = corp_codes_df[corp_codes_df["stock_code"] == _c]
                _n   = _row.iloc[0]["corp_name"] if not _row.empty else _c
                _chips.append(f"`{_c}` {_n}")
            st.markdown("&nbsp; · &nbsp;".join(_chips), unsafe_allow_html=True)

            _cc1, _cc2 = st.columns([3, 1])
            with _cc2:
                if st.button("🗑️ 목록 초기화", key="clear_extra_tickers",
                             use_container_width=True):
                    st.session_state["extra_tickers"] = []
                    st.rerun()
        else:
            st.caption("추가된 종목 없음 — 검색 후 ➕ 버튼으로 추가하세요.")

# ── 분석 실행 ─────────────────────────────────────────────────
if run_btn:
    if dart_instance is None:
        st.error("DART 연결에 실패했습니다. API 키를 확인하세요.")
        st.stop()

    raw = re.split(r"[\s,;]+", ticker_input.strip())
    tickers: list[str] = []
    _ldf = (corp_codes_df[corp_codes_df["stock_code"].str.len() == 6]
            if corp_codes_df is not None else None)

    for _t in raw:
        _t = _t.strip()
        if not _t:
            continue
        if re.match(r"^\d{1,6}$", _t):
            # ① 숫자 → 6자리 코드로 변환
            tickers.append(_t.zfill(6))
        elif _ldf is not None:
            # ② 문자열 → 종목명 검색
            _exact   = _ldf[_ldf["corp_name"] == _t]
            _partial = _ldf[_ldf["corp_name"].str.contains(_t, case=False, na=False)]
            if not _exact.empty:
                _c = _exact.iloc[0]["stock_code"]
                st.info(f"📌 '{_t}' → {_exact.iloc[0]['corp_name']} ({_c})")
                tickers.append(_c)
            elif len(_partial) == 1:
                _c = _partial.iloc[0]["stock_code"]
                st.info(f"📌 '{_t}' → {_partial.iloc[0]['corp_name']} ({_c})")
                tickers.append(_c)
            elif len(_partial) > 1:
                _c   = _partial.iloc[0]["stock_code"]
                _cnd = ", ".join(_partial["corp_name"].head(5).tolist())
                st.warning(
                    f"⚠️ '{_t}' 검색 결과 {len(_partial)}개 — "
                    f"첫 번째 사용: **{_partial.iloc[0]['corp_name']}** ({_c})\n"
                    f"후보: {_cnd}"
                )
                tickers.append(_c)
            else:
                st.warning(f"⚠️ '{_t}' — 일치하는 상장 종목이 없습니다.")
        else:
            st.warning(f"⚠️ '{_t}' — DART 미연결 상태에서는 이름 검색 불가합니다.")

    # ③ 검색 위젯으로 추가된 종목 합치기
    for _ec in st.session_state.get("extra_tickers", []):
        if _ec not in tickers:
            tickers.append(_ec)

    # 중복 제거 (입력 순서 유지)
    tickers = list(dict.fromkeys(tickers))

    if not tickers:
        st.error("유효한 종목 코드/종목명을 입력해주세요.")
        st.stop()

    total    = len(tickers)
    prog     = st.progress(0, text="분석 준비 중...")
    log_area = st.empty()
    results  = []

    for idx, ticker in enumerate(tickers):
        prog.progress(idx / total, text=f"분석 중... {idx+1}/{total}  [{ticker}]")

        _log_box = log_area

        def make_logger(box=_log_box):
            def _log(msg):
                box.markdown(
                    f"<div style='color:#8b949e;font-size:.84em;"
                    f"font-family:monospace;padding:4px 0'>⏳ {msg}</div>",
                    unsafe_allow_html=True)
            return _log

        r = analyze_stock(
            ticker,
            int(start_year),
            int(end_year),
            end_month=int(end_month),
            dart_inst=dart_instance,
            corp_codes=corp_codes_df,
            log_fn=make_logger(),
        )
        if r:
            results.append(r)
        prog.progress((idx + 1) / total)

    log_area.empty()
    prog.empty()

    if not results:
        st.error("분석 가능한 결과가 없습니다. 종목코드 또는 DART 데이터를 확인하세요.")
        st.stop()

    st.session_state["results"]    = results
    st.session_state["start_year"] = start_year
    st.session_state["end_year"]   = end_year
    st.session_state["end_month"]  = end_month
    st.success(f"✅ 분석 완료! {len(results)}개 종목")

# ── 결과 표시 ─────────────────────────────────────────────────
results: list = st.session_state.get("results", [])

if results:
    passed_n = sum(1 for r in results if r["passed"])
    failed_n = sum(1 for r in results if not r["passed"] and r["dollar_test_ratio"] is not None)
    na_n     = sum(1 for r in results if r["dollar_test_ratio"] is None)
    denom    = len(results) - na_n
    rate     = passed_n / denom * 100 if denom > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("분석 종목",  len(results))
    c2.metric("✅ 통과",    passed_n)
    c3.metric("❌ 미통과",  failed_n)
    c4.metric("통과율",    f"{rate:.0f}%")

    st.markdown("---")
    st.markdown("### 📊 종목별 결과")

    rows = []
    for r in sorted(results,
                    key=lambda x: (x["dollar_test_ratio"] or -999), reverse=True):
        ratio = r["dollar_test_ratio"]
        rows.append({
            "종목명":      r["name"],
            "코드":        r["ticker"],
            "분석기간":    f"{r['start_year']}~{r['end_label']} ({r['years_analyzed']}y)",
            "시작가(원)":  f"{r['start_price']:,.0f}",
            "현재가(원)":  f"{r['end_price']:,.0f}",
            "수익률":      f"{r['price_appreciation_pct']:+.1f}%" if r['price_appreciation_pct'] else "N/A",
            "CAGR":       f"{r['price_cagr']:+.1f}%" if r['price_cagr'] else "N/A",
            "누적유보EPS": f"{r['total_retained_eps']:,.0f}",
            "$1 비율":    f"{ratio:.2f}x" if ratio is not None else "N/A",
            "결과":       ("✅ 통과" if r["passed"] else
                          ("❌ 미통과" if ratio is not None else "⚠️ 계산불가")),
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 🔍 종목 상세")

    name_map = {f"[{r['ticker']}] {r['name']}": r for r in results}
    selected = st.selectbox("종목 선택", list(name_map.keys()))
    r        = name_map[selected]

    col_l, col_r = st.columns([1, 2])

    with col_l:
        st.markdown(f"**{r['name']}** `{r['ticker']}`")
        st.markdown(f"분석기간: **{r['start_year']} ~ {r['end_label']}** ({r['years_analyzed']}년)")
        if r.get("latest_eps_label"):
            st.caption(f"📋 마지막 연도 EPS 기준: {r['latest_eps_label']}")
        st.markdown(f"재무 확보: **{r['data_years_count']}**개연도")
        st.markdown("---")

        ratio = r["dollar_test_ratio"]
        if ratio is None:
            st.warning("⚠️ 계산 불가 (누적 유보이익 ≤ 0)")
        elif ratio >= 1.0:
            st.success(f"✅ **통과** — $1 비율 **{ratio:.2f}x**")
        else:
            st.error(f"❌ **미통과** — $1 비율 **{ratio:.2f}x**")

        st.markdown("---")
        for k, v in {
            "시작가":       f"{r['start_price']:,.0f}원",
            "현재가":       f"{r['end_price']:,.0f}원",
            "주가 상승분":  f"{r['price_appreciation']:+,.0f}원 ({r['price_appreciation_pct']:+.1f}%)" if r['price_appreciation_pct'] else "N/A",
            "CAGR":        f"{r['price_cagr']:+.1f}%" if r['price_cagr'] else "N/A",
            "누적 유보EPS": f"{r['total_retained_eps']:,.0f}원",
        }.items():
            st.markdown(f"**{k}**: {v}")

    with col_r:
        cd    = r["chart_data"]
        years = [c["year"]         for c in cd]
        cum_r = [c["cum_retained"] for c in cd]
        p_chg = [c["price_change"] for c in cd]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=years, y=cum_r, name="누적 유보이익/주(원)",
            line=dict(color="#f0b429", width=2.5),
            fill="tozeroy", fillcolor="rgba(240,180,41,0.07)",
            mode="lines+markers", marker=dict(size=5),
        ))
        fig.add_trace(go.Scatter(
            x=years, y=p_chg, name="주가 상승분(원)",
            line=dict(color="#58a6ff", width=2.5),
            fill="tozeroy", fillcolor="rgba(88,166,255,0.07)",
            mode="lines+markers", marker=dict(size=5),
        ))
        fig.add_hline(y=0, line_dash="dot", line_color="#484f58")
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#161b22", plot_bgcolor="#0d1117",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(l=0, r=0, t=30, b=0),
            yaxis_tickformat=",",
            hovermode="x unified",
            height=320,
        )
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("📋 연도별 상세 데이터"):
        ytbl = []
        for c in cd:
            ytbl.append({
                "연도":        c["year"],
                "주가(원)":    f"{c['close']:,.0f}"        if c["close"]               else "-",
                "EPS(원)":     f"{c['EPS']:,.0f}"          if c["EPS"] is not None     else "-",
                "DPS(원)":     f"{c['DPS']:,.0f}"          if c["DPS"] is not None     else "-",
                "유보EPS(원)": f"{c['retained_eps']:+,.0f}" if c["retained_eps"] is not None else "-",
                "누적유보EPS": f"{c['cum_retained']:,.0f}",
            })
        st.dataframe(pd.DataFrame(ytbl), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 💾 결과 저장")
    html_out = build_html(results, datetime.now().strftime("%Y년 %m월 %d일"))
    sy = st.session_state.get("start_year", start_year)
    ey = st.session_state.get("end_year",   end_year)
    em = st.session_state.get("end_month",  end_month)
    end_file_str = f"{ey}_{em:02d}" if em != 12 else str(ey)
    st.download_button(
        label="📥 HTML 대시보드 다운로드",
        data=html_out.encode("utf-8"),
        file_name=f"warren_buffett_{sy}_{end_file_str}.html",
        mime="text/html",
        use_container_width=True,
        type="secondary",
    )

else:
    st.info("👈 왼쪽에서 DART API 키·종목코드·기간을 입력한 뒤 **분석 시작**을 눌러주세요.")
    st.markdown("""<div style="color:#8b949e;font-size:.9em;line-height:2;margin-top:12px">
<b>종목코드 예시</b><br>
005930 — 삼성전자 &nbsp;|&nbsp; 000660 — SK하이닉스 &nbsp;|&nbsp;
035420 — NAVER &nbsp;|&nbsp; 051910 — LG화학 &nbsp;|&nbsp; 068270 — 셀트리온
</div>""", unsafe_allow_html=True)
