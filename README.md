# 🌐 金融市場 Dashboard

即時金融市場數據 Dashboard，包含 S&P 500、IWM、VIX、10Y Yield、DXY、USD/HKD、Oil、Gold 及 CNN Fear & Greed 指標。

## 功能
- 📈 8 個資產圖表，每個含 10MA / 20MA
- 🧭 CNN Fear & Greed 儀表盤
- 🔄 一鍵 Refresh 重新抓取最新數據
- 📋 最新數據快照含日變動

## 本機運行

```bash
pip install -r requirements.txt
streamlit run app.py
```

瀏覽器會自動打開 http://localhost:8501

## 部署到 Streamlit Cloud（免費）

1. 將此 repo push 上 GitHub
2. 去 https://share.streamlit.io
3. 選你的 repo，main file 選 `app.py`
4. 點 Deploy — 完成！

## 文件結構

```
├── app.py               # 主程序
├── requirements.txt     # 套件依賴
└── README.md
```
