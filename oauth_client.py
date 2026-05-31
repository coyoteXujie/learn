"""
OAuth 2.0 客户端 (Client) Demo
===============================
演示作为第三方应用，如何接入 OAuth 认证。

运行方式：
  pip install flask requests
  python oauth_client.py

客户端会启动在 http://localhost:5002

本 demo 展示了 Client 在 OAuth 流程中需要做的所有事情：
  1. 构造授权 URL，将用户重定向到授权服务器
  2. 接收授权码回调
  3. 用授权码 + client_secret 换取 Token
  4. 使用 Token 请求受保护资源
"""

import secrets
import requests
from flask import Flask, request, redirect, jsonify, render_template_string

app = Flask(__name__)

# ============================================================
# Client 配置（在授权服务器注册时获得）
# ============================================================

CLIENT_ID = "demo_client_id"
CLIENT_SECRET = "demo_client_secret"
REDIRECT_URI = "http://localhost:5002/callback"
AUTHORIZE_URL = "http://localhost:5001/oauth/authorize"
TOKEN_URL = "http://localhost:5001/oauth/token"
USERINFO_URL = "http://localhost:5001/api/userinfo"

# 存储 state（防 CSRF）和获取到的 token
state_store = {}
token_store = {}


# ============================================================
# 页面 1: 首页 - 展示 "使用 XX 登录" 按钮
# ============================================================

HOME_PAGE = """
<!DOCTYPE html>
<html>
<head><title>OAuth Client - 第三方应用</title></head>
<body style="font-family:sans-serif;max-width:600px;margin:50px auto;">
  <h2>🖥️ Demo 第三方应用</h2>
  <p>这是一个需要用户授权的第三方应用。</p>
  <p>当前状态: <strong>{{ status }}</strong></p>

  {% if token %}
  <h3>✅ 已获取 Token</h3>
  <p>Access Token: <code>{{ token[:30] }}...</code></p>
  <p><a href="/profile">查看用户信息</a></p>
  <p><a href="/logout">退出登录</a></p>
  {% else %}
  <h3>🔐 请先登录</h3>
  <p>点击下方按钮，将通过 OAuth 授权服务器登录：</p>
  <a href="/login" style="display:inline-block;padding:10px 20px;background:#0366d6;color:white;
     text-decoration:none;border-radius:5px;font-size:16px;">
    🔑 使用 OAuth Provider 登录
  </a>
  {% endif %}

  <hr>
  <h3>📋 Client 请求时多了什么？</h3>
  <pre style="background:#f5f5f5;padding:15px;border-radius:5px;">
普通请求（无认证）:
  GET /api/userinfo
  → 401 Unauthorized

OAuth 请求（带 Token）:
  GET /api/userinfo
  Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
  → 200 OK + 用户数据

区别:
  1. 请求头多了 Authorization: Bearer &lt;access_token&gt;
  2. 不需要携带用户名/密码
  3. Token 有过期时间和权限范围限制
  4. Token 可以被撤销
  </pre>
</body>
</html>
"""


@app.route("/")
def home():
    token = token_store.get("access_token")
    status = "已登录" if token else "未登录"
    return render_template_string(HOME_PAGE, token=token, status=status)


# ============================================================
# 步骤 1: 构造授权 URL，重定向用户到授权服务器
# ============================================================


@app.route("/login")
def login():
    """
    Client 需要做的第一步：构造授权 URL 并重定向用户。

    必须包含的参数:
      - response_type=code  (授权码模式)
      - client_id           (在 Provider 注册时获得)
      - redirect_uri        (授权后回调地址)
      - scope               (请求的权限范围)
      - state               (随机字符串，防 CSRF 攻击)

    这就是 "使用 XX 登录" 按钮背后做的事情！
    """
    # 生成随机 state，防止 CSRF 攻击
    state = secrets.token_urlsafe(32)
    state_store[state] = True

    # 构造授权 URL
    auth_url = (
        f"{AUTHORIZE_URL}"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=read+email"
        f"&state={state}"
    )

    print(f"\n[Client] 步骤1: 重定向用户到授权服务器")
    print(f"[Client] 授权 URL: {auth_url}")
    print(f"[Client] 生成的 state: {state}")

    # 将用户重定向到授权服务器
    return redirect(auth_url)


# ============================================================
# 步骤 2: 接收授权码回调
# 步骤 3: 用授权码换取 Token
# ============================================================


@app.route("/callback")
def callback():
    """
    授权服务器将用户重定向回这里，URL 中携带授权码。

    Client 需要做的:
      1. 验证 state 是否与之前发送的一致（防 CSRF）
      2. 用授权码 + client_secret 向授权服务器换取 Token
         （这一步在 Client 后端完成，不经过浏览器）
    """
    # 检查是否有错误（用户拒绝授权等）
    error = request.args.get("error")
    if error:
        return jsonify({"error": error, "message": "用户拒绝授权或授权失败"}), 400

    code = request.args.get("code")
    state = request.args.get("state")

    print(f"\n[Client] 步骤2: 收到授权码回调")
    print(f"[Client] 授权码: {code}")
    print(f"[Client] 返回的 state: {state}")

    # 验证 state（防 CSRF 攻击）
    if state not in state_store:
        return jsonify({"error": "invalid_state", "message": "state 不匹配，可能是 CSRF 攻击"}), 400
    state_store.pop(state)

    # 用授权码换取 Token（后端对后端请求，不经过浏览器）
    print(f"\n[Client] 步骤3: 用授权码换取 Token")
    token_response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,  # 只有后端知道，保证安全
        },
    )

    if token_response.status_code != 200:
        return jsonify({"error": "token_exchange_failed", "detail": token_response.json()}), 400

    token_data = token_response.json()
    print(f"[Client] 获取到 Token: {token_data['access_token'][:30]}...")
    print(f"[Client] Token 类型: {token_data['token_type']}")
    print(f"[Client] 过期时间: {token_data['expires_in']}秒")
    print(f"[Client] 权限范围: {token_data['scope']}")

    # 存储 Token（生产环境应存入数据库或 session）
    token_store["access_token"] = token_data["access_token"]
    token_store["refresh_token"] = token_data.get("refresh_token")
    token_store["token_type"] = token_data["token_type"]
    token_store["expires_in"] = token_data["expires_in"]
    token_store["scope"] = token_data["scope"]

    return redirect("/")


# ============================================================
# 步骤 4: 使用 Token 请求受保护资源
# ============================================================


@app.route("/profile")
def profile():
    """
    使用 access_token 请求用户信息。

    这就是 Client 请求时 "多了什么" 的实际体现：
      请求头多了 Authorization: Bearer <access_token>
    """
    access_token = token_store.get("access_token")
    if not access_token:
        return redirect("/")

    print(f"\n[Client] 步骤4: 使用 Token 请求受保护资源")
    print(f"[Client] 请求头: Authorization: Bearer {access_token[:20]}...")

    # 关键：请求头携带 Bearer Token
    response = requests.get(
        USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )

    if response.status_code != 200:
        return jsonify({"error": "resource_request_failed", "detail": response.json()})

    user_info = response.json()
    print(f"[Client] 获取到用户信息: {user_info}")

    return render_template_string(
        """
    <!DOCTYPE html>
    <html>
    <head><title>用户信息</title></head>
    <body style="font-family:sans-serif;max-width:600px;margin:50px auto;">
      <h2>👤 用户信息</h2>
      <p>通过 OAuth Token 获取成功！</p>
      <table style="border-collapse:collapse;width:100%;">
        <tr><td style="border:1px solid #ddd;padding:8px;"><strong>用户名</strong></td>
            <td style="border:1px solid #ddd;padding:8px;">{{ username }}</td></tr>
        <tr><td style="border:1px solid #ddd;padding:8px;"><strong>邮箱</strong></td>
            <td style="border:1px solid #ddd;padding:8px;">{{ email }}</td></tr>
      </table>

      <h3>🔍 请求详情</h3>
      <pre style="background:#f5f5f5;padding:15px;border-radius:5px;">
请求:
  GET {{ userinfo_url }}
  Authorization: Bearer {{ token_preview }}...

响应:
  {{ response_json }}
      </pre>

      <p><a href="/">返回首页</a></p>
    </body>
    </html>
    """,
        username=user_info.get("username", ""),
        email=user_info.get("email", "（未授权）"),
        userinfo_url=USERINFO_URL,
        token_preview=access_token[:20],
        response_json=response.json(),
    )


@app.route("/logout")
def logout():
    token_store.clear()
    return redirect("/")


# ============================================================
# 启动服务
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("OAuth 2.0 Client (第三方应用) 启动")
    print("地址: http://localhost:5002")
    print("=" * 60)
    print("\nClient 配置:")
    print(f"  client_id:     {CLIENT_ID}")
    print(f"  client_secret: {CLIENT_SECRET}")
    print(f"  redirect_uri:  {REDIRECT_URI}")
    print(f"  authorize_url: {AUTHORIZE_URL}")
    print(f"  token_url:     {TOKEN_URL}")
    print()
    app.run(port=5002, debug=True)
