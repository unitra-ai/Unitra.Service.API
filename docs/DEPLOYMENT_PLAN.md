# Unitra Service.API - Dokploy 部署计划

> 记录于: 2025-12-21
> 状态: 待执行 (当需要服务器时)

## 项目概述

Unitra 翻译平台 FastAPI 后端服务的部署规划，使用 Dokploy 自托管 PaaS + DigitalOcean。

## 已完成的工作

- [x] W1-S01: FastAPI 项目初始化
- [x] W1-S02: 数据库 Schema 设计 (User, Subscription, UsageLog, RefreshToken)
- [x] W1-S03: API Gateway 核心 (异常处理, 中间件, 依赖注入)
- [x] W1-S04: 健康检查 & 结构化日志 (structlog)
- [x] W1-X01: CI/CD Pipeline (GitHub Actions)

## CI/CD 配置 (已完成)

文件位置: `.github/workflows/`

| 文件 | 用途 |
|------|------|
| `ci.yml` | PR 检查 (lint, test, build, security) |
| `deploy-staging.yml` | 自动部署到 Staging (push to main) |
| `deploy-prod.yml` | 手动审批部署到 Production (release) |

---

## 待办: Dokploy + DigitalOcean 部署

### Step 1: 创建 DigitalOcean Droplet

1. 登录 [DigitalOcean](https://cloud.digitalocean.com)
2. Create → Droplets
3. 配置:

| 设置 | 值 |
|------|-----|
| Region | Singapore (sgp1) |
| Image | Ubuntu 22.04 LTS |
| Size | $24/月 (2 vCPU, 4GB RAM, 80GB SSD) |
| Authentication | SSH Key |
| Hostname | `dokploy-unitra` |

4. 记录 IP 地址

---

### Step 2: 安装 Dokploy

```bash
ssh root@<IP地址>
curl -sSL https://dokploy.com/install.sh | sh
```

安装完成后访问: `http://<IP>:3000`

---

### Step 3: 配置 DNS

在域名 DNS 管理中添加 A 记录:

| Type | Name | Value |
|------|------|-------|
| A | `dokploy` | `<IP地址>` |
| A | `api` | `<IP地址>` |
| A | `staging-api` | `<IP地址>` |

---

### Step 4: 在 Dokploy 创建服务

#### 4.1 创建项目
- Projects → Create Project → 命名 `unitra`

#### 4.2 创建 PostgreSQL
- Add Service → Database → PostgreSQL
- Name: `postgres`, Version: `16`
- 复制连接字符串

#### 4.3 创建 Redis
- Add Service → Database → Redis
- Name: `redis`, Version: `7`
- 复制连接字符串

#### 4.4 创建 API 应用
- Add Service → Application
- Name: `unitra-api`
- Source: Docker Image
- Image: `ghcr.io/unitra-ai/unitra.service.api:staging`

---

### Step 5: 配置环境变量

在应用的 Environment 标签添加:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:xxx@postgres:5432/postgres

# Redis
REDIS_URL=redis://redis:6379/0

# Application
SECRET_KEY=<运行: openssl rand -hex 32>
ENVIRONMENT=staging
DEBUG=false

# Stripe (可选)
STRIPE_API_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
```

---

### Step 6: 配置域名和 SSL

1. 应用 → Domains 标签
2. 添加: `staging-api.yourdomain.com`
3. 勾选 Enable HTTPS
4. 保存

---

### Step 7: 获取 Webhook URL

1. 应用设置 → Webhooks
2. Generate Webhook
3. 复制 URL (格式: `https://dokploy.xxx/api/webhook/xxxx`)

---

### Step 8: GitHub 配置

#### Secrets (Repository → Settings → Secrets)

| Name | Value |
|------|-------|
| `DOKPLOY_WEBHOOK_URL` | Staging Webhook URL |
| `DOKPLOY_WEBHOOK_URL_PROD` | Production Webhook URL |

#### Variables (Repository → Settings → Variables)

| Name | Value |
|------|-------|
| `STAGING_API_URL` | `https://staging-api.yourdomain.com` |
| `PRODUCTION_API_URL` | `https://api.yourdomain.com` |

---

### Step 9: 配置 GHCR 访问

1. 创建 GitHub Personal Access Token:
   - GitHub → Settings → Developer settings → Personal access tokens
   - 勾选 `read:packages`

2. 在 Dokploy 配置:
   - Settings → Docker Registry → Add
   - URL: `ghcr.io`
   - Username: GitHub 用户名
   - Password: PAT token

---

## 费用估算

| 项目 | 月费用 |
|------|--------|
| DigitalOcean Droplet (2vCPU/4GB) | $24 |
| 域名 | ~$1 |
| **总计** | **~$25/月** |

对比 Railway ($40-50/月)，**节省约 50%**

---

## 验证部署

```bash
# 健康检查
curl https://staging-api.yourdomain.com/api/health

# 版本信息
curl https://staging-api.yourdomain.com/api/version

# 存活探针
curl https://staging-api.yourdomain.com/api/health/live
```

预期返回:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "staging",
  "components": {
    "database": {"status": "healthy", "latency_ms": 1.23},
    "redis": {"status": "healthy", "latency_ms": 0.45}
  }
}
```

---

## 生产环境

重复 Step 4-7，创建独立的生产服务:
- 应用名: `unitra-api-prod`
- 域名: `api.yourdomain.com`
- 使用 `DOKPLOY_WEBHOOK_URL_PROD`
