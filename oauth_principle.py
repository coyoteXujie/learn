"""
OAuth 2.0 原理详解
==================

一、OAuth 是什么？
------------------
OAuth 2.0 是一个**授权框架**（不是认证协议），它允许第三方应用在**不获取用户密码**的前提下，
获取用户在某个服务上的**有限访问权限**。

核心思想：用 "令牌(Token)" 代替 "密码"。

类比：
  你住酒店，不想把房间钥匙给朋友，而是去前台给朋友办了一张"临时房卡"，
  这张卡只能开你的房门，而且可以设置过期时间和权限范围。
  - 你 = Resource Owner（资源拥有者）
  - 前台 = Authorization Server（授权服务器）
  - 朋友 = Client（第三方应用）
  - 房卡 = Access Token（访问令牌）


二、四个核心角色
----------------
┌─────────────┐                                    ┌─────────────┐
│             │  1. 用户点击"使用XX登录"             │             │
│   Resource  │ ──────────────────────────────────> │   Client    │
│   Owner     │                                    │  (第三方应用) │
│   (用户)    │  2. 重定向到授权服务器登录            │             │
│             │ <────────────────────────────────── │             │
└──────┬──────┘                                    └──────┬──────┘
       │                                                  │
       │ 3. 用户在授权服务器上登录并同意授权                 │
       ▼                                                  │
┌─────────────┐                                           │
│             │  4. 返回授权码(Authorization Code)         │
│ Authorization│ ──────────────────────────────────────> │
│   Server    │                                           │
│ (授权服务器)  │  5. Client用授权码换取Access Token        │
│             │ <────────────────────────────────────── │
│             │  6. 返回 Access Token                    │
│             │ ──────────────────────────────────────> │
└─────────────┘                                           │
                                                          │
┌─────────────┐                                           │
│             │  7. Client 用 Token 请求受保护资源          │
│  Resource   │ <────────────────────────────────────── │
│   Server    │                                           │
│ (资源服务器)  │  8. 返回受保护的数据                      │
│             │ ──────────────────────────────────────> │
└─────────────┘                                           │


三、OAuth 2.0 四种授权模式
--------------------------

1. 授权码模式 (Authorization Code) —— 最安全、最常用 ★★★
   适用场景：有后端的 Web 应用
   流程：用户登录 -> 获取授权码 -> 后端用授权码换 Token

2. 隐式模式 (Implicit) —— 已废弃 ⚠️
   适用场景：纯前端 SPA（已不推荐，改用 PKCE）
   流程：Token 直接通过浏览器返回（不安全）

3. 密码模式 (Resource Owner Password Credentials) —— 不推荐 ⚠️
   适用场景：高度信任的第一方应用
   流程：直接用用户名密码换 Token

4. 客户端凭证模式 (Client Credentials) —— 服务间通信
   适用场景：机器对机器，无用户参与
   流程：用 client_id + client_secret 直接换 Token


四、授权码模式详细流程（最常用）
--------------------------------

步骤1: 用户点击 "使用 GitHub 登录"
  Client 构造 URL，将用户重定向到授权服务器：
  GET https://github.com/login/oauth/authorize?
      response_type=code          # 固定为 code
      &client_id=xxx              # Client 的唯一标识
      &redirect_uri=xxx           # 授权后回调地址
      &scope=read:user            # 请求的权限范围
      &state=abc123               # 防 CSRF 的随机字符串

步骤2: 用户在授权服务器上登录并同意授权
  授权服务器展示登录页面，用户输入账号密码，确认授权

步骤3: 授权服务器重定向回 Client，携带授权码
  302 Redirect -> https://client.com/callback?
      code=AUTHORIZATION_CODE     # 授权码，一次性，短期有效
      &state=abc123               # 原样返回，用于验证

步骤4: Client 后端用授权码换取 Token
  POST https://github.com/login/oauth/access_token
  Body:
      grant_type=authorization_code
      &code=AUTHORIZATION_CODE
      &redirect_uri=xxx
      &client_id=xxx
      &client_secret=xxx          # 只有后端知道，保证安全

步骤5: 授权服务器返回 Token
  {
      "access_token": "ghp_xxxxx",
      "token_type": "Bearer",
      "expires_in": 3600,
      "refresh_token": "ghr_xxxxx",
      "scope": "read:user"
  }

步骤6: Client 使用 Token 访问资源
  GET https://api.github.com/user
  Header: Authorization: Bearer ghp_xxxxx


五、服务要支持 OAuth 认证，需要做什么？
----------------------------------------

一个服务要成为 OAuth Provider（如 GitHub、Google），需要实现：

1. 注册管理
   - 提供 client_id 和 client_secret 的发放
   - 管理 redirect_uri 白名单
   - 管理应用权限范围 (scope)

2. 授权端点 (Authorization Endpoint)
   - GET /oauth/authorize
   - 展示登录页面
   - 展示授权确认页面（"XX应用想访问你的XX数据，是否同意？"）
   - 生成授权码 (authorization_code)
   - 重定向回 client 的 redirect_uri

3. 令牌端点 (Token Endpoint)
   - POST /oauth/token
   - 验证 client_id + client_secret
   - 验证授权码的有效性
   - 签发 access_token 和 refresh_token
   - 支持 grant_type=authorization_code 和 grant_type=refresh_token

4. 资源端点 (Resource Endpoint)
   - 验证 Bearer Token 的有效性
   - 根据 scope 限制返回的数据范围

5. 安全措施
   - state 参数防 CSRF
   - redirect_uri 严格匹配
   - 授权码一次性使用 + 短期有效
   - Token 使用 HTTPS 传输
   - 支持 PKCE（对公开客户端）


六、Client 请求时多了什么？
---------------------------

普通 API 请求：
  GET /api/user
  （无认证信息，被拒绝 401）

使用 OAuth Token 的请求：
  GET /api/user
  Authorization: Bearer eyJhbGciOiJSUzI1NiIs...

区别：
  1. 请求头多了 Authorization: Bearer <access_token>
  2. 不需要携带用户名/密码
  3. Token 有过期时间和权限范围限制
  4. Token 可以被撤销，而密码不能随意改

获取 Token 的过程（对比普通登录）：
  普通登录：POST /login {username, password} -> session_id
  OAuth：  需要先经过授权服务器，获取授权码，再换取 token


七、Token 的类型
----------------

1. 不透明 Token (Opaque Token)
   - 随机字符串，如 "ghp_abc123xyz"
   - 资源服务器需要每次向授权服务器验证（或查数据库）
   - 优点：可以立即撤销

2. JWT Token (自包含 Token)
   - 格式：header.payload.signature
   - 资源服务器可以自己验证签名，不需要每次问授权服务器
   - 优点：无状态，性能好
   - 缺点：无法立即撤销（除非引入黑名单）

3. Refresh Token
   - 用于在 access_token 过期后获取新的 access_token
   - 不发给资源服务器，只在授权服务器使用
   - 有效期长，但只能使用一次


八、OAuth 2.0 vs OpenID Connect (OIDC)
---------------------------------------

OAuth 2.0 解决的是**授权**问题："你能访问什么？"
OIDC 解决的是**认证**问题："你是谁？"

OIDC 在 OAuth 2.0 之上增加了：
  - id_token (JWT 格式，包含用户身份信息)
  - userinfo 端点
  - 标准化的 scope: openid, profile, email

大多数"使用 XX 登录"的功能，实际用的是 OIDC，不是纯 OAuth 2.0。
"""

if __name__ == "__main__":
    help(__import__("__main__"))
