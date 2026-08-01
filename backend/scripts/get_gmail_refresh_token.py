"""取得 Gmail API 的 refresh token（一次性工具）。

用途：線上環境不能走 SMTP（Render 免費方案封鎖對外 587，實測連線逾時），
改用 Gmail API 走 HTTPS 寄信，需要一組 refresh token。

前置作業（Google Cloud Console）：
  1. 建立專案 → 啟用 Gmail API
  2. OAuth 同意畫面：目標對象選「外部」，並把寄件用的 Gmail 加進「測試使用者」
  3. 憑證 → 建立 OAuth 用戶端 ID → 應用程式類型選「**桌面應用程式**」
  4. 把取得的 Client ID / Client Secret 填進 backend/.env：
       GMAIL_CLIENT_ID=...
       GMAIL_CLIENT_SECRET=...

執行：
  cd backend && venv/Scripts/python.exe scripts/get_gmail_refresh_token.py

會開啟瀏覽器要你登入並授權（畫面上出現「Google 尚未驗證這個應用程式」是正常的，
點「進階 → 繼續前往」）。完成後終端機會印出 refresh token。

**重要**：OAuth 同意畫面停在「測試中」狀態時，Google 發的 refresh token
只有 7 天有效期。拿到 token 後務必回同意畫面點「發布應用程式」，
否則線上寄信會在一週後突然失效。
"""

import http.server
import socket
import socketserver
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

import httpx  # noqa: E402

from app.core.config import settings  # noqa: E402

PORT = 8765
REDIRECT_URI = f"http://localhost:{PORT}"
SCOPE = "https://www.googleapis.com/auth/gmail.send"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"

received: dict[str, str] = {}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        received.update({k: v[0] for k, v in params.items()})
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        ok = "code" in received
        msg = "授權完成，可以關閉這個視窗回終端機看結果。" if ok else \
              f"授權失敗：{received.get('error', '未知錯誤')}"
        self.wfile.write(f"<html><body style='font-family:sans-serif'><h3>{msg}</h3>"
                         "</body></html>".encode())

    def log_message(self, *args):  # 不要把 HTTP log 灌進終端機
        pass


def main() -> int:
    if not (settings.gmail_client_id and settings.gmail_client_secret):
        print("[中止] backend/.env 缺少 GMAIL_CLIENT_ID 或 GMAIL_CLIENT_SECRET")
        print("       請先在 Google Cloud Console 建立「桌面應用程式」類型的 OAuth 用戶端。")
        return 1

    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", PORT)) == 0:
            print(f"[中止] port {PORT} 已被占用，請先關掉占用該 port 的程式。")
            return 1

    params = {
        "client_id": settings.gmail_client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        # access_type=offline 才會發 refresh token；
        # prompt=consent 確保即使先前授權過也重新發一份。
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    server = socketserver.TCPServer(("127.0.0.1", PORT), Handler)
    server.timeout = 1

    print("請在開啟的瀏覽器中完成授權（若沒自動開啟，手動貼上下面的網址）：")
    print(f"\n{url}\n")
    threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()

    print(f"等待授權回呼（{REDIRECT_URI}）…")
    for _ in range(300):  # 最多等 5 分鐘
        server.handle_request()
        if received:
            break
    server.server_close()

    if "code" not in received:
        print(f"[失敗] 沒有取得授權碼：{received or '使用者未完成授權'}")
        return 1

    resp = httpx.post(TOKEN_URL, data={
        "code": received["code"],
        "client_id": settings.gmail_client_id,
        "client_secret": settings.gmail_client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }, timeout=60)

    if resp.status_code != 200:
        print(f"[失敗] 換取 token 失敗：{resp.status_code}\n{resp.text[:500]}")
        return 1

    data = resp.json()
    refresh = data.get("refresh_token")
    if not refresh:
        print("[失敗] 回應沒有 refresh_token。多半是這個帳號先前已授權過，"
              "請到 https://myaccount.google.com/permissions 移除本應用後重跑。")
        print(data)
        return 1

    print("\n=== 取得成功 ===")
    print(f"scope: {data.get('scope')}")
    print("\n把這一行加進 backend/.env，以及 Render 的環境變數：\n")
    print(f"GMAIL_REFRESH_TOKEN={refresh}")
    print("\n別忘了回 OAuth 同意畫面點「發布應用程式」，"
          "否則測試中狀態的 refresh token 只有 7 天有效。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
