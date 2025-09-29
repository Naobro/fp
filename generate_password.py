import random
import string
import datetime
from supabase import create_client
import streamlit as st

# 1. Supabase クライアント作成
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_SERVICE_KEY"]  # 書き込みは service_role を使う
supabase = create_client(url, key)

# 2. パスワード生成関数
def generate_password(length=8):
    chars = string.ascii_letters + string.digits  # 英字＋数字
    return ''.join(random.choice(chars) for _ in range(length))

# 3. 今月のキーを作る（例: 2025-10）
today = datetime.date.today()
month_key = today.strftime("%Y-%m")

# 4. 新しいパスワードを作る
new_pw = generate_password(8)

# 5. Supabase に保存（同じ月なら上書きされる）
supabase.table("monthly_passwords").upsert({
    "month": month_key,
    "password": new_pw
}).execute()

print(f"{month_key} の新しいパスワードを保存しました: {new_pw}")