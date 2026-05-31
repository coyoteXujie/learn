"""
OAuth 2.0 服务端 (Provider) Demo
=================================
演示一个服务要支持 OAuth 认证，需要实现哪些端点和逻辑。

运行方式：
  pip install flask
  python oauth_provider.py

服务端会启动在 http://localhost:5001

本 demo 包含：
  1. 客户端注册管理
  2. 授权端点 (Authorization Endpoint)
  3. 令牌端点 (Token Endpoint)
  4. 受保护资源端点 (Resource Endpoint)
"""

import secrets
import time
from flask import Flask, request, redirect, jsonify, render_template_string

app = Flask(__name__)

# ============================================================
# 模拟存储（生产环境请使用数据库）
# ============================================================

registered_clients = {
    "demo_client_id": {
        "client_id": "demo_client_id",
        "client_secret": "demo_client_secret",
        "redirect_uris": ["http://localhost:5002/callback"],
        "client_name": "Demo 第三方应用",
    }
}

auth_codes = {}

tokens = {}

users = {
    "alice": {"username": "alice", "password": "password123", "email": "alice@example.com"},
    "bob": {"username": "bob", "password": "password456", "email": "bob@example.com"},
}

# ============================================================
# 辅助函数
# ============================================================


def generate_code():
    return secrets.token_urlsafe(32)


def generate_token():
    return secrets.token_urlsafe(48)


# ============================================================
# 端点 1: 授权端点 - 用户登录 + 授权确认
# ============================================================

LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head><title>OAuth Provider - 登录</title></head>
<body style="font-family:sans-serif;max-width:500px;margin:50px auto;">
  <h2>🔐 OAuth 授权服务器 - 登录</h2>
  <p>应用 <strong>{{ client_name }}</strong> 请求访问你的账号</p>
  <form method="POST" action="/oauth/authorize">
    <input type="hidden" name="client_id" value="{{ client_id }}">
    <input type="hidden" name="redirect_uri" value="{{ redirect_uri }}">
    <input type="hidden" name="scope" value="{{ scope }}">
    <input type="hidden" name="state" value="{{ state }}">
    <input type="hidden" name="response_type" value="{{ response_type }}">
    <p>用户名: <input type="text" name="username" value="alice"></p>
    <p>密&emsp;码: <input type="password" name="password" value="password123"></p>
    <p><button type="submit" name="action" value="approve">✅ 同意授权</button>
       <button type="submit" name="action" value="deny">❌ 拒绝</button></p>
  </form>
</body>
</html>
"""


@app.route("/oauth/authorize", methods=["GET"])
def authorize_get():
    """
    授权端点 - GET
    这是 OAuth 流程的起点，Client 将用户重定向到这里。

    必需参数:
      - response_type: 固定为 "code"（授权码模式）
      - client_id: 客户端标识
      - redirect_uri: 回调地址
      - scope: 请求的权限范围
      - state: 防 CSRF 的随机字符串

    服务端需要做的:
      1. 验证 client_id 是否已注册
      2. 验证 redirect_uri 是否在白名单中
      3. 展示登录页面，让用户登录并确认授权
    """
    client_id = request.args.get("client_id")
    redirect_uri = request.args.get("redirect_uri")
    scope = request.args.get("scope", "")
    state = request.args.get("state", "")
    response_type = request.args.get("response_type")

    # 验证 response_type
    if response_type != "code":
        return jsonify({"error": "unsupported_response_type"}), 400

    # 验证 client_id
    client = registered_clients.get(client_id)
    if not client:
        return jsonify({"error": "invalid_client", "message": "未注册的 client_id"}), 400

    # 验证 redirect_uri
    if redirect_uri not in client["redirect_uris"]:
        return jsonify({"error": "invalid_redirect_uri", "message": "redirect_uri 不在白名单中"}), 400

    # 展示登录页面
    return render_template_string(
        LOGIN_PAGE,
        client_name=client["client_name"],
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        response_type=response_type,
    )


@app.route("/oauth/authorize", methods=["POST"])
def authorize_post():
    """
    授权端点 - POST
    用户登录并做出授权决定后，服务端需要:
      1. 验证用户身份
      2. 如果同意，生成授权码，重定向回 Client
      3. 如果拒绝，重定向回 Client 并携带 error
    """
    action = request.form.get("action")
    client_id = request.form.get("client_id")
    redirect_uri = request.form.get("redirect_uri")
    scope = request.form.get("scope", "")
    state = request.form.get("state", "")
    username = request.form.get("username")
    password = request.form.get("password")

    # 验证用户身份
    user = users.get(username)
    if not user or user["password"] != password:
        return jsonify({"error": "access_denied", "message": "用户名或密码错误"}), 401

    if action == "deny":
        # 用户拒绝授权
        return redirect(f"{redirect_uri}?error=access_denied&state={state}")

    # 用户同意授权 -> 生成授权码
    code = generate_code()
    auth_codes[code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "username": username,
        "created_at": time.time(),
        "expires_in": 600,  # 授权码 10 分钟有效
    }

    print(f"\n[Provider] 生成授权码: {code}")
    print(f"[Provider] 授权码关联用户: {username}, 权限范围: {scope}")

    # 重定向回 Client，携带授权码和 state
    return redirect(f"{redirect_uri}?code={code}&state={state}")


# ============================================================
# 端点 2: 令牌端点 - 用授权码换取 Token
# ============================================================


@app.route("/oauth/token", methods=["POST"])
def token():
    """
    令牌端点 - POST
    Client 后端用授权码 + client_secret 换取 access_token。

    必需参数:
      - grant_type: 固定为 "authorization_code"
      - code: 授权码
      - redirect_uri: 必须与授权请求时一致
      - client_id: 客户端标识
      - client_secret: 客户端密钥（证明请求来自 Client 后端）

    服务端需要做的:
      1. 验证 client_id + client_secret
      2. 验证授权码有效性（存在、未使用、未过期）
      3. 验证 redirect_uri 一致
      4. 签发 access_token 和 refresh_token
      5. 使授权码失效（一次性使用）
    """
    grant_type = request.form.get("grant_type")
    code = request.form.get("code")
    redirect_uri = request.form.get("redirect_uri")
    client_id = request.form.get("client_id")
    client_secret = request.form.get("client_secret")

    # 验证 grant_type
    if grant_type != "authorization_code":
        return jsonify({"error": "unsupported_grant_type"}), 400

    # 验证客户端身份
    client = registered_clients.get(client_id)
    if not client or client["client_secret"] != client_secret:
        return jsonify({"error": "invalid_client", "message": "client_id 或 client_secret 错误"}), 401

    # 验证授权码
    code_data = auth_codes.get(code)
    if not code_data:
        return jsonify({"error": "invalid_grant", "message": "授权码不存在或已使用"}), 400

    # 验证授权码是否过期
    if time.time() - code_data["created_at"] > code_data["expires_in"]:
        auth_codes.pop(code, None)
        return jsonify({"error": "invalid_grant", "message": "授权码已过期"}), 400

    # 验证授权码归属（防止授权码被其他 Client 窃取使用）
    if code_data["client_id"] != client_id:
        return jsonify({"error": "invalid_grant", "message": "授权码与 client_id 不匹配"}), 400

    # 验证 redirect_uri 一致
    if code_data["redirect_uri"] != redirect_uri:
        return jsonify({"error": "invalid_grant", "message": "redirect_uri 不一致"}), 400

    # 授权码一次性使用，用完即删
    auth_codes.pop(code)

    # 签发 Token
    access_token = generate_token()
    refresh_token = generate_token()

    tokens[access_token] = {
        "client_id": client_id,
        "username": code_data["username"],
        "scope": code_data["scope"],
        "created_at": time.time(),
        "expires_in": 3600,  # 1 小时有效
    }

    print(f"\n[Provider] 签发 Token: {access_token[:20]}...")
    print(f"[Provider] Token 关联用户: {code_data['username']}")

    return jsonify(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": refresh_token,
            "scope": code_data["scope"],
        }
    )


# ============================================================
# 端点 3: 受保护资源端点 - 验证 Token 返回数据
# ============================================================


@app.route("/api/userinfo", methods=["GET"])
def userinfo():
    """
    受保护资源端点
    Client 携带 access_token 请求用户信息。

    请求头:
      Authorization: Bearer <access_token>

    服务端需要做的:
      1. 从请求头提取 Bearer Token
      2. 验证 Token 有效性（存在、未过期）
      3. 根据 scope 决定返回哪些字段
      4. 返回受保护的用户数据
    """
    # 提取 Token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "unauthorized", "message": "缺少 Bearer Token"}), 401

    access_token = auth_header[7:]  # 去掉 "Bearer " 前缀

    # 验证 Token
    token_data = tokens.get(access_token)
    if not token_data:
        return jsonify({"error": "invalid_token", "message": "Token 无效"}), 401

    # 验证是否过期
    if time.time() - token_data["created_at"] > token_data["expires_in"]:
        tokens.pop(access_token)
        return jsonify({"error": "token_expired", "message": "Token 已过期"}), 401

    # 获取用户数据
    user = users[token_data["username"]]
    scope = token_data["scope"]

    # 根据 scope 决定返回哪些字段
    result = {"username": user["username"]}
    if "email" in scope:
        result["email"] = user["email"]

    print(f"\n[Provider] Token 验证通过，返回用户数据: {result}")

    return jsonify(result)


# ============================================================
# 启动服务
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("OAuth 2.0 Provider (授权服务器) 启动")
    print("地址: http://localhost:5001")
    print("=" * 60)
    print("\n已注册的客户端:")
    for cid, client in registered_clients.items():
        print(f"  client_id:     {cid}")
        print(f"  client_secret: {client['client_secret']}")
        print(f"  redirect_uri:  {client['redirect_uris'][0]}")
        print()
    app.run(port=5001, debug=True)
