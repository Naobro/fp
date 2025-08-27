# utils/rates.py
from __future__ import annotations
from datetime import datetime
from typing import Dict

# ====== 毎月の基準金利（%）← ここだけ更新すれば全ページに反映 ======
BASE_RATES: Dict[str, Dict[str, float]] = {
    # キーは "YYYY-MM"（ゼロ埋め）。値は %（例: 0.610）
    "2025-08": {"SBI新生銀行": 0.590, "三菱UFJ銀行": 0.595, "PayPay銀行": 0.599, "じぶん銀行": 0.780, "住信SBI銀行": 0.739},
    "2025-09": {"SBI新生銀行": 0.600, "三菱UFJ銀行": 0.605, "PayPay銀行": 0.610, "じぶん銀行": 0.770, "住信SBI銀行": 0.740},
    # 以降は毎月追加してください
    # "2025-10": {...},
}

BANK_ORDER = ["SBI新生銀行", "三菱UFJ銀行", "PayPay銀行", "じぶん銀行", "住信SBI銀行"]

def month_key(dt: datetime | None = None) -> str:
    dt = dt or datetime.now()
    return dt.strftime("%Y-%m")

def month_label(dt: datetime | None = None) -> str:
    dt = dt or datetime.now()
    return dt.strftime("%Y年%m月")

def get_base_rates_for_current_month(dt: datetime | None = None) -> Dict[str, float]:
    """今月の基準金利（%）を返す。無ければ最後のエントリを返す。"""
    mk = month_key(dt)
    if mk in BASE_RATES:
        return BASE_RATES[mk].copy()
    # 定義が無ければ最後の月を使う
    last_key = sorted(BASE_RATES.keys())[-1]
    return BASE_RATES[last_key].copy()
