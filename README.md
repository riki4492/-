# Split+ 2.0（割り勘アプリ）

以前の `warikan_app.py` を刷新したStreamlit版です。固定負担、5段階の傾斜配分、比率カスタマイズ、ぴったり精算、切り上げ集金、LINE共有、明細CSV出力を搭載しています。

## 起動

```sh
pip install -r requirements.txt
streamlit run warikan_app.py
```

## Streamlit Community Cloud で更新

既存のGitHubリポジトリのルートに、`warikan_app.py`、`warikan_core.py`、`requirements.txt`、`.streamlit/config.toml` をアップロードしてください（既存の `warikan_app.py` を上書き）。エントリーポイントは以前と同じ `warikan_app.py` です。デプロイ後にリロードしてください。

## 端数の仕様

- ぴったり精算：最大剰余法で1円単位まで合計を一致させます。選択した単位（10円/100円）で割り切れない不足分だけ、1人の負担額を細かく調整するため、同ランク内でも少額の差が生じる場合があります。
- 切り上げ集金：全員の理論負担額を指定単位で上に丸めます。集金が多くなる場合は幹事のおつりとして表示されます。

## 履歴

履歴はStreamlitのセッション内だけです。アプリ再起動やセッション切断後も残す必要がある場合は、CSVとして保存してください。共有サーバー上に個人データを永続保存する設計にはしていません。
