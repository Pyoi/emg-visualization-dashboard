#　とりあえずここに置きます。（2020版から少し変えた）

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="EMG Dashboard", layout="wide")
st.title("筋電データ可視化ダッシュボード")
st.caption("CSVを読み込み、平滑化した筋電波形と活動別の要約を表示します。")

uploaded = st.sidebar.file_uploader("筋電CSVをアップロード", type=["csv"])
if not uploaded:
    st.info("左のサイドバーからCSVをアップロードしてください。")
    st.stop()

# CSVの読み込み（文字コードを、ここで対応）
df = None
for enc in ("utf-8", "utf-8-sig", "cp932"):
    try:
        df = pd.read_csv(uploaded, encoding=enc)
        break
    except Exception:
        pass
if df is None:
    st.error("CSVを読めませんでした")
    st.stop()

cols = list(df.columns)

ts_col = st.sidebar.selectbox("日時列", cols)
val_col = st.sidebar.selectbox("筋電列（数値）", cols)
cat_col = st.sidebar.selectbox("活動ラベル（任意）", ["(なし)"] + cols)

df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")
df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
df = df.dropna(subset=[ts_col, val_col]).sort_values(ts_col)

# 平滑化
window = st.sidebar.slider("平滑化（移動平均の窓）", 1, 60, 7)
df["emg_smooth"] = df[val_col].rolling(window=window, min_periods=1, center=True).mean()

# ピーク検出
thr = st.sidebar.number_input("ピーク閾値", value=float(df["emg_smooth"].quantile(0.85)))
above = df["emg_smooth"] > thr
peak_count = int(((above) & (~above.shift(1).fillna(False))).sum())

# サマリーを表示
duration_sec = (df[ts_col].max() - df[ts_col].min()).total_seconds()
c1, c2, c3, c4 = st.columns(4)
c1.metric("平均（平滑）", f"{df['emg_smooth'].mean():.2f} mV")
c2.metric("最大（平滑）", f"{df['emg_smooth'].max():.2f} mV")
c3.metric("測定時間", f"{duration_sec:.0f} 秒")
c4.metric("ピーク回数", f"{peak_count}")

# 色をここで設定
color_map = {
    "rest": "#6B7280",
    "grip": "#EF4444",
    "release": "#3B82F6",
}
default_color = "#10B981"

st.subheader("時系列（平滑化＋色分け）")
fig = go.Figure()

# 生波形？
fig.add_trace(go.Scatter(
    x=df[ts_col],
    y=df[val_col],
    mode="lines",
    name="raw",
    line=dict(color="rgba(120,120,120,0.3)", width=1)
))

# 平滑波形
if cat_col != "(なし)":
    for act in df[cat_col].unique():
        sub = df[df[cat_col] == act]
        fig.add_trace(go.Scatter(
            x=sub[ts_col],
            y=sub["emg_smooth"],
            mode="lines",
            name=f"smooth ({act})",
            line=dict(color=color_map.get(str(act), default_color), width=3)
        ))
else:
    fig.add_trace(go.Scatter(
        x=df[ts_col],
        y=df["emg_smooth"],
        mode="lines",
        name="smooth",
        line=dict(color="#111827", width=3)
    ))

fig.update_layout(xaxis_title="Time", yaxis_title="mV")
st.plotly_chart(fig, use_container_width=True)

# 活動別集計
if cat_col != "(なし)":
    st.subheader("活動別平均値")
    g = df.groupby(cat_col)["emg_smooth"].mean().reset_index()
    fig2 = px.bar(
        g,
        x=cat_col,
        y="emg_smooth",
        color=cat_col,
        color_discrete_map=color_map
    )

    st.plotly_chart(fig2, use_container_width=True)
