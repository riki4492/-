"""割り勘アプリ 2.0 — スマホから使える傾斜配分精算ツール。"""
from __future__ import annotations

import csv
import html
import io
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from warikan_core import DEFAULT_RANKS, calculate

st.set_page_config(
    page_title="割り勘アプリ | Split+",
    page_icon="💸",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
    .stApp { background: #F5F7FB; color: #1E293B; }
    .block-container { max-width: 740px; padding-top: 1.25rem; padding-bottom: 4rem; }
    #MainMenu, footer { visibility: hidden; }
    div[data-testid="stVerticalBlock"] { gap: 0.75rem; }
    .hero {
      background: linear-gradient(115deg, #535DEB, #8778F6);
      color: white; padding: 28px 24px; border-radius: 24px; margin-bottom: 18px;
      box-shadow: 0 12px 30px rgba(83,93,235,.15);
    }
    .hero .eyebrow { text-transform: uppercase; letter-spacing: .16em; font-size: 11px; opacity: .85; font-weight: 700; }
    .hero h1 { font-size: clamp(28px, 6vw, 39px); line-height: 1.2; margin: 8px 0; color: white !important; font-weight: 800; }
    .hero p { font-size: 14px; margin: 0; color: #F3F1FF; }
    .section-title { margin: 18px 0 4px; font-weight: 800; font-size: 19px; color: #263149; }
    .section-sub { margin: 0 0 8px; color: #68758B; font-size: 13px; }
    .result-card {
      padding: 16px 18px; margin: 9px 0; background: white;
      border: 1px solid #E6EAF2; border-radius: 16px;
      box-shadow: 0 2px 8px rgba(29,39,69,.025);
    }
    .result-title { font-weight: 800; font-size: 15px; color: #1E293B; }
    .result-detail { margin-top: 7px; font-size: 14px; color: #65758C; }
    .result-money { font-weight: 800; font-size: 19px; color: #4B57D4; }
    .pill { display:inline-block; font-size: 11px; background:#EAEAFE; color:#535DEB; padding: 3px 9px; border-radius: 999px; margin-left: 8px; }
    .pay-total { font-size: 13px; color: #6A7588; margin-top: 5px; }
    .small-note { color:#69788C; font-size: 12px; }
    div[data-testid="stMetric"] {
      background:white; padding: 12px; border-radius:14px; border: 1px solid #E6EAF2;
    }
    div[data-testid="stMetricValue"] { font-size: clamp(18px, 3.5vw, 27px); }
    div[data-testid="stNumberInput"], div[data-testid="stTextInput"] { margin-bottom: .35rem; }
    div[data-testid="stAlert"] { border-radius: 12px; }
    .stButton > button[kind="primary"] { background-color: #585EF0; border-color: #585EF0; }
    @media(max-width: 550px) {
      .block-container { padding: .8rem .95rem 3rem; }
      .hero { padding: 23px 20px; border-radius: 20px; }
      .result-card { padding: 14px 15px; }
      div[data-testid="stMetricValue"] { font-size: 19px; }
    }
</style>
    """,
    unsafe_allow_html=True,
)


def money(amount: int) -> str:
    return f"{amount:,}円"


def name_safe(value: str) -> str:
    return html.escape(value, quote=True)


def example_inputs() -> None:
    st.session_state["bill_total"] = 25000
    st.session_state["bill_title"] = "飲み会"
    st.session_state["fixed_count"] = 1
    st.session_state["fixed_name_0"] = "部長"
    st.session_state["fixed_amount_0"] = 5000
    for i, count in enumerate((1, 1, 3, 1, 0)):
        st.session_state[f"rank_count_{i}"] = count


def reset_inputs() -> None:
    for key in list(st.session_state.keys()):
        if key.startswith(("fixed_name_", "fixed_amount_", "rank_count_", "rank_weight_", "rank_label_")):
            del st.session_state[key]
    st.session_state["bill_total"] = 0
    st.session_state["bill_title"] = ""
    st.session_state["fixed_count"] = 0
    st.session_state["round_mode"] = "ぴったり精算"
    st.session_state["round_unit"] = "100円"


def summary_amounts(payments: list[int]) -> str:
    counts = Counter(payments)
    return " ／ ".join(
        f"{money(amount)} × {count}人"
        for amount, count in sorted(counts.items(), reverse=True)
    )


def make_line_text(title: str, result: dict) -> str:
    lines = [f"🧾 {title or '割り勘精算'}", f"お会計：{money(result['total'])}（{result['people']}人）", ""]
    fixed = [row for row in result["rows"] if row["category"] == "固定"]
    ranks = [row for row in result["rows"] if row["category"] == "ランク"]
    if fixed:
        lines.append("【固定額】")
        lines.extend(f"{row['label']}：{money(row['payments'][0])}" for row in fixed)
        lines.append("")
    if ranks:
        lines.append("【ランク別】")
        for row in ranks:
            lines.append(f"{row['label']}（{len(row['payments'])}人）：{summary_amounts(row['payments'])}")
        lines.append("")
    lines.append(f"集金合計：{money(result['collected'])}")
    if result["difference"] > 0:
        lines.append(f"おつり：{money(result['difference'])}（幹事管理）")
    elif result["difference"] < 0:
        lines.append(f"不足：{money(-result['difference'])}")
    else:
        lines.append("✅ お会計とぴったり一致")
    return "\n".join(lines)


def make_csv(result: dict) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["区分", "名前・ランク", "番号", "支払額（円）"])
    for row in result["rows"]:
        for i, amount in enumerate(row["payments"], 1):
            writer.writerow([row["category"], row["label"], i, amount])
    writer.writerow(["合計", "", "", result["collected"]])
    writer.writerow(["会計との差額", "", "", result["difference"]])
    return stream.getvalue().encode("utf-8-sig")


st.markdown(
    '<div class="hero"><div class="eyebrow">SPLIT + / SMART BILL SPLITTER</div>'
    '<h1>💸 割り勘を、もっとスマートに。</h1>'
    '<p>固定額も、先輩・後輩の傾斜配分も。入力するだけで自動精算。</p></div>',
    unsafe_allow_html=True,
)

with st.expander("使い方を見る", expanded=False):
    st.write("① お会計を入力 → ② 固定額で払う人とランク別人数を設定 → ③ 自動計算の結果をLINEへコピー。")
    st.caption("「ぴったり精算」は人数ごとに端数を調整するため、同じランクでも支払額が少し異なる場合があります。")

st.markdown('<div class="section-title">01 / お会計</div>', unsafe_allow_html=True)
st.text_input("イベント名（省略可）", placeholder="例：10月の飲み会", key="bill_title")
st.number_input("合計金額（円）", min_value=0, max_value=10_000_000_000, step=1000, key="bill_total")

st.markdown('<div class="section-title">02 / 固定額で払う人</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">先に多めに払う人、金額を決めて払う人を登録。</div>', unsafe_allow_html=True)
st.number_input("固定額の人の人数", min_value=0, max_value=30, step=1, key="fixed_count")
fixed_people: list[tuple[str, int]] = []
for i in range(int(st.session_state.fixed_count)):
    with st.container(border=True):
        st.markdown(f"**固定メンバー {i+1}**")
        n = st.text_input("名前", key=f"fixed_name_{i}", placeholder=f"例：部長{i+1}")
        a = st.number_input("負担する金額（円）", min_value=0, max_value=10_000_000_000, step=100, key=f"fixed_amount_{i}")
        fixed_people.append((n.strip() or f"固定{i+1}", int(a)))

st.markdown('<div class="section-title">03 / 残りの人のランク・人数</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">固定額で払う人はここに含めないでください。</div>', unsafe_allow_html=True)
rank_definitions = []
for i, (default_name, default_weight) in enumerate(DEFAULT_RANKS):
    if f"rank_label_{i}" not in st.session_state:
        st.session_state[f"rank_label_{i}"] = default_name
    if f"rank_weight_{i}" not in st.session_state:
        st.session_state[f"rank_weight_{i}"] = float(default_weight)
    name = st.session_state[f"rank_label_{i}"].strip() or default_name
    count = st.number_input(
        f"{name}（×{st.session_state[f'rank_weight_{i}']:g}）",
        min_value=0, max_value=300, step=1, key=f"rank_count_{i}",
    )
    rank_definitions.append((name, int(count), st.session_state[f"rank_weight_{i}"]))

with st.expander("⚙️ ランク名・負担比率をカスタマイズ"):
    st.caption("負担比率が大きいほど、同じ人数なら支払額が大きくなります。変更は自動反映されます。")
    for i, _ in enumerate(DEFAULT_RANKS):
        st.text_input(f"ランク {i+1} の名前", key=f"rank_label_{i}")
        st.number_input(
            f"ランク {i+1} の負担比率", min_value=0.1, max_value=20.0,
            step=0.1, format="%.1f", key=f"rank_weight_{i}",
        )

st.markdown('<div class="section-title">04 / 端数処理</div>', unsafe_allow_html=True)
st.selectbox("精算方式", ("ぴったり精算", "切り上げ集金（おつりあり）"), key="round_mode")
st.selectbox("端数の単位", ("1円", "10円", "100円"), index=2, key="round_unit")
if st.session_state.round_mode == "ぴったり精算":
    st.caption("差額は必ず0円。端数の都合で同じランクの人でも最大100円程度の違いが出ることがあります。")
else:
    st.caption("全員の負担を指定単位で切り上げます。多く集まった分は幹事がおつりとして管理してください。")

col_ex, col_reset = st.columns(2)
with col_ex:
    st.button("✨ サンプル入力", use_container_width=True, on_click=example_inputs)
with col_reset:
    st.button("↻ 全入力リセット", use_container_width=True, on_click=reset_inputs)

result = None
error = None
if st.session_state.bill_total > 0:
    try:
        result = calculate(
            int(st.session_state.bill_total), fixed_people, rank_definitions,
            unit=int(st.session_state.round_unit.replace("円", "")),
            mode="exact" if st.session_state.round_mode == "ぴったり精算" else "roundup",
        )
    except ValueError as exc:
        error = str(exc)

st.markdown('<div class="section-title">05 / 精算結果</div>', unsafe_allow_html=True)
if error:
    st.error(error)
elif not result:
    st.info("合計金額と人数を入力すると、ここに自動で精算結果が表示されます。")
else:
    m1, m2 = st.columns(2)
    with m1:
        st.metric("必要金額", money(result["total"]))
    with m2:
        st.metric("対象人数", f"{result['people']}人")
    st.metric("集金予定", money(result["collected"]))
    if result["difference"] == 0:
        st.success("✅ お会計と集金額がぴったり一致しています！")
    elif result["difference"] > 0:
        st.warning(f"集金超過 {money(result['difference'])}。幹事がおつりとして返す・管理する金額です。")
    else:
        st.error(f"集金不足 {money(-result['difference'])} です。")

    for row in result["rows"]:
        amounts = row["payments"]
        cat = "固定" if row["category"] == "固定" else "傾斜"
        st.markdown(
            f'<div class="result-card"><span class="result-title">{name_safe(row["label"])}</span>'
            f'<span class="pill">{cat} / {len(amounts)}人</span>'
            f'<div class="result-detail"><span class="result-money">{name_safe(summary_amounts(amounts))}</span></div>'
            f'<div class="pay-total">小計：{money(sum(amounts))}</div></div>',
            unsafe_allow_html=True,
        )
    st.caption(f"固定額の合計 {money(result['fixed_total'])} ／ ランク別の合計 {money(result['rank_total'])}")

    with st.expander("一人ずつの金額を確認する"):
        for row in result["rows"]:
            st.write(f"**{row['label']}**")
            for i, amount in enumerate(row["payments"], 1):
                st.write(f"{i}人目：{money(amount)}")

    st.markdown('<div class="section-title">📋 LINEに貼り付け</div>', unsafe_allow_html=True)
    st.caption("右上のコピーアイコンを押してLINEに貼り付けてください。")
    line_text = make_line_text(st.session_state.bill_title.strip(), result)
    st.code(line_text, language=None)
    st.download_button(
        "⬇︎ 明細CSVを保存", make_csv(result),
        file_name="warikan_result.csv", mime="text/csv", use_container_width=True,
    )
    if st.button("🕘 この精算を履歴に保存", use_container_width=True, type="primary"):
        if "history" not in st.session_state:
            st.session_state.history = []
        st.session_state.history.insert(0, {
            "saved_at": datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%m/%d %H:%M"),
            "title": st.session_state.bill_title.strip() or "割り勘精算",
            "text": line_text,
        })
        st.session_state.history = st.session_state.history[:10]
        st.toast("今回の精算を保存しました", icon="✅")

if st.session_state.get("history"):
    st.markdown('<div class="section-title">🕘 このセッションの履歴</div>', unsafe_allow_html=True)
    for record in st.session_state.history:
        with st.expander(f"{record['saved_at']}　{record['title']}"):
            st.code(record["text"], language=None)
    st.caption("履歴はこのブラウザー接続中のみ保持されます。消えないように残したい場合は、明細CSVを保存してください。")

st.markdown('<p class="small-note">Split+ 2.0 ・合計チェック付き傾斜割り勘ツール</p>', unsafe_allow_html=True)
