# 多租户架构设计文档

**项目：** ScanIt/扫客
**日期：** 2026-05-12
**状态：** 已确认

---

## 1. 架构概述

### 1.1 设计决策

| 方面 | 决策 | 说明 |
|------|------|------|
| 隔离方式 | Tenant ID 逻辑隔离 | 所有业务表加 tenant_id，API 自动注入 |
| 租户结构 | 扁平租户 | MVP 阶段不做层级，后续可扩展 |
| 计费模式 | 配额制 | 检测次数/月，后续可精细化 |
| 门户分离 | 双门户 | `/app` 用户端 + `/admin` 管理端 |

### 1.2 角色权限

```
System Admin    → 平台管理（创建租户、全局配置）
Tenant Admin    → 租户管理（用户、配置、额度）
Reviewer        → 检测结果审核
User            → 作品管理、发起检测、查看报告
```

---

## 2. 数据模型

### 2.1 新增表

```sql
-- 租户表
CREATE TABLE tenants (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,              -- 租户名称
    slug VARCHAR(50) UNIQUE NOT NULL,        -- 租户标识（用于子域名等）
    plan VARCHAR(20) DEFAULT 'basic',        -- 套餐：basic/pro/enterprise
    quota_monthly INT DEFAULT 100,           -- 月度检测配额
    quota_used INT DEFAULT 0,                -- 已使用配额
    is_active BOOLEAN DEFAULT TRUE,
    settings JSONB DEFAULT '{}',             -- 租户级配置
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- 租户配置（继承全局配置）
-- settings 示例：
{
    "image_threshold": 0.85,
    "video_threshold": 0.8,
    "search_engines": ["google", "baidu"],
    "llm_tier": "tier_2"
}
```

### 2.2 现有表修改

所有业务表添加 `tenant_id`：

```sql
-- users
ALTER TABLE users ADD COLUMN tenant_id UUID REFERENCES tenants(id);

-- works
ALTER TABLE works ADD COLUMN tenant_id UUID REFERENCES tenants(id);

-- tasks
ALTER TABLE tasks ADD COLUMN tenant_id UUID REFERENCES tenants(id);

-- detection_results
ALTER TABLE detection_results ADD COLUMN tenant_id UUID REFERENCES tenants(id);
```

### 2.3 User 模型更新

```python
class User(Base):
    # 现有字段...
    tenant_id: Mapped[UUID | None] = mapped_column(ForeignKey("tenants.id"))
    role: Mapped[str] = mapped_column(
        Enum("system_admin", "tenant_admin", "reviewer", "user", name="user_role_enum")
    )
```

---

## 3. API 设计

### 3.1 门户路由

| 门户 | 路由前缀 | 角色 |
|------|----------|------|
| 用户端 | `/api/...` | user, reviewer, tenant_admin |
| 管理端 | `/api/admin/...` | tenant_admin, system_admin |
| 平台端 | `/api/system/...` | system_admin |

### 3.2 新增 API 端点

**租户管理（System Admin）：**
```
POST   /api/system/tenants          # 创建租户
GET    /api/system/tenants          # 租户列表
PUT    /api/system/tenants/{id}     # 更新租户
DELETE /api/system/tenants/{id}     # 禁用租户
```

**租户内管理（Tenant Admin）：**
```
GET    /api/admin/users             # 租户用户列表
POST   /api/admin/users             # 创建用户
PUT    /api/admin/users/{id}        # 更新用户角色
DELETE /api/admin/users/{id}        # 禁用用户

GET    /api/admin/quota             # 查看配额使用
GET    /api/admin/settings          # 租户配置
PUT    /api/admin/settings          # 更新配置

GET    /api/admin/tasks             # 所有检测任务
GET    /api/admin/reports           # 统计报告
```

### 3.3 租户注入中间件

```python
async def get_current_tenant(
    current_user: User = Depends(get_current_user),
) -> Tenant:
    if current_user.role == "system_admin":
        return None  # 系统管理员跨租户
    if not current_user.tenant_id:
        raise HTTPException(400, "User not assigned to tenant")
    return await tenant_repo.get(current_user.tenant_id)
```

---

## 4. 前端架构

### 4.1 路由结构

```
/app                    # 用户端
├── /dashboard
├── /works
├── /tasks
├── /reports
└── /settings

/admin                  # 管理端
├── /dashboard
├── /users
├── /quota
├── /tasks
├── /reports
└── /settings
```

### 4.2 权限控制

```typescript
// 前端路由守卫
const routes = {
  '/app/*': ['user', 'reviewer', 'tenant_admin'],
  '/admin/*': ['tenant_admin', 'system_admin'],
  '/admin/quota': ['tenant_admin'],
}
```

---

## 5. 实现计划

### Phase 1: 数据模型（2天）
- [ ] 创建 Tenant 模型
- [ ] 修改 User 模型（添加 tenant_id, 更新 role enum）
- [ ] 所有业务表添加 tenant_id
- [ ] 数据库迁移脚本

### Phase 2: API 层（3天）
- [ ] 租户注入中间件
- [ ] Tenant CRUD API
- [ ] Admin API（用户管理、配置、配额）
- [ ] 权限装饰器

### Phase 3: 前端（4天）
- [ ] Admin 布局组件
- [ ] 用户管理页面
- [ ] 配额监控页面
- [ ] 租户配置页面

### Phase 4: 测试（2天）
- [ ] 租户隔离测试
- [ ] 权限测试
- [ ] E2E 测试

---

## 6. 注意事项

1. **数据隔离**：所有查询必须带 `tenant_id` 过滤
2. **配额检查**：创建检测任务前检查配额
3. **System Admin**：可跨租户操作，需特殊处理
4. **向后兼容**：现有数据需要分配默认租户

---

**确认人：** 左左
**确认时间：** 2026-05-12 06:30
