import math
import pandas as pd
import streamlit as st

# ---------------------------------------
# 基本設定
# ---------------------------------------
st.set_page_config(page_title="割り勘アプリ", page_icon="💴", layout="centered")

st.title("💴 割り勘アプリ（固定 + 位ごと人数割り）")

st.caption("合計金額から「固定で払う人」を引いて、残りを位（ランク）ごとの人数で割ります。")

# ---------------------------------------
# 位（ランク）と重み
# ---------------------------------------
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


# ---------------------------------------
# 共通入力：合計金額 & 端数処理（同じ画面にまとめる）
# ---------------------------------------
total = st.number_input("合計金額（円）", min_value=0, step=100, value=0)

round_option = st.selectbox(
    "今回の位割り部分の端数処理",
    ("そのまま（四捨五入）", "10円単位で切り上げ", "100円単位で切り上げ"),
    help="※ 固定額はそのまま、位で割る部分だけこのルールで端数処理します。",
)

st.write("---")

# ---------------------------------------
# 固定で払う人の設定（縦にカード表示）
# ---------------------------------------
st.subheader("🧍 固定で払う人")

num_fixed = st.number_input("固定で払う人の人数", min_value=0, step=1, value=1)
int_num_fixed = int(num_fixed)

fixed_names = []
fixed_amounts = []

if int_num_fixed > 0:
    st.caption("※ 例：部長 10000円、社長 20000円 など")
    for i in range(int_num_fixed):
        default_name = f"固定{i+1}"
        with st.container():
            st.markdown(f"#### 固定の人 {i+1}人目")
            name = st.text_input(
                "名前",
                value=default_name,
                key=f"fixed_name_{i}",
            )
            if name.strip() == "":
                name = default_name

            amount = st.number_input(
                "固定額（円）",
                min_value=0,
                step=100,
                value=0,
                key=f"fixed_amount_{i}",
            )

        st.markdown("---")

        fixed_names.append(name)
        fixed_amounts.append(amount)

else:
    st.caption("固定で払う人がいない場合は 0 のままでOKです。")

# ---------------------------------------
# 位ごとの人数設定
# ---------------------------------------
st.subheader("🧑‍🤝‍🧑 位ごとに割る人の人数")

st.caption("※ 固定額の人を除いた、残りの人たちを登録してください。")

rank_counts = {rank: 0 for rank in rank_list}

for rank in rank_list:
    rank_counts[rank] = st.number_input(
        f"{rank} の人数",
        min_value=0,
        step=1,
        value=0,
        key=f"rank_count_{rank}",
    )

st.write("---")

# ---------------------------------------
# 計算
# ---------------------------------------
if st.button("計算する"):
    if total <= 0:
        st.error("合計金額を入力してください。")
    else:
        # 固定分の計算
        fixed_total = sum(fixed_amounts)
        remain = total - fixed_total

        # 固定の人のテーブル
        fixed_rows = []
        for name, amount in zip(fixed_names, fixed_amounts):
            fixed_rows.append(
                {
                    "区分": "固定",
                    "名前 / 位": name,
                    "人数": 1,
                    "1人あたり（円）": int(amount),
                    "合計（円）": int(amount),
                }
            )

        # 位割り対象の人数・重み
        total_people_rank = sum(rank_counts.values())

        # remain < 0 は明らかにおかしいのでエラー
        if remain < 0:
            st.error(
                f"固定額の合計 {fixed_total:,} 円 が合計金額 {total:,} 円 を超えています。\n"
                "固定額を見直してください。"
            )
        else:
            rank_rows = []
            rank_total = 0

            if remain == 0:
                # 残りが0 → 位割り部分は全員0円
                if total_people_rank > 0:
                    st.info("合計金額が固定の人だけでピッタリなので、位で割る人の負担は 0 円になります。")
                    for rank in rank_list:
                        count = int(rank_counts[rank])
                        if count <= 0:
                            continue
                        rank_rows.append(
                            {
                                "区分": "位割り",
                                "名前 / 位": rank,
                                "人数": count,
                                "1人あたり（円）": 0,
                                "合計（円）": 0,
                            }
                        )
                    rank_total = 0
                else:
                    # 固定だけでピッタリ
                    rank_total = 0
            else:
                # 残り > 0 のとき位割り
                if total_people_rank == 0:
                    st.error(
                        f"固定額の合計は {fixed_total:,} 円、残り {remain:,} 円 があります。\n"
                        "位で割る人の人数を入力してください。"
                    )
                    rank_rows = []
                    rank_total = 0
                else:
                    # 重み合計
                    weight_sum = 0
                    for rank in rank_list:
                        weight_sum += rank_counts[rank] * rank_weights_master[rank]

                    if weight_sum == 0:
                        st.error("位割りの重みがすべて0です。人数やランク設定を確認してください。")
                        rank_rows = []
                        rank_total = 0
                    else:
                        base_per_weight = remain / weight_sum

                        for rank in rank_list:
                            count = int(rank_counts[rank])
                            if count <= 0:
                                continue
                            w = rank_weights_master[rank]
                            raw_per_person = base_per_weight * w

                            if round_option == "そのまま（四捨五入）":
                                per_person = int(round(raw_per_person))
                            elif round_option == "10円単位で切り上げ":
                                per_person = int(round_up(raw_per_person, 10))
                            else:
                                per_person = int(round_up(raw_per_person, 100))

                            subtotal = per_person * count
                            rank_total += subtotal

                            rank_rows.append(
                                {
                                    "区分": "位割り",
                                    "名前 / 位": rank,
                                    "人数": count,
                                    "1人あたり（円）": per_person,
                                    "合計（円）": subtotal,
                                }
                            )

            # 結果まとめ
            total_collected = fixed_total + rank_total
            diff = total_collected - total

            st.subheader("📊 結果一覧")

            all_rows = fixed_rows + rank_rows
            if all_rows:
                df = pd.DataFrame(all_rows)
                st.dataframe(df, hide_index=True)
            else:
                st.info("まだ固定額も位割りも設定されていません。")

            st.write("---")
            st.write(f"**合計金額**：{total:,} 円")
            st.write(f"・固定で払う人の合計：{fixed_total:,} 円")
            st.write(f"・位で割る人の合計：{rank_total:,} 円")
            st.write(f"**集金合計（固定 + 位）**：{total_collected:,} 円")

            if diff > 0:
                st.warning(f"集金合計が **{diff:,} 円多い** です（幹事のおつりなどに）。")
            elif diff < 0:
                st.error(f"集金合計が **{-diff:,} 円足りません。** 固定額や人数・端数処理を見直してください。")
            else:
                st.success("合計金額とピッタリ一致しました！🎉")

            # LINE用テキスト
            st.write("---")
            st.subheader("📋 LINEに貼れるテキスト")

            lines = [f"合計：{total:,}円"]

            if fixed_rows:
                lines.append("＜固定で払う人＞")
                for r in fixed_rows:
                    lines.append(f"{r['名前 / 位']}：{r['合計（円）']:,}円（固定）")

            if rank_rows:
                lines.append("＜位で割る人＞")
                for r in rank_rows:
                    lines.append(
                        f"{r['名前 / 位']}：{r['人数']}人 → 1人 {r['1人あたり（円）']:,}円（合計 {r['合計（円）']:,}円）"
                    )

            if diff > 0:
                lines.append(f"※端数 {diff:,}円 は幹事のおつり")
            elif diff < 0:
                lines.append(f"※{-diff:,}円 足りないのでどこかで調整してください")

            st.code("\n".join(lines), language="text")
