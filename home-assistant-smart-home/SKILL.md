---
name: home-assistant-smart-home
description: "Use when 用户要搭建智能家居/HA 接入设备/优化仪表盘/AI 控制全屋。覆盖部署→多品牌接入→仪表盘→AI 接管全流程。"
category: devops
tags: [home-assistant, smart-home, nas, docker, integration]
---

# 全屋智能接入 Home Assistant（HA）

把家里跨品牌的智能设备统一接入 HA，一个界面 + 一个 AI 助手控制全屋。本技能是**执行手册**：按顺序做完即得结果。

## 触发条件

- 用户要部署 Home Assistant（NAS / 服务器 / 旧电脑）
- 用户要把某品牌设备接入 HA（米家/海尔/美的/石头/万和/爱快路由器等）
- 仪表盘布局/卡片配置出问题
- 要让 AI 助手通过 REST API 控制全屋设备

## 前置检查

1. ✅ 有能跑 Docker 的 NAS / 服务器（群晖 / Linux / 旧 PC 均可）
2. ✅ 确认目标设备品牌，先查有没有现成集成（HA 社区基本覆盖主流品牌）
3. ⚠️ 无现成集成的品牌（如万和热水器）才考虑 App 逆向——工作量最大，先确认值得
4. ⚠️ 国内网络：镜像源优先 lscr.io，官方源大镜像大概率拉不动

## 执行流程

### 第一步：部署（约 30 分钟）

1. 拉镜像：`docker pull lscr.io/linuxserver/homeassistant:latest`（国内源，详见 references/deployment.md）
2. host 网络跑容器，挂载 config/data/localtime/dbus
3. 群晖等带防火墙的 NAS：iptables 放行 8123（插到 DROP 前 + 写 JSON 持久化）
4. 外网访问：Cloudflare Tunnel 配 `ha.your-domain.com → http://<nas-ip>:8123`

**验证**：`curl http://<nas-ip>:8123` 返回 HA 页面；外网 https 打开不报 400。

### 第二步：接入设备（按品牌逐个来）

| 品牌 | 方案 | 关键坑 |
|---|---|---|
| 米家净化器/净水器/空调伴侣 | xiaomi_miot_auto（HACS） | 登录用米家手机号非商城邮箱；防重复实体 |
| 海尔冰箱 | banto6/haier（HACS） | 国区账号 hOn 登不上；需 client_id+refresh_token |
| 美的/小天鹅洗衣机 | midea_ac_lan wutao fork v0.7.1 | 0 实体=默认全隐藏，走 options flow |
| 石头扫地机 | HA 内置 Roborock | 扫码登录一次成功 |
| 爱快路由器 | HACS dscao/ikuai | 经典接口 login 有效，SPA 接口死路 |
| 万和热水器（无现成集成） | App 逆向 + 自写集成 | 见 references/app-reverse-engineering.md |

每个品牌详细步骤见 `references/device-integrations.md`。

**验证**：每接入一个品牌，设置 → 设备和服务 → 能看到该设备且实体可控制。

### 第三步：仪表盘布局（约 30 分钟）

1. 新版默认 sections 布局：一区块一设备，卡片自动网格
2. 每台设备挑 3-5 个最常用实体，不塞满
3. 卡片选型：空调=thermostat（type:climate 已移除）；扫地机=tile+按钮；净化器=tile+fan-preset-modes
4. 设备改中文名，全系统生效

详见 `references/dashboard.md`。

**验证**：手机 HA App 打开仪表盘，一屏看全屋，卡片上直接可操作。

### 第四步：AI 助手接管（可选）

1. HA 设置 → 长期访问令牌
2. REST API：`GET /api/states` 查状态、`POST /api/services/<domain>/<service>` 控制
3. 交给 AI Agent（如 Hermes）——部署/接入/调仪表盘全过程可代劳，你只定大方向

详见 `references/ai-control.md`。

## 排障速查（完整表见 references/troubleshooting.md）

| 症状 | 一句话根因 | 处理 |
|---|---|---|
| pull 报 invalid tar header | 源对大镜像同步损坏 | 拉 alpine 验证 → 换 lscr.io |
| 外网 https 400 Bad Request | HA 未信任反向代理 | 改 .storage/http 加 trusted_proxies |
| 手机 App 反复断开 | CF 边缘掐 WebSocket 长连接 | App 设内部地址内网 IP |
| 集成 entry loaded 但 0 实体 | 实体默认全隐藏 | options flow 提交实体数组 |
| App 有 SSL Pinning 抓不了包 | 证书校验 | 换同品牌小程序（WebView 无 Pinning）；或 APK 逆向 |

## 关键要点

1. 智能家居瓶颈是生态，不是硬件——每家一个 App 互不相通，HA 就是凿墙的
2. 第三方集成优先选活跃 fork，旧版常与新版 HA 不兼容
3. 混合 App 逆向优先挖 JS（assets/www/build/main.js），不用反编译字节码
4. 单会话硬限制用家庭成员子账号分离
5. 所有自动化/配置都能走 REST API 脚本化

## 参考资料

- `references/deployment.md` — 镜像源、防火墙、Tunnel 细节
- `references/device-integrations.md` — 各品牌接入分步
- `references/app-reverse-engineering.md` — 厂商 App 逆向方法论
- `references/dashboard.md` — sections 布局与卡片选型
- `references/ai-control.md` — REST API + AI Agent 接管
- `references/troubleshooting.md` — 完整排障表
