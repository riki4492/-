import math
import pandas as pd
import streamlit as st

# ---------------------------------------
# 基本設定
# ---------------------------------------
st.set_page_config(page_title="割り勘アプリ", page_icon="💴", layout="centered")

st.title("💴 割り勘アプリ")

# サイドバー：モード選択
st.sidebar.header("モード選択")

rank_weights_master = {
    "がっつり払う（先輩・上司）": 1.5,
    "ちょい多め（中堅）": 1.2,
    "ふつう": 1.0,
    "ちょい少なめ（後輩）": 0.8,
    "ほぼおごり（新入社員など）": 0.5,
}
rank_list = list(rank_weights_master.keys())


def round_up(x, unit):
    return math.ceil(x / unit) * unit


# モード名（ここだけで定義・管理）
pattern_labels = {
    "p1": "① 数人だけ固定額、残りを位ごとに割る",
    "p2": "② 合計金額を全員で割る（人ごとに位を決定）",
    "p3": "③ 合計金額を全員で割る（位ごとの人数で算出）",
}

pattern_key = st.sidebar.radio(
    "計算パターン",
    options=list(pattern_labels.keys()),
    format_func=lambda k: pattern_labels[k],
    index=0,
)

st.sidebar.markdown("---")
round_option = st.sidebar.selectbox(
    "端数処理（位割り部分）",
    ("そのまま（四捨五入）", "10円単位で切り上げ", "100円単位で切り上げ"),
)

# ---------------------------------------
# 共通：合計金額
# ---------------------------------------
# ★ ここだけがモード名表示。太帯(subheader)はもう使わない
st.caption(pattern_labels[pattern_key])

total = st.number_input("合計金額（円）", min_value=0, step=100, value=0)

st.write("---")

# 先に変数だけ用意
names_p1, is_fixed_p1, fixed_amounts_p1, ranks_p1 = [], [], [], []
names_p2, ranks_p2 = [], []
rank_counts_p3 = {rank: 0 for rank in rank_list}

# ---------------------------------------
# パターン①：数人固定額 + 残り位割り
# ---------------------------------------
if pattern_key == "p1":
    num_people_p1 = st.number_input("人数", min_value=1, step=1, value=4, key="p1_num")
    int_num_p1 = int(num_people_p1)

    st.caption("※ 固定額 or 位割りを人ごとに選ぶ")

    for i in range(int_num_p1):
        default_name = f"人{i+1}"
        with st.container():
            cols = st.columns([2, 1.3, 2])
            with cols[0]:
                name = st.text_input(
                    f"名前（{i+1}人目）",
                    value=default_name,
                    key=f"p1_name_{i}",
                )
                if name.strip() == "":
                    name = default_name
            with cols[1]:
                fixed_flag = st.checkbox("固定額", value=False, key=f"p1_fixed_flag_{i}")
            if fixed_flag:
                with cols[2]:
                    fixed_value = st.number_input(
                        "固定額（円）",
                        min_value=0,
                        step=100,
                        value=0,
                        key=f"p1_fixed_{i}",
                    )
                rank = None
            else:
                fixed_value = 0
                with cols[2]:
                    rank = st.selectbox(
                        "位（ランク）",
                        rank_list,
                        index=2,
                        key=f"p1_rank_{i}",
                    )

        names_p1.append(name)
        is_fixed_p1.append(fixed_flag)
        fixed_amounts_p1.append(fixed_value)
        ranks_p1.append(rank)

# ---------------------------------------
# パターン②：全員位割り（人ごと）
# ---------------------------------------
elif pattern_key == "p2":
    num_people_p2 = st.number_input("人数", min_value=1, step=1, value=4, key="p2_num")
    int_num_p2 = int(num_people_p2)

    st.caption("※ 全員が位（ランク）に応じた金額を支払う")

    for i in range(int_num_p2):
        default_name = f"人{i+1}"
        cols = st.columns([2, 2])
        with cols[0]:
            name = st.text_input(
                f"名前（{i+1}人目）",
                value=default_name,
                key=f"p2_name_{i}",
            )
            if name.strip() == "":
                name = default_name
        with cols[1]:
            rank = st.selectbox(
                f"位（{default_name}）",
                rank_list,
                index=2,
                key=f"p2_rank_{i}",
            )
        names_p2.append(name)
        ranks_p2.append(rank)

# ---------------------------------------
# パターン③：位ごとの人数
# ---------------------------------------
else:  # p3
    st.caption("※ 名前は不要。どの位の人が何人いるかだけ入力")

    for rank in rank_list:
        rank_counts_p3[rank] = st.number_input(
            f"{rank} の人数",
            min_value=0,
            step=1,
            value=0,
            key=f"p3_count_{rank}",
        )

# ---------------------------------------
# 計算ボタン
# ---------------------------------------
st.write("---")

if st.button("計算する"):
    if total <= 0:
        st.error("合計金額を入力してください。")
    else:
        # =========================
        # ① 数人固定額 + 残り位割り
        # =========================
        if pattern_key == "p1":
            int_num = len(names_p1)
            if int_num == 0:
                st.error("人数が0人です。")
            else:
                fixed_total = sum(fixed_amounts_p1)
                remain = total - fixed_total

                if remain < 0:
                    st.error(
                        f"固定額の合計 {fixed_total:,} 円 > 合計金額 {total:,} 円 "
                        "固定額の設定を見直してください。"
                    )
                else:
                    weights, idx_list = [], []
                    for i in range(int_num):
                        if not is_fixed_p1[i]:
                            rank = ranks_p1[i]
                            if rank is None:
                                continue
                            w = rank_weights_master[rank]
                            weights.append(w)
                            idx_list.append(i)

                    weight_sum = sum(weights)
                    pay_list = [0] * int_num

                    # 固定額ぶん
                    for i in range(int_num):
                        if is_fixed_p1[i]:
                            pay_list[i] = int(fixed_amounts_p1[i])

                    if remain > 0 and weight_sum == 0:
                        st.error("残り金額がありますが、位割り対象者がいません。ランク設定を確認してください。")
                    else:
                        if remain > 0 and weight_sum > 0:
                            base_per_weight = remain / weight_sum
                            for w, idx in zip(weights, idx_list):
                                raw = base_per_weight * w
                                if round_option == "そのまま（四捨五入）":
                                    pay = int(round(raw))
                                elif round_option == "10円単位で切り上げ":
                                    pay = int(round_up(raw, 10))
                                else:
                                    pay = int(round_up(raw, 100))
                                pay_list[idx] = pay

                        total_collected = sum(pay_list)
                        diff = total_collected - total

                        rows = []
                        for i in range(int_num):
                            mode = "固定額" if is_fixed_p1[i] else "位割り"
                            rank_label = ranks_p1[i] if ranks_p1[i] is not None else "-"
                            rows.append(
                                {
                                    "名前": names_p1[i],
                                    "方式": mode,
                                    "位（ランク）": rank_label,
                                    "支払額（円）": pay_list[i],
                                }
                            )
                        df = pd.DataFrame(rows)
                        st.dataframe(df, hide_index=True)

                        st.write(f"**合計金額**：{total:,} 円")
                        st.write(f"・固定額合計：{fixed_total:,} 円")
                        st.write(f"・位割り対象：{remain:,} 円")
                        st.write(f"**集金合計**：{total_collected:,} 円（{int_num}人）")

                        if diff > 0:
                            st.warning(f"集金が **{diff:,} 円多い** → 幹事のおつりなどに")
                        elif diff < 0:
                            st.error(f"集金が **{-diff:,} 円足りない** → 固定額や人数を調整")
                        else:
                            st.success("ピッタリ割り勘！🎉")

        # =========================
        # ② 全員 位割り（人ごと）
        # =========================
        elif pattern_key == "p2":
            int_num = len(names_p2)
            if int_num == 0:
                st.error("人数が0人です。")
            else:
                weights = [rank_weights_master[r] for r in ranks_p2]
                weight_sum = sum(weights)
                if weight_sum == 0:
                    st.error("全員の重みが0です。ランク設定を確認してください。")
                else:
                    base_per_weight = total / weight_sum
                    pay_list = []
                    for w in weights:
                        raw = base_per_weight * w
                        if round_option == "そのまま（四捨五入）":
                            pay = int(round(raw))
                        elif round_option == "10円単位で切り上げ":
                            pay = int(round_up(raw, 10))
                        else:
                            pay = int(round_up(raw, 100))
                        pay_list.append(pay)

                    total_collected = sum(pay_list)
                    diff = total_collected - total

                    rows = []
                    for i in range(int_num):
                        rows.append(
                            {
                                "名前": names_p2[i],
                                "位（ランク）": ranks_p2[i],
                                "支払額（円）": pay_list[i],
                            }
                        )
                    df = pd.DataFrame(rows)
                    st.dataframe(df, hide_index=True)

                    st.write(f"**合計金額**：{total:,} 円")
                    st.write(f"**集金合計**：{total_collected:,} 円（{int_num}人）")

                    if diff > 0:
                        st.warning(f"集金が **{diff:,} 円多い** → 幹事のおつりなどに")
                    elif diff < 0:
                        st.error(f"集金が **{-diff:,} 円足りない** → ランクや端数処理を調整")
                    else:
                        st.success("ピッタリ割り勘！🎉")

        # =========================
        # ③ 位ごとの人数だけ
        # =========================
        else:  # p3
            total_people = sum(rank_counts_p3.values())
            if total_people == 0:
                st.error("人数が0人です。ランクごとの人数を入力してください。")
            else:
                weight_sum = 0
                for rank in rank_list:
                    weight_sum += rank_counts_p3[rank] * rank_weights_master[rank]

                if weight_sum == 0:
                    st.error("全員の重みが0です。人数やランク設定を確認してください。")
                else:
                    base_per_weight = total / weight_sum
                    rows = []
                    total_collected = 0

                    for rank in rank_list:
                        count = int(rank_counts_p3[rank])
                        if count <= 0:
                            continue
                        w = rank_weights_master[rank]
                        raw = base_per_weight * w
                        if round_option == "そのまま（四捨五入）":
                            per_person = int(round(raw))
                        elif round_option == "10円単位で切り上げ":
                            per_person = int(round_up(raw, 10))
                        else:
                            per_person = int(round_up(raw, 100))

                        subtotal = per_person * count
                        total_collected += subtotal

                        rows.append(
                            {
                                "位（ランク）": rank,
                                "人数": count,
                                "1人あたり（円）": per_person,
                                "合計（円）": subtotal,
                            }
                        )

                    df = pd.DataFrame(rows)
                    diff = total_collected - total

                    st.dataframe(df, hide_index=True)

                    st.write(f"**合計金額**：{total:,} 円")
                    st.write(f"**集金合計**：{total_collected:,} 円（{total_people}人）")

                    if diff > 0:
                        st.warning(f"集金が **{diff:,} 円多い** → 幹事のおつりなどに")
                    elif diff < 0:
                        st.error(f"集金が **{-diff:,} 円足りない** → 人数や端数処理を調整")
                    else:
                        st.success("ピッタリ割り勘！🎉")
