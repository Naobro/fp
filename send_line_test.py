import requests
import streamlit as st

LINE_CHANNEL_ACCESS_TOKEN = st.secrets["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_USER_ID = st.secrets["LINE_USER_ID"]

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
}

message = {
    "to": LINE_USER_ID,
    "messages": [
        {"type": "text", "text": "✅ テスト送信です！このメッセージが届いていたら成功です。"}
    ]
}

res = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=message)
print(res.status_code, res.text)