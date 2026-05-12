# ScanIt 项目看板

> 最后更新：2026-05-12
> 当前阶段：M6 多租户架构改造（进行中）

---

## 📊 项目概览

| 指标 | 状态 |
|------|------|
| M0-M5 基础功能 | ██████████ 100% ✅ |
| M6 多租户改造 | ██████████ 100% ✅ |
| LLM 增强 | ██████████ 100% ✅ |
| 代码审查 | ██████████ 100% ✅ |

---

## 🎯 里程碑追踪

```
M0 [██████████] 100% ✅ 项目初始化
M1 [██████████] 100% ✅ 后端骨架
M2 [██████████] 100% ✅ 核心引擎
M3 [██████████] 100% ✅ 任务调度
M4 [██████████] 100% ✅ 前端开发
M5 [██████████] 100% ✅ 部署上线
M6 [██████████] 100% ✅ 多租户改造
```

---

## 📋 M6 多租户改造 — 任务看板

### 架构决策

| 方面 | 决策 |
|------|------|
| 隔离方式 | Tenant ID 逻辑隔离 |
| 门户分离 | `/app` 用户端 + `/admin` 管理端 |
| 租户结构 | 扁平租户（MVP） |
| 计费模式 | 配额制（检测次数/月） |
| 角色体系 | system_admin / tenant_admin / reviewer / user |

### 设计文档
- `docs/DESIGN_MULTI_TENANT.md`

---

### ✅ Phase 1: 数据模型（已完成）

| ID | 任务 | 依赖 | 状态 |
|----|------|------|------|
| T1.1 | 创建 Tenant 模型（`app/models/tenant.py`） | - | ✅ |
| T1.2 | 修改 User 模型（tenant_id + 新 role enum） | T1.1 | ✅ |
| T1.3 | 业务表加 tenant_id（works/tasks/results） | T1.1 | ✅ |
| T1.4 | Alembic 迁移（`m6_001_multi_tenant.py`） | T1.1-T1.3 | ✅ |
| T1.5 | 数据迁移脚本（`scripts/migrate_default_tenant.py`） | T1.4 | ✅ |
| T1.6 | 租户 Schema（`schemas/tenant.py`）+ 更新 user schema | T1.1 | ✅ |

---

### ✅ Phase 2: API 层（已完成）

| ID | 任务 | 依赖 | 状态 | 改动文件 |
|----|------|------|------|----------|
| T2.1 | deps.py 租户依赖注入 | T1.2 | ✅ | `api/deps.py` |
| T2.2 | 租户 CRUD API（system_admin 专用） | T1.1 | ✅ | `api/tenants.py` |
| T2.3 | 路由注册 | T2.2 | ✅ | `api/__init__.py` |
| T2.4 | JWT 加入 tenant_id + role | T2.1 | ✅ | `api/auth.py` |
| T2.5 | 注册接口：支持邀请码/租户分配 | T2.4 | ✅ | `api/auth.py` |
| T2.6 | works.py 加 tenant_id 过滤 | T2.1 | ✅ | `api/works.py` |
| T2.7 | tasks.py 加 tenant_id 过滤 + 配额检查 | T2.1 | ✅ | `api/tasks.py` |
| T2.8 | results.py 加 tenant_id 过滤 | T2.1 | ✅ | `api/results.py` |
| T2.9 | llm.py 读取租户 llm_tier 配置 | T2.1 | ✅ | `api/llm.py` |
| T2.10 | 配额检查中间件 | T2.4 | ✅ | 新建 `api/middleware.py` |
| T2.11 | admin 用户管理 API | T2.5 | ✅ | `api/tenants.py` |

---

### ✅ Phase 3: 前端适配（已完成）

| ID | 任务 | 依赖 | 状态 | 改动范围 |
|----|------|------|------|----------|
| T3.1 | 前端 client.ts 补充 tenant API 方法 | T2.2 | ✅ | `client.ts` |
| T3.2 | Admin Dashboard 页面组件 | T3.1 | ✅ | 新建 `AdminDashboard.tsx` |
| T3.3 | App.tsx 双门户路由 | T3.2 | ✅ | `App.tsx` |
| T3.4 | tsconfig.json 修复 vite 类型 | - | ✅ | `tsconfig.json` |

---

### ✅ Phase 4: 测试与收尾（已完成）

| ID | 任务 | 依赖 | 状态 |
|----|------|------|------|
| T4.1 | 租户隔离单测 | T2.6-T2.8 | ✅ |
| T4.2 | 权限控制单测 | T2.4 | ✅ |
| T4.3 | 配额扣减单测 | T2.10 | ✅ |
| T4.4 | 修复测试 fixtures + tenant_id | T2.10 | ✅ |
| T4.5 | 修复 JSONB→JSON SQLite 兼容 | T1.1 | ✅ |

---

## ✅ 已完成里程碑

| 里程碑 | 完成日期 | 说明 |
|--------|----------|------|
| M0-M5 | 2026-05-11 | 基础功能全部完成 |
| LLM 增强 | 2026-05-11 | 三层 Provider + 日志 + 注释 |
| 代码审查 | 2026-05-12 | JWT 修复 + 安全审查 |
| M6 Phase 1 | 2026-05-12 | 数据模型 + 迁移 ✅ |
| M6 Phase 3 | 2026-05-12 | 前端适配（双门户）✅ |
| M6 Phase 4 | 2026-05-12 | 测试修复（68 passed）✅ |

---

## 📌 当前焦点

**M6 多租户改造完成！** ✅

测试结果：68 passed

---

## 📝 每日更新日志

| 日期 | 更新内容 |
|------|----------|
| 2026-05-11 | M0-M5 + LLM 增强 ✅ |
| 2026-05-12 | 代码审查 + JWT 修复 ✅ |
| 2026-05-12 | 多租户架构设计确认 ✅ |
| 2026-05-12 | Phase 1 数据模型完成 ✅ |
| 2026-05-12 | Phase 2 API 层全部完成 ✅ |
| 2026-05-12 | Phase 3 前端适配完成 ✅ |
| 2026-05-12 | Phase 4 测试修复完成（68 passed）✅ |
