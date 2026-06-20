# 合同管理系统 (contract-mgmt-v2) 运行手册

## 本地安装与启动

```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库（建表 + 预置 admin/demo 账号）
python init_db.py

# 启动开发服务器
python app.py
# 服务运行在 http://localhost:19051/projects/contract-mgmt-v2/
```

## 测试、构建与健康检查

```bash
# 健康检查
curl http://localhost:19051/projects/contract-mgmt-v2/healthz
# → {"status":"ok","version":"0.0.1"}

# 运行自动化测试
python /tmp/run_final.py  # 或使用 evidence/claude/ 下的测试脚本

# 手动测试登录
curl -c /tmp/cookies.txt -L -d "username=admin&password=admin123" \
  http://localhost:19051/projects/contract-mgmt-v2/auth/login
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| SECRET_KEY | contract-mgmt-v2-dev-key-... | Flask session 签名密钥 |
| DATABASE_URL | sqlite:///data/app.db | 数据库连接 |

## Base Path

项目部署在 `/projects/contract-mgmt-v2/`，静态资源和路由不假设部署在 `/`。

- 开发: `http://localhost:19051/projects/contract-mgmt-v2/`
- 生产: `https://cqw.life/projects/contract-mgmt-v2/`

## 缓存策略

- HTML 响应头: `Cache-Control: no-cache, no-store, must-revalidate`
- 静态资源: `?v=0.0.1` 版本令牌（随迭代递增）
- **不能**用 `<meta>` 标签代替真实 HTTP 响应头

## 预置账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员 |
| demo | demo123 | 普通用户 |

## Aliyun systemd 与 Nginx

服务名: `codingagent-contract-mgmt-v2`
部署根目录: `/srv/codingagent/contract-mgmt-v2/`
端口: 19051

## 日志查看

Flask 开发服务器日志直接输出到 stdout/stderr。
生产环境使用 systemd journal: `journalctl -u codingagent-contract-mgmt-v2 -f`

## 常见故障与恢复

| 问题 | 解决 |
|------|------|
| 端口占用 | `lsof -ti:19051 \| xargs kill` |
| 数据库损坏 | 删除 `data/app.db`，重新运行 `python init_db.py` |
| 附件丢失 | 备份 `uploads/` 目录，定期同步 |

## 回滚

Git tag 策略待后续迭代建立。当前通过 `git checkout` 回到目标 commit。
