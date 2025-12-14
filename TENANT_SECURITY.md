# 租户安全系统

memRagAgent 实现了完整的多租户安全隔离机制，支持 API Key 认证和数据隔离。

## 核心概念

### 1. 租户 (Tenant)
- 数据隔离的最小单位
- `tenant.code` = `project_id`（在 API 中使用）
- 每个租户有独立的用户、用户组、API Keys

### 2. 用户 (User)
- 属于某个租户
- 有角色权限：`admin` / `member` / `viewer`
- 可选，用于多人协作场景

### 3. API Key
- 访问凭证，必须绑定到租户
- 可选绑定到用户
- 有权限范围 (scopes)：`*` 表示全部权限

## 认证流程

### 请求头

| Header | 说明 | 必填 |
|--------|------|------|
| `X-API-Key` | API 密钥 | 是（生产模式） |
| `X-Project-Id` | 项目/租户编码 | 否（管理员可不填） |
| `X-User-Id` | 用户 ID | 否（可选追踪） |

### 认证模式

```
┌─────────────────────────────────────────────────────────────┐
│                      请求进入                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │   AUTH_ENABLED = true ?      │
        └──────────────┬───────────────┘
                       │
           ┌───────────┴───────────┐
           │ false                 │ true
           ▼                       ▼
   ┌───────────────┐    ┌───────────────────────┐
   │ 开发模式      │    │ 验证 X-API-Key        │
   │ 无需认证      │    └───────────┬───────────┘
   │ 管理员权限    │                │
   └───────────────┘                ▼
                       ┌───────────────────────┐
                       │ Key == ADMIN_API_KEY? │
                       └───────────┬───────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │ 是                          │ 否
                    ▼                             ▼
           ┌─────────────────┐      ┌─────────────────────┐
           │ 管理员模式      │      │ 查询数据库验证 Key  │
           │ 可访问所有数据  │      └───────────┬─────────┘
           └─────────────────┘                  │
                                                ▼
                                   ┌─────────────────────────┐
                                   │ 工程模式                │
                                   │ 只能访问该租户的数据   │
                                   └─────────────────────────┘
```

## 数据库表结构

### tenants（租户表）
```sql
CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,  -- 即 project_id
    name VARCHAR(200) NOT NULL,
    type VARCHAR(20) DEFAULT 'team',   -- personal/team/enterprise
    status VARCHAR(20) DEFAULT 'active',
    config JSONB
);
```

### tenant_users（用户表）
```sql
CREATE TABLE tenant_users (
    id SERIAL PRIMARY KEY,
    tenant_id INT REFERENCES tenants(id),
    group_id INT REFERENCES user_groups(id),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(200) UNIQUE,
    display_name VARCHAR(200),
    role VARCHAR(20) DEFAULT 'member',  -- admin/member/viewer
    status VARCHAR(20) DEFAULT 'active'
);
```

### api_keys（API 密钥表）
```sql
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    tenant_id INT REFERENCES tenants(id),
    user_id INT REFERENCES tenant_users(id),  -- 可选
    name VARCHAR(100) NOT NULL,
    key_prefix VARCHAR(20) NOT NULL,    -- 用于显示
    key_hash VARCHAR(200) NOT NULL,     -- 哈希存储
    scopes JSONB DEFAULT '["*"]',
    status VARCHAR(20) DEFAULT 'active'
);
```

## API 端点

### 租户管理

| Method | Endpoint | 说明 |
|--------|----------|------|
| GET | `/api/tenants` | 列出所有租户 |
| POST | `/api/tenants` | 创建租户 |
| GET | `/api/tenants/{id}` | 获取租户详情 |
| PUT | `/api/tenants/{id}` | 更新租户 |
| DELETE | `/api/tenants/{id}` | 删除租户 |

### 用户管理

| Method | Endpoint | 说明 |
|--------|----------|------|
| GET | `/api/tenants/{id}/users` | 列出租户用户 |
| POST | `/api/tenants/{id}/users` | 创建用户 |
| GET | `/api/users/{id}` | 获取用户详情 |
| PUT | `/api/users/{id}` | 更新用户 |
| DELETE | `/api/users/{id}` | 删除用户 |

### API Key 管理

| Method | Endpoint | 说明 |
|--------|----------|------|
| GET | `/api/tenants/{id}/api-keys` | 列出租户 API Keys |
| POST | `/api/tenants/{id}/api-keys` | 创建 API Key |
| DELETE | `/api/api-keys/{id}` | 撤销 API Key |
| POST | `/api/api-keys/{id}/regenerate` | 重新生成 API Key |

### 用户组管理

| Method | Endpoint | 说明 |
|--------|----------|------|
| GET | `/api/tenants/{id}/groups` | 列出用户组 |
| POST | `/api/tenants/{id}/groups` | 创建用户组 |

## 前端使用

### 设置认证信息

在 Settings 页面配置：
- API Key：从租户管理页面创建
- Project ID：租户编码（tenant.code）

### HTTP 客户端

```typescript
// 自动附加认证头
import http from './api/http'

// 所有请求自动带上 X-API-Key 和 X-Project-Id
const data = await http.get('/api/memory/memories/query')
```

### 本地存储

```typescript
// API Key 存储
localStorage.getItem('memrag_api_key')
localStorage.getItem('memrag_project_id')
```

## 测试配置

测试代码使用 `test_config.py` 集中管理配置：

```python
from test_config import (
    ADMIN,           # 管理员配置
    TENANT_A,        # 测试租户 A
    TENANT_B,        # 测试租户 B
    TEST_USER_1,     # 测试用户 1
    get_admin_headers,
    get_user_headers,
)
```

### 运行测试

```bash
# 开发模式测试（AUTH_ENABLED=false）
cd backend/tests
pytest test_auth.py -v

# 生产模式测试（需要配置）
AUTH_ENABLED=true pytest test_auth.py::TestAuthEnabled -v
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `AUTH_ENABLED` | 是否启用认证 | `false` |
| `ADMIN_API_KEY` | 管理员 API Key | - |
| `INTERNAL_API_KEY` | 服务间通信 Key（备用） | - |

## 服务间凭证传递

### daoyou_agent 调用架构

```
用户请求 (API Key A, project_id)
         │
         ▼
    daoyou_agent
         │ 提取用户凭证
         ▼
   ┌─────────────────────────────────────────┐
   │  传递用户原始 API Key 和 project_id     │
   └─────────────────────────────────────────┘
         │
         ├──────────────┬──────────────┐
         ▼              ▼              ▼
    Memory 服务   Knowledge 服务   Graph 服务
         │              │              │
         ▼              ▼              ▼
   验证用户 Key    验证用户 Key    验证用户 Key
         │              │              │
         ▼              ▼              ▼
   apply_project_filter (按 project_id 过滤数据)
```

### 凭证优先级

```python
# 服务客户端中
api_key = user_api_key or self.api_key
#         ↑ 用户 Key 优先   ↑ 内部 Key 作为 fallback
```

**关键点**：
- 用户的 API Key 会**原样传递**给 Memory/Knowledge 服务
- 保持用户级别的租户隔离
- 内部 Key 仅在用户未提供时作为 fallback（开发模式）

## 知识图谱隔离

Neo4j 图谱数据按 `project_id` 隔离：

```cypher
-- 实体节点包含 project_id
MERGE (n:Person {name: $name, project_id: $project_id})

-- 查询时按 project_id 过滤
MATCH (n) WHERE n.project_id = $project_id
```

**效果**：不同租户的同名实体（如"张三"）是独立的节点，互不干扰。

## 安全最佳实践

1. **生产环境必须设置** `AUTH_ENABLED=true`
2. **API Key 只显示一次**，创建后立即保存
3. **使用工程级 Key** 而非管理员 Key
4. **定期轮换** API Key
5. **最小权限原则**：按需设置 scopes

## 故障排除

### 401 未授权
- 检查 `X-API-Key` 是否正确
- 检查 API Key 状态是否为 `active`
- 检查 `AUTH_ENABLED` 环境变量

### 403 禁止访问
- 检查 `X-Project-Id` 是否匹配
- 检查 API Key 的 scopes 是否足够

### 密钥丢失
1. 登录管理页面
2. 找到对应的 API Key
3. 点击"重新生成"
4. 保存新密钥
