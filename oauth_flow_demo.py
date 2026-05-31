"""
OAuth 2.0 完整交互流程 Demo（无需浏览器，纯命令行）
====================================================
在一个脚本中模拟 Provider + Client 的完整 OAuth 授权码流程，
帮助你理解每一步到底发生了什么。

运行方式：
  pip install requests
  python oauth_flow_demo.py

流程概览：
  用户 → Client → Provider(授权) → Client → Provider(换Token) → Client → Provider(访问资源)
"""

import secrets
import time
import requests

# ============================================================
# 模拟 Provider 的存储（与 oauth_provider.py 一致）
# ============================================================

registered_clients = {
    "demo_client_id": {
        "client_id": "demo_client_id",
        "client_secret": "demo_client_secret",
        "redirect_uris": ["http://localhost:5002/callback"],
    }
}

auth_codes = {}
tokens = {}
users = {"alice": {"username": "alice", "password": "password123", "email": "alice@example.com"}}


# ============================================================
# 模拟 Provider 的三个端点
# ============================================================


def provider_authorize(client_id, redirect_uri, scope, state, username, password, action="approve"):
    """模拟 Provider 的授权端点"""
    client = registered_clients.get(client_id)
    if not client:
        return {"error": "invalid_client"}

    if redirect_uri not in client["redirect_uris"]:
        return {"error": "invalid_redirect_uri"}

    user = users.get(username)
    if not user or user["password"] != password:
        return {"error": "access_denied", "message": "用户名或密码错误"}

    if action == "deny":
        return {"error": "access_denied", "redirect": f"{redirect_uri}?error=access_denied&state={state}"}

    code = secrets.token_urlsafe(16)
    auth_codes[code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "username": username,
        "created_at": time.time(),
        "expires_in": 600,
    }
    return {"code": code, "state": state}


def provider_token(grant_type, code, redirect_uri, client_id, client_secret):
    """模拟 Provider 的令牌端点"""
    if grant_type != "authorization_code":
        return {"error": "unsupported_grant_type"}

    client = registered_clients.get(client_id)
    if not client or client["client_secret"] != client_secret:
        return {"error": "invalid_client"}

    code_data = auth_codes.get(code)
    if not code_data:
        return {"error": "invalid_grant", "message": "授权码无效"}

    if time.time() - code_data["created_at"] > code_data["expires_in"]:
        return {"error": "invalid_grant", "message": "授权码过期"}

    if code_data["client_id"] != client_id:
        return {"error": "invalid_grant", "message": "client_id 不匹配"}

    if code_data["redirect_uri"] != redirect_uri:
        return {"error": "invalid_grant", "message": "redirect_uri 不一致"}

    auth_codes.pop(code)

    access_token = secrets.token_urlsafe(24)
    tokens[access_token] = {
        "client_id": client_id,
        "username": code_data["username"],
        "scope": code_data["scope"],
        "created_at": time.time(),
        "expires_in": 3600,
    }

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": code_data["scope"],
    }


def provider_userinfo(access_token):
    """模拟 Provider 的受保护资源端点"""
    token_data = tokens.get(access_token)
    if not token_data:
        return {"error": "invalid_token"}

    if time.time() - token_data["created_at"] > token_data["expires_in"]:
        return {"error": "token_expired"}

    user = users[token_data["username"]]
    result = {"username": user["username"]}
    if "email" in token_data["scope"]:
        result["email"] = user["email"]
    return result


# ============================================================
# 模拟 Client 的完整流程
# ============================================================


def run_oauth_flow():
    CLIENT_ID = "demo_client_id"
    CLIENT_SECRET = "demo_client_secret"
    REDIRECT_URI = "http://localhost:5002/callback"

    print("=" * 70)
    print("  OAuth 2.0 授权码模式 - 完整交互流程演示")
    print("=" * 70)

    # ──────────────────────────────────────────────────────────
    # 步骤 1: Client 构造授权 URL
    # ──────────────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("📌 步骤 1: Client 构造授权 URL，准备重定向用户")
    print("─" * 70)

    state = secrets.token_urlsafe(16)
    scope = "read email"

    auth_url = (
        f"http://localhost:5001/oauth/authorize"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={scope.replace(' ', '+')}"
        f"&state={state}"
    )

    print(f"""
Client 构造的授权 URL:
  GET {auth_url}

参数说明:
  response_type=code   → 授权码模式，固定值
  client_id={CLIENT_ID}  → 在 Provider 注册时获得的标识
  redirect_uri={REDIRECT_URI}  → 授权后回调地址
  scope={scope}  → 请求的权限范围
  state={state}  → 防 CSRF 的随机字符串

💡 这就是 "使用 XX 登录" 按钮点击后发生的第一件事！
   用户的浏览器被重定向到这个 URL。
""")

    # ──────────────────────────────────────────────────────────
    # 步骤 2: 用户在 Provider 上登录并授权
    # ──────────────────────────────────────────────────────────
    print("─" * 70)
    print("📌 步骤 2: 用户在授权服务器上登录并同意授权")
    print("─" * 70)

    result = provider_authorize(
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        scope=scope,
        state=state,
        username="alice",
        password="password123",
    )

    if "error" in result:
        print(f"❌ 授权失败: {result}")
        return

    code = result["code"]
    returned_state = result["state"]

    print(f"""
用户在 Provider 页面上:
  1. 输入用户名: alice
  2. 输入密码: password123
  3. 看到: "Demo 第三方应用 请求访问你的账号 (read, email)"
  4. 点击 "同意授权"

Provider 处理:
  ✅ 验证 client_id 有效
  ✅ 验证 redirect_uri 在白名单中
  ✅ 验证用户身份
  ✅ 生成授权码: {code}
  ✅ 重定向回 Client: {REDIRECT_URI}?code={code}&state={returned_state}

💡 授权码的特点:
  - 一次性使用（用完即废）
  - 短期有效（通常 10 分钟）
  - 绑定了 client_id 和 redirect_uri
""")

    # ──────────────────────────────────────────────────────────
    # 步骤 3: Client 验证 state，用授权码换 Token
    # ──────────────────────────────────────────────────────────
    print("─" * 70)
    print("📌 步骤 3: Client 用授权码 + client_secret 换取 Token")
    print("─" * 70)

    # 验证 state
    if returned_state != state:
        print("❌ state 不匹配！可能是 CSRF 攻击！")
        return

    print(f"✅ state 验证通过: {state}")

    token_result = provider_token(
        grant_type="authorization_code",
        code=code,
        redirect_uri=REDIRECT_URI,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )

    if "error" in token_result:
        print(f"❌ 换取 Token 失败: {token_result}")
        return

    access_token = token_result["access_token"]

    print(f"""
Client 后端向 Provider 发起请求（不经过浏览器！）:
  POST http://localhost:5001/oauth/token
  Content-Type: application/x-www-form-urlencoded

  grant_type=authorization_code
  code={code}
  redirect_uri={REDIRECT_URI}
  client_id={CLIENT_ID}
  client_secret={CLIENT_SECRET}    ← 🔑 只有后端知道！

Provider 返回:
  {{
    "access_token": "{access_token[:20]}...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "scope": "{token_result['scope']}"
  }}

💡 为什么需要 client_secret？
  授权码可能被截获（通过浏览器 URL），但只有真正的 Client 后端
  才知道 client_secret，所以即使授权码泄露，攻击者也无法换取 Token。
""")

    # ──────────────────────────────────────────────────────────
    # 步骤 4: Client 使用 Token 请求受保护资源
    # ──────────────────────────────────────────────────────────
    print("─" * 70)
    print("📌 步骤 4: Client 使用 Token 请求受保护资源")
    print("─" * 70)

    user_info = provider_userinfo(access_token)

    if "error" in user_info:
        print(f"❌ 请求资源失败: {user_info}")
        return

    print(f"""
Client 向 Provider 发起请求:
  GET http://localhost:5001/api/userinfo
  Authorization: Bearer {access_token[:20]}...

  ╔══════════════════════════════════════════════════════════╗
  ║  这就是 Client 请求时 "多了什么" 的答案：                ║
  ║                                                          ║
  ║  普通请求:                                               ║
  ║    GET /api/userinfo                                     ║
  ║    （无 Authorization 头 → 401 Unauthorized）            ║
  ║                                                          ║
  ║  OAuth 请求:                                             ║
  ║    GET /api/userinfo                                     ║
  ║    Authorization: Bearer <access_token>                  ║
  ║    （有合法 Token → 200 OK + 用户数据）                  ║
  ╚══════════════════════════════════════════════════════════╝

Provider 返回用户信息:
  {user_info}
""")

    # ──────────────────────────────────────────────────────────
    # 对比总结
    # ──────────────────────────────────────────────────────────
    print("=" * 70)
    print("  📊 总结：服务支持 OAuth 需要做什么 & Client 请求多了什么")
    print("=" * 70)

    print("""
┌─────────────────────────────────────────────────────────────────┐
│ 服务要支持 OAuth（成为 Provider），需要实现：                      │
├─────────────────────────────────────────────────────────────────┤
│ 1. 客户端注册管理                                                │
│    - 发放 client_id + client_secret                             │
│    - 管理 redirect_uri 白名单                                    │
│                                                                 │
│ 2. 授权端点 GET /oauth/authorize                                │
│    - 验证 client_id、redirect_uri                               │
│    - 展示登录+授权确认页面                                        │
│    - 生成授权码，重定向回 Client                                  │
│                                                                 │
│ 3. 令牌端点 POST /oauth/token                                   │
│    - 验证 client_id + client_secret                             │
│    - 验证授权码（有效性、归属、一次性）                             │
│    - 签发 access_token（+ refresh_token）                        │
│                                                                 │
│ 4. 资源端点 GET /api/xxx                                        │
│    - 验证 Bearer Token                                          │
│    - 根据 scope 限制返回数据                                     │
│                                                                 │
│ 5. 安全措施                                                      │
│    - state 防 CSRF、redirect_uri 严格匹配                        │
│    - 授权码一次性+短期有效、Token HTTPS 传输                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Client 请求时多了什么：                                          │
├─────────────────────────────────────────────────────────────────┤
│ 1. 获取阶段（比普通登录多了整个 OAuth 流程）：                     │
│    - 构造授权 URL，重定向用户到 Provider                          │
│    - 接收回调中的授权码                                           │
│    - 后端用授权码 + client_secret 换取 Token                     │
│                                                                 │
│ 2. 使用阶段（每个 API 请求多了）：                                │
│    - 请求头: Authorization: Bearer <access_token>               │
│    - 不需要用户名/密码                                            │
│    - Token 有过期时间和 scope 限制                               │
│    - Token 可被撤销                                              │
└─────────────────────────────────────────────────────────────────┘
""")


if __name__ == "__main__":
    run_oauth_flow()
