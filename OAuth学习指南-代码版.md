# OAuth 2.0 完全指南

> 从原理到实战，一篇搞懂 OAuth 到底在干什么

---

## 一、OAuth 是什么？用生活例子理解

你住酒店，朋友想进你房间拿个东西。你有两种选择：

- ❌ **把房间钥匙给朋友** → 相当于把密码告诉第三方，太危险
- ✅ **去前台给朋友办一张临时房卡** → 限定时间、限定权限，安全可控

OAuth 做的就是第二件事：**用令牌（Token）代替密码**，让第三方应用在不知道你密码的情况下，获取你有限的访问权限。

| 生活角色 | OAuth 角色 | 说明 |
|---------|-----------|------|
| 你 | Resource Owner（资源拥有者） | 拥有数据的用户 |
| 酒店前台 | Authorization Server（授权服务器） | 负责认证和发令牌 |
| 朋友 | Client（第三方应用） | 想访问你数据的应用 |
| 房卡 | Access Token（访问令牌） | 临时访问凭证 |
| 你的房间 | Resource Server（资源服务器） | 存放受保护数据的服务 |

---

## 二、OAuth 2.0 四大角色

```plantuml
@startuml
skinparam backgroundColor #FEFEFE
skinparam participantBorderColor #333333
skinparam participantBackgroundColor #E8F4FD
skinparam arrowColor #333333

title OAuth 2.0 四大角色交互流程

participant "Resource Owner\n(用户)" as RO
participant "Client\n(第三方应用)" as Client
participant "Authorization Server\n(授权服务器)" as Auth
participant "Resource Server\n(资源服务器)" as Resource

RO -> Client : ① 点击"使用XX登录"
Client -> RO : ② 重定向到授权服务器
RO -> Auth : ③ 用户登录并同意授权
Auth -> Client : ④ 返回授权码(Authorization Code)
Client -> Auth : ⑤ 用授权码换取 Access Token
Auth -> Client : ⑥ 返回 Access Token
Client -> Resource : ⑦ 用 Token 请求受保护资源
Resource -> Client : ⑧ 返回受保护的数据

@enduml
```

**简单记忆**：
- **Resource Owner**：你，拥有数据的人
- **Client**：想用你数据的第三方应用（比如"使用微信登录"的那个网站）
- **Authorization Server**：发令牌的（微信的认证服务器）
- **Resource Server**：存数据的（微信的用户信息 API）

> 实际上 Authorization Server 和 Resource Server 通常是同一个服务（比如 GitHub），只是逻辑上分开。

---

## 三、四种授权模式

OAuth 2.0 定义了四种授权模式（Grant Type），适用于不同场景：

### 3.1 授权码模式（Authorization Code）⭐ 最常用

**适用场景**：有后端的 Web 应用

**为什么最安全？** 因为授权码和 Token 分两步获取，Token 只在 Client 后端和 Provider 之间传输，不经过浏览器。

```plantuml
@startuml
skinparam backgroundColor #FEFEFE
skinparam participantBorderColor #333333
skinparam participantBackgroundColor #E8F4FD
skinparam arrowColor #333333

title 授权码模式 (Authorization Code) 详细流程

participant "用户浏览器" as Browser #FFF3E0
participant "Client 后端" as Client #E8F5E9
participant "Authorization Server\n(授权服务器)" as Auth #E8F4FD
participant "Resource Server\n(资源服务器)" as Resource #FCE4EC

== 第一步：用户发起登录 ==
Browser -> Client : ① 点击"使用XX登录"
Client --> Browser : ② 302 重定向到授权服务器\nGET /oauth/authorize?response_type=code&client_id=xxx&redirect_uri=xxx&scope=read&state=abc123

== 第二步：用户在授权服务器上认证 ==
Browser -> Auth : ③ 用户登录并同意授权
Auth --> Browser : ④ 302 重定向回 Client\nGET /callback?code=AUTH_CODE&state=abc123

== 第三步：Client 后端用授权码换 Token（不经过浏览器！）==
Browser -> Client : ⑤ 浏览器带着 code 访问 callback
Client -> Auth : ⑥ POST /oauth/token\ngrant_type=authorization_code&code=AUTH_CODE&client_id=xxx&client_secret=xxx
Auth --> Client : ⑦ 返回 { access_token, token_type, expires_in, refresh_token }

== 第四步：Client 使用 Token 访问资源 ==
Client -> Resource : ⑧ GET /api/userinfo\nAuthorization: Bearer <access_token>
Resource --> Client : ⑨ 返回用户数据
Client --> Browser : ⑩ 登录成功，展示用户信息

note right of Client : 步骤⑥⑦只在后端之间进行\n浏览器看不到 Token！

@enduml
```

### 3.2 隐式模式（Implicit）⚠️ 已废弃

**适用场景**：纯前端 SPA（已不推荐，改用授权码+PKCE）

Token 直接通过浏览器 URL 返回，容易被截获，安全性差。

```plantuml
@startuml
skinparam backgroundColor #FEFEFE
skinparam participantBorderColor #333333
skinparam participantBackgroundColor #E8F4FD
skinparam arrowColor #333333

title 隐式模式 (Implicit) - 已废弃

participant "用户浏览器" as Browser #FFF3E0
participant "Client\n(前端SPA)" as Client #E8F5E9
participant "Authorization Server\n(授权服务器)" as Auth #E8F4FD

Browser -> Client : ① 点击登录
Client --> Browser : ② 重定向到授权服务器\nGET /oauth/authorize?response_type=token&client_id=xxx
Browser -> Auth : ③ 用户登录并同意授权
Auth --> Browser : ④ ⚠️ Token 直接通过 URL 返回\n302 Redirect → /callback#access_token=xxx&token_type=Bearer

note right of Browser : ⚠️ Token 暴露在浏览器 URL 中！\n容易被中间人截获\n这就是为什么被废弃

@enduml
```

### 3.3 密码模式（Resource Owner Password Credentials）⚠️ 不推荐

**适用场景**：高度信任的第一方应用

用户直接把用户名密码给 Client，Client 拿去换 Token。违背了 OAuth "不用密码"的初衷。

```plantuml
@startuml
skinparam backgroundColor #FEFEFE
skinparam participantBorderColor #333333
skinparam participantBackgroundColor #E8F4FD
skinparam arrowColor #333333

title 密码模式 (Password) - 不推荐

participant "用户" as User #FFF3E0
participant "Client\n(第一方应用)" as Client #E8F5E9
participant "Authorization Server\n(授权服务器)" as Auth #E8F4FD

User -> Client : ① ⚠️ 直接输入用户名和密码
Client -> Auth : ② POST /oauth/token\ngrant_type=password&username=xxx&password=xxx&client_id=xxx&client_secret=xxx
Auth --> Client : ③ 返回 { access_token, refresh_token }

note right of User : ⚠️ 用户密码直接暴露给 Client\n违背了 OAuth "不用密码"的初衷\n仅适合高度信任的第一方应用

@enduml
```

### 3.4 客户端凭证模式（Client Credentials）

**适用场景**：机器对机器通信，无用户参与

Client 直接用 `client_id` + `client_secret` 换 Token，适合微服务间调用。

```plantuml
@startuml
skinparam backgroundColor #FEFEFE
skinparam participantBorderColor #333333
skinparam participantBackgroundColor #E8F4FD
skinparam arrowColor #333333

title 客户端凭证模式 (Client Credentials) - 服务间通信

participant "服务 A\n(Client)" as Client #E8F5E9
participant "Authorization Server\n(授权服务器)" as Auth #E8F4FD
participant "服务 B\n(Resource Server)" as Resource #FCE4EC

Client -> Auth : ① POST /oauth/token\ngrant_type=client_credentials&client_id=xxx&client_secret=xxx&scope=read
Auth --> Client : ② 返回 { access_token, expires_in }
Client -> Resource : ③ GET /api/data\nAuthorization: Bearer <access_token>
Resource --> Client : ④ 返回数据

note over Client, Resource : 无用户参与\n适合微服务间调用

@enduml
```

---

## 四、授权码模式详细拆解（重点！）

### 步骤 ①②：Client 构造授权 URL，重定向用户

用户点击"使用 GitHub 登录"按钮后，Client 构造如下 URL 并将浏览器重定向过去：

```
GET https://github.com/login/oauth/authorize?
    response_type=code          # 固定为 code（授权码模式）
    &client_id=xxx              # Client 的唯一标识（注册时获得）
    &redirect_uri=xxx           # 授权后回调地址（必须在白名单中）
    &scope=read:user            # 请求的权限范围
    &state=abc123               # 防 CSRF 的随机字符串
```

**每个参数的作用**：

| 参数 | 作用 | 谁提供 |
|------|------|--------|
| `response_type` | 告诉 Provider 用哪种模式 | Client 写死 `code` |
| `client_id` | 标识是哪个应用在请求 | 注册时 Provider 发放 |
| `redirect_uri` | 授权完成后跳回哪 | Client 注册时声明 |
| `scope` | 想要什么权限 | Client 按需请求 |
| `state` | 防 CSRF 攻击 | Client 随机生成，回调时验证 |

### 步骤 ③④：用户登录并授权，Provider 返回授权码

用户在 Provider 页面上登录并点击"同意授权"后，Provider 将浏览器重定向回 Client：

```
302 Redirect → https://client.com/callback?
    code=AUTHORIZATION_CODE     # 授权码，一次性，短期有效（约10分钟）
    &state=abc123               # 原样返回，Client 需验证是否与之前一致
```

**授权码的特点**：
- 🔒 一次性使用，用过即废
- ⏰ 短期有效（通常 10 分钟）
- 🔗 绑定了 `client_id` 和 `redirect_uri`，防止被其他应用盗用

### 步骤 ⑤⑥：Client 后端用授权码换 Token

**这是最关键的一步！** 这个请求在 Client 后端和 Provider 之间直接进行，**不经过浏览器**：

```
POST https://github.com/login/oauth/access_token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code
code=AUTHORIZATION_CODE
redirect_uri=https://client.com/callback
client_id=xxx
client_secret=xxx              # 🔑 只有 Client 后端知道！
```

Provider 返回：

```json
{
    "access_token": "ghp_xxxxxxxxxxxx",
    "token_type": "Bearer",
    "expires_in": 3600,
    "refresh_token": "ghr_xxxxxxxxxxxx",
    "scope": "read:user"
}
```

**为什么需要 `client_secret`？**

授权码通过浏览器 URL 传递，可能被截获。但攻击者不知道 `client_secret`，所以即使拿到授权码也无法换取 Token。这就是授权码模式比隐式模式安全的核心原因。

### 步骤 ⑦⑧：Client 使用 Token 访问资源

```http
GET https://api.github.com/user
Authorization: Bearer ghp_xxxxxxxxxxxx
```

Provider 验证 Token 后返回用户数据。

---

## 五、核心问题：服务要支持 OAuth，需要做什么？

一个服务要成为 OAuth Provider（像 GitHub、Google 那样支持第三方登录），需要实现以下内容：

```plantuml
@startuml
skinparam backgroundColor #FEFEFE
skinparam componentBorderColor #333333
skinparam componentBackgroundColor #E8F4FD
skinparam arrowColor #333333

title OAuth Provider 需要实现的模块

package "OAuth Provider" {

    component "客户端注册管理" as Registry #E8F5E9 {
        note as N1
          发放 client_id + client_secret
          管理 redirect_uri 白名单
          管理 scope 权限范围
        end note
    }

    component "授权端点\nGET /oauth/authorize" as Authorize #FFF3E0 {
        note as N2
          验证 client_id
          验证 redirect_uri
          展示登录 + 授权确认页面
          生成授权码
          重定向回 Client
        end note
    }

    component "令牌端点\nPOST /oauth/token" as Token #E8F4FD {
        note as N3
          验证 client_id + client_secret
          验证授权码（有效/未使用/未过期）
          签发 access_token
          签发 refresh_token
          使授权码失效
        end note
    }

    component "资源端点\nGET /api/xxx" as Resource #FCE4EC {
        note as N4
          提取 Bearer Token
          验证 Token 有效性
          根据 scope 限制返回字段
          Token 无效返回 401
        end note
    }

    component "安全措施" as Security #FFEBEE {
        note as N5
          state 防 CSRF
          redirect_uri 严格匹配
          授权码一次性 + 短期有效
          Token 使用 HTTPS 传输
          支持 PKCE
        end note
    }
}

Registry -down-> Authorize : client_id 验证
Authorize -down-> Token : 授权码
Token -down-> Resource : access_token
Security .up.> Registry
Security .up.> Authorize
Security .up.> Token
Security .up.> Resource

@enduml
```

### 5.1 客户端注册管理

第三方应用先要在你这里"注册"，你发放凭证：

```
注册时你提供：
  client_id     → 应用的唯一标识（公开的）
  client_secret → 应用的密钥（只有应用后端知道）

注册时对方提供：
  应用名称       → 展示给用户看
  redirect_uri  → 授权后的回调地址白名单
  需要的 scope  → 权限范围
```

### 5.2 授权端点 `GET /oauth/authorize`

这是用户看到的登录页面，你需要：

1. ✅ 验证 `client_id` 是否已注册
2. ✅ 验证 `redirect_uri` 是否在白名单中
3. ✅ 展示登录页面，让用户输入账号密码
4. ✅ 展示授权确认页面："XX应用想访问你的XX数据，是否同意？"
5. ✅ 用户同意后，生成授权码，重定向回 Client
6. ✅ 用户拒绝时，重定向回 Client 并携带 `error=access_denied`

### 5.3 令牌端点 `POST /oauth/token`

这是 Client 后端换取 Token 的接口，你需要：

1. ✅ 验证 `client_id` + `client_secret`（确认是合法的 Client）
2. ✅ 验证授权码有效性（存在、未使用、未过期）
3. ✅ 验证授权码归属（`client_id` 和 `redirect_uri` 是否匹配）
4. ✅ 签发 `access_token` 和 `refresh_token`
5. ✅ 使授权码失效（一次性使用）

### 5.4 资源端点 `GET /api/xxx`

这是受保护的数据接口，你需要：

1. ✅ 从请求头提取 `Authorization: Bearer <token>`
2. ✅ 验证 Token 有效性（存在、未过期）
3. ✅ 根据 `scope` 决定返回哪些字段
4. ✅ Token 无效时返回 `401 Unauthorized`

### 5.5 安全措施（必须做！）

| 措施 | 防什么攻击 |
|------|-----------|
| `state` 参数 | CSRF 攻击 |
| `redirect_uri` 严格匹配 | 开放重定向攻击 |
| 授权码一次性使用 | 授权码重放攻击 |
| 授权码短期有效 | 授权码泄露 |
| Token 使用 HTTPS | 中间人攻击 |
| 支持 PKCE | 授权码截获（公开客户端） |

---

## 六、核心问题：Client 请求时多了什么？

### 6.1 获取凭证阶段（比普通登录多了整个 OAuth 流程）

**普通登录**：
```
用户 → 输入用户名密码 → Client 后端验证 → 登录成功
```

**OAuth 登录**：
```
用户 → 点击"使用XX登录" → 跳转到Provider → 在Provider上登录 → 同意授权
→ Provider返回授权码 → Client后端用授权码+密钥换Token → 登录成功
```

```plantuml
@startuml
skinparam backgroundColor #FEFEFE
skinparam participantBorderColor #333333
skinparam arrowColor #333333

title 普通登录 vs OAuth 登录 对比

== 普通登录（直接给密码）==
participant "用户" as User1 #FFF3E0
participant "Client" as Client1 #E8F5E9

User1 -> Client1 : 用户名 + 密码
Client1 --> User1 : 登录成功 (session_id)

== OAuth 登录（用 Token 代替密码）==
participant "用户" as User2 #FFF3E0
participant "Client" as Client2 #E8F5E9
participant "Provider" as Provider #E8F4FD

User2 -> Client2 : 点击"使用XX登录"
Client2 --> User2 : 重定向到 Provider
User2 -> Provider : 在 Provider 上登录 + 同意授权
Provider -> Client2 : 授权码 → Token
Client2 --> User2 : 登录成功

note over User1, Client1 : ⚠️ 密码直接给 Client
note over User2, Provider : ✅ 密码只给 Provider\nClient 只拿到 Token

@enduml
```

多了什么？
- Client 需要提前在 Provider 注册，获得 `client_id` 和 `client_secret`
- Client 需要构造授权 URL 并重定向用户
- Client 需要实现回调接口接收授权码
- Client 需要后端发起请求用授权码换 Token

### 6.2 使用凭证阶段（每个 API 请求多了什么）

**普通请求（无认证）**：
```http
GET /api/userinfo
→ 401 Unauthorized
```

**OAuth 请求（带 Token）**：
```http
GET /api/userinfo
Authorization: Bearer ghp_xxxxxxxxxxxx
→ 200 OK + 用户数据
```

**就多了这一个请求头！** `Authorization: Bearer <access_token>`

对比普通 session 认证：

| | Session 认证 | OAuth Token 认证 |
|---|---|---|
| 凭证 | Cookie 中的 session_id | Authorization 头中的 Bearer Token |
| 谁发凭证 | Client 自己 | 授权服务器 |
| 跨域 | Cookie 有同源限制 | Token 天然跨域 |
| 撤销 | 删 session | 撤销 Token |
| 信息量 | 需查服务端 | JWT 可自包含 |

---

## 七、Token 的类型

```plantuml
@startuml
skinparam backgroundColor #FEFEFE
skinparam componentBorderColor #333333
skinparam arrowColor #333333

title Token 类型对比

rectangle "Opaque Token\n(不透明令牌)" as Opaque #E8F4FD {
    card "随机字符串\nghp_abc123xyz456" as O1
    card "每次需查授权服务器验证" as O2
    card "✅ 可立即撤销" as O3
    card "❌ 性能开销大" as O4
}

rectangle "JWT Token\n(自包含令牌)" as JWT #E8F5E9 {
    card "header.payload.signature\n三段式结构" as J1
    card "资源服务器自行验证签名" as J2
    card "✅ 无状态，性能好" as J3
    card "❌ 无法立即撤销" as J4
}

rectangle "Refresh Token\n(刷新令牌)" as Refresh #FFF3E0 {
    card "用于获取新的 access_token" as R1
    card "只在授权服务器使用" as R2
    card "有效期长，但只能用一次" as R3
}

Opaque -[hidden]down- JWT
JWT -[hidden]down- Refresh

@enduml
```

### 7.1 不透明 Token（Opaque Token）

```
ghp_abc123xyz456    ← 随机字符串，看不懂
```

- 资源服务器每次都要问授权服务器："这个 Token 有效吗？"
- 优点：可以立即撤销
- 缺点：每次都要查，性能开销大

### 7.2 JWT Token（自包含 Token）

```
eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

- 由 `header.payload.signature` 三部分组成
- 资源服务器可以自己验证签名，不需要问授权服务器
- 优点：无状态，性能好
- 缺点：无法立即撤销（除非引入黑名单）

### 7.3 Refresh Token

- 用于在 `access_token` 过期后获取新的 `access_token`
- **不发给资源服务器**，只在授权服务器使用
- 有效期长，但只能使用一次

```
POST /oauth/token
grant_type=refresh_token
refresh_token=ghr_xxxxx
client_id=xxx
client_secret=xxx

→ 返回新的 access_token + 新的 refresh_token
```

---

## 八、OAuth 2.0 vs OpenID Connect

很多人说"OAuth 登录"，但大多数"使用 XX 登录"功能实际用的是 **OpenID Connect (OIDC)**，不是纯 OAuth 2.0。

| | OAuth 2.0 | OpenID Connect |
|---|---|---|
| 解决什么问题 | **授权**：你能访问什么？ | **认证**：你是谁？ |
| 返回什么 | access_token | access_token + **id_token** |
| id_token | ❌ 没有 | ✅ JWT 格式，包含用户身份信息 |
| userinfo 端点 | ❌ 没有标准 | ✅ 标准端点获取用户信息 |
| 标准 scope | 自定义 | `openid` `profile` `email` |

**简单理解**：OIDC = OAuth 2.0 + 身份认证层

---

## 九、动手实践

本目录提供了三个 Python Demo，建议按以下顺序学习：

### 9.1 命令行 Demo（最快上手）

```bash
python oauth_flow_demo.py
```

纯命令行模拟完整 OAuth 授权码流程，无需浏览器，几分钟就能跑通。每一步都有详细输出，帮你理解数据在各方之间如何流转。

### 9.2 Web Demo（完整体验）

需要两个终端窗口：

```bash
# 终端1：启动 Provider（授权服务器）
pip install flask requests
python oauth_provider.py    # http://localhost:5001

# 终端2：启动 Client（第三方应用）
python oauth_client.py      # http://localhost:5002
```

然后浏览器访问 `http://localhost:5002`，点击"使用 OAuth Provider 登录"按钮，体验完整的浏览器交互流程。

### 9.3 文件说明

| 文件 | 说明 |
|------|------|
| `oauth_principle.py` | 原理详解（代码注释形式，建议直接看本文档） |
| `oauth_provider.py` | Provider 服务端实现（Flask，端口 5001） |
| `oauth_client.py` | Client 客户端实现（Flask，端口 5002） |
| `oauth_flow_demo.py` | 命令行联调 Demo（无需浏览器） |

---

## 十、常见问题

### Q1：OAuth 和 SSO 是什么关系？

OAuth 是授权框架，SSO（单点登录）是一种场景。OAuth 可以用来实现 SSO，但 OAuth 本身不是 SSO。OIDC 更适合做 SSO。

### Q2：为什么授权码不直接给 Token，要多一步？

因为授权码通过浏览器传递，可能被截获。多一步"用授权码换 Token"是在 Client 后端和 Provider 之间直接通信，用 `client_secret` 做认证，保证了 Token 不会泄露到浏览器。

### Q3：Token 被盗了怎么办？

- 设置较短的过期时间
- 使用 HTTPS 防止中间人攻击
- 支持 Token 撤销机制
- 绑定 Token 和客户端信息（IP、UA 等）

### Q4：PKCE 是什么？

PKCE（Proof Key for Code Exchange）是授权码模式的增强版，专为无法安全保存 `client_secret` 的公开客户端（如移动 App、SPA）设计。它在授权码流程中增加了一个随机生成的 `code_verifier` 和 `code_challenge`，防止授权码被截获后滥用。

---

> 📌 总结一句话：**OAuth 的核心就是用 Token 代替密码，服务要做的是发令牌和验令牌，Client 请求时多了 `Authorization: Bearer <token>` 这个请求头。**
