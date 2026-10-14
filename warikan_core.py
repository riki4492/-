"""割り勘計算エンジン。Streamlit非依存でテスト可能。"""
from __future__ import annotations

from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from typing import Any

DEFAULT_RANKS: tuple[tuple[str, str], ...] = (
    ("がっつり払う", "1.5"),
    ("ちょい多め", "1.2"),
    ("ふつう", "1.0"),
    ("ちょい少なめ", "0.8"),
    ("ほぼおごり", "0.5"),
)


def _distribute_exact(remain: int, weights: list[Decimal], unit: int) -> list[int]:
    """最大剰余法で配分し、1円単位まで集金総額を厳密に一致させる。"""
    if not weights:
        return []
    if remain == 0:
        return [0] * len(weights)

    wsum = sum(weights)
    chunks, spare_yen = divmod(remain, unit)
    quota = [Decimal(chunks) * w / wsum for w in weights]
    chunk_allocations = [int(v.to_integral_value(rounding=ROUND_FLOOR)) for v in quota]
    shortage = chunks - sum(chunk_allocations)
    # 分配単位の余りを、切り捨てによる損失が大きい順に渡す。
    order = sorted(
        range(len(weights)),
        key=lambda i: (quota[i] - chunk_allocations[i], weights[i], -i),
        reverse=True,
    )
    for i in order[:shortage]:
        chunk_allocations[i] += 1

    amounts = [n * unit for n in chunk_allocations]
    if spare_yen:
        # 10/100円単位で割り切れない場合、差の大きい1人に数円を割り当てる。
        ideal = [Decimal(remain) * w / wsum for w in weights]
        pick = max(
            range(len(weights)),
            key=lambda i: (ideal[i] - amounts[i], weights[i], -i),
        )
        amounts[pick] += spare_yen
    return amounts


def _distribute_roundup(remain: int, weights: list[Decimal], unit: int) -> list[int]:
    if remain == 0:
        return [0] * len(weights)
    wsum = sum(weights)
    return [
        int((Decimal(remain) * w / wsum / unit).to_integral_value(rounding=ROUND_CEILING)) * unit
        for w in weights
    ]


def calculate(
    total: int,
    fixed: list[tuple[str, int]],
    ranks: list[tuple[str, int, str | float | Decimal]],
    *,
    unit: int = 100,
    mode: str = "exact",
) -> dict[str, Any]:
    """一人ごとの負担を計算。mode='exact'は合計一致、'roundup'は切り上げ。"""
    if not isinstance(total, int) or total < 0:
        raise ValueError("合計金額は0円以上の整数にしてください。")
    if unit not in (1, 10, 100):
        raise ValueError("端数単位は1円・10円・100円から選んでください。")
    if mode not in ("exact", "roundup"):
        raise ValueError("精算方式が不正です。")
    if any(not isinstance(amount, int) or amount < 0 for _, amount in fixed):
        raise ValueError("固定額は0円以上の整数にしてください。")

    fixed_total = sum(amount for _, amount in fixed)
    if fixed_total > total:
        raise ValueError(f"固定額の合計 {fixed_total:,}円 が、お会計 {total:,}円 を超えています。")

    weights: list[Decimal] = []
    rank_defs: list[tuple[str, int, Decimal]] = []
    for label, count, weight_raw in ranks:
        if not isinstance(count, int) or count < 0:
            raise ValueError("人数は0以上の整数にしてください。")
        weight = Decimal(str(weight_raw))
        if not weight.is_finite() or weight <= 0:
            raise ValueError("負担比率は0より大きい値にしてください。")
        rank_defs.append((label, count, weight))
        weights.extend([weight] * count)

    remain = total - fixed_total
    if remain > 0 and not weights:
        raise ValueError(f"固定額を除いた残り {remain:,}円 を分ける人がいません。ランク別人数を入力してください。")
    if not fixed and not weights:
        raise ValueError("固定額で払う人か、ランク別人数を入力してください。")

    payments = (
        _distribute_exact(remain, weights, unit)
        if mode == "exact" else _distribute_roundup(remain, weights, unit)
    )

    rows: list[dict[str, Any]] = []
    for index, (label, amount) in enumerate(fixed):
        rows.append({"category": "固定", "label": label or f"固定{index+1}", "payments": [amount]})
    offset = 0
    for label, count, _ in rank_defs:
        if count:
            rows.append({"category": "ランク", "label": label, "payments": payments[offset : offset + count]})
        offset += count

    collected = fixed_total + sum(payments)
    return {
        "total": total,
        "people": len(fixed) + len(payments),
        "fixed_total": fixed_total,
        "rank_total": sum(payments),
        "collected": collected,
        "difference": collected - total,
        "rows": rows,
        "mode": mode,
        "unit": unit,
    }
