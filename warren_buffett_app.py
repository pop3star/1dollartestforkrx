def _extract_eps_from_fs(fs: pd.DataFrame) -> dict | None:
    """재무제표 DataFrame에서 EPS/DPS/순이익 추출 (누적금액 우선, 중단영업 합산, 희석 제외 로직 포함)"""
    
    nm_col  = next((c for c in fs.columns if "account_nm" in c.lower()), None)
    amt_col = next((c for c in fs.columns if "thstrm_amount" in c.lower()), None)
    
    # NEW: 3분기/반기 보고서의 누적 EPS를 가져오기 위한 당기누적금액 컬럼 탐색
    add_amt_col = next((c for c in fs.columns if "thstrm_add_amount" in c.lower()), None)
    
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
                
                # [안전장치 1] '희석'이 포함된 계정명 철저히 배제
                rows = rows[~rows[nm_col].astype(str).str.contains("희석")]
                if rows.empty:
                    continue

                row = rows.iloc[0]
                val = None
                
                # [안전장치 2] 1순위: 당기누적금액 (thstrm_add_amount) 확인
                # 분기/반기 보고서에서는 3개월 치가 아닌 '누적 금액'을 가져와야 함
                if add_amt_col and pd.notna(row.get(add_amt_col)):
                    v = str(row[add_amt_col]).strip()
                    if v not in ("", "-", "―"):
                        val = v
                        
                # [안전장치 3] 2순위: 당기누적금액이 없으면 당기금액 (thstrm_amount) 사용
                # 연간 사업보고서는 보통 누적금액 컬럼 없이 당기금액만 존재함
                if val is None and pd.notna(row.get(amt_col)):
                    v = str(row[amt_col]).strip()
                    if v not in ("", "-", "―"):
                        val = v

                if val is not None:
                    return float(val.replace(",", "").replace(" ", ""))
            except Exception:
                pass
        return None

    # EPS 탐색 1순위: 전체 '기본주당이익'
    eps = find([
        "기본주당이익", "기본주당순이익", "보통주기본주당이익", 
        "보통주 1주당 순이익", "주당순이익", "주당이익", "주당손익"
    ])
    
    # EPS 탐색 2순위: 계속영업과 중단영업이 분리된 경우 합산
    if eps is None:
        eps_cont = find(["계속영업기본주당이익", "계속영업주당이익", "계속영업주당순이익", "계속영업 보통주 1주당순이익", "계속영업"])
        eps_disc = find(["중단영업기본주당이익", "중단영업주당이익", "중단영업주당순이익", "중단영업 보통주 1주당순이익", "중단영업"])
        
        if eps_cont is not None:
            eps = eps_cont + (eps_disc if eps_disc is not None else 0.0)

    # 배당금 및 당기순이익 탐색 (순이익도 누적금액을 자동으로 가져옴)
    dps = find(["주당배당금", "주당현금배당금", "현금배당금(주당)", "1주당 배당금"])
    ni  = find(["당기순이익", "당기순손익", "연결당기순이익", "연결당기순손익", "반기순이익", "분기순이익"])
    
    if eps is not None:
        return {"EPS": eps, "DPS": dps or 0.0, "NI": ni}
    return None
