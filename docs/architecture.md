# 合同管理系统 (contract-mgmt-v2) 当前架构

## 系统目标与边界

提供一个多用户合同管理系统，支持用户注册登录、合同 CRUD、PDF/Word 附件上传下载。
角色分为管理员和普通用户，管理员可管理所有用户和合同，普通用户仅管理自己的合同。

**范围外**：电子签章、审批工作流、第三方集成、合同模板引擎、高级搜索。

## 技术栈与选择理由

| 组件 | 选择 | 理由 |
|------|------|------|
| 后端框架 | Python Flask 3.1 | 轻量、成熟，适合中小型 Web 应用 |
| ORM | SQLAlchemy 2.0 + Flask-SQLAlchemy | 声明式模型，自动迁移 |
| 数据库 | SQLite | 单文件部署，零配置，满足演示需求 |
| 认证 | Flask-Login + bcrypt | Session 管理 + 行业标准密码哈希 |
| 前端 | Jinja2 + Bootstrap 5 (CDN) | 服务端渲染，响应式布局 |
| WSGI | Werkzeug 开发服务器 | 本地开发/演示；生产使用 Nginx + systemd |
| 端口 | 19051 | 项目配置指定 |
| Base Path | /projects/contract-mgmt-v2/ | Nginx 反向代理前缀 |

## 模块职责与依赖

```
app.py            Flask 应用工厂、蓝图注册、所有路由处理、附件上传/下载
models.py         SQLAlchemy 模型: User, Contract, Attachment
config.py         配置类: SECRET_KEY, DB_URI, 上传限制, 文件类型白名单
init_db.py        数据库初始化: 建表 + 预置 admin/demo 账号
templates/        Jinja2 模板: base, login, register, dashboard, contract_*, admin_users
static/           CSS + JS 静态资源
uploads/          用户上传的附件文件存储
data/             SQLite 数据库文件
```

## 数据模型

- **User**: id, username, password_hash, role (admin/user), is_active, created_at
- **Contract**: id, title, description, counterparty, amount, status, user_id (FK), created_at, updated_at
- **Attachment**: id, filename, original_filename, file_path, file_size, mime_type, contract_id (FK), uploaded_at

## 数据流、状态流与外部接口

1. 请求 → Nginx 反向代理 → Flask (port 19051) → Blueprint (url_prefix=/projects/contract-mgmt-v2/)
2. 所有 HTML 响应注入 `Cache-Control: no-cache` 响应头
3. 静态资源 URL 携带 `?v=0.0.1` 版本令牌
4. 附件上传存储于本地 uploads/ 目录，文件名加 UUID 前缀防冲突
5. 无外部 API 依赖

## 路由设计

- `/healthz` — 健康检查 (public)
- `/auth/login`, `/auth/register`, `/auth/logout` — 认证 (public/login_required)
- `/` — 合同列表仪表盘 (login_required)
- `/contracts/create`, `/contracts/<id>`, `/contracts/<id>/edit`, `/contracts/<id>/delete` — 合同 CRUD (login_required)
- `/contracts/<id>/attachments/upload`, `/attachments/<id>/download` — 附件管理 (login_required)
- `/admin/users`, `/admin/users/<id>/toggle`, `/admin/users/<id>/delete` — 用户管理 (admin_required)

## 安全边界

- Flask-Login session 管理
- bcrypt 密码哈希（salt rounds 自动）
- 角色检查装饰器 (admin_required)
- 文件上传限制：10MB，仅 pdf/doc/docx
- 用户只能操作自己的合同（管理员除外）
- 管理员不能禁用/删除自己

## 测试策略

- curl 集成测试覆盖所有端点
- 测试覆盖：认证流程、CRUD 操作、文件上传/下载、权限控制、缓存头、静态资源
- 预置测试账号: admin/admin123, demo/demo123

## 部署拓扑

- Aliyun ECS + systemd (docker-free)
- Nginx 反向代理 → Flask Werkzeug
- 公网 URL: https://cqw.life/projects/contract-mgmt-v2/

## 已知技术债

- 无 CSRF 保护（演示环境，由 Hermes 决定是否后续添加）
- 开发服务器单进程，不适合生产并发
- 无文件类型魔术字节验证（仅检查扩展名）

## 关联 ADR 与最近变更

- ADR: 待建立
- 最近变更: v0.0.1 — 初始版本，完整用户+合同+附件管理
