---
name: home-assistant-smart-home
description: "全屋智能接入 Home Assistant 完整流程 — 部署、设备接入、App 逆向、仪表盘布局、AI 助手接管。触发：搭建智能家居/HA 接入设备/仪表盘优化。"
category: devops
---

# 全屋智能接入 Home Assistant（完整实战流程）

把家里各品牌的智能设备统一接入 Home Assistant（HA），并在手机上用一个界面 + 一个 AI 助手控制全屋。本文档来自真实部署经验，覆盖从零到全部设备接入再到 AI 接管的完整链路。

**适用读者**：有 NAS/服务器可以跑 Docker 的用户；设备跨多个品牌（米家/海尔/美的/石头/万和等）需要统一控制的用户。

## 总体架构

```
手机 App / AI 助手
    ↓ WebSocket / REST API
Home Assistant（Docker 容器）
    ↓ 各品牌集成
小米净化器 / 海尔冰箱 / 美的洗衣机 / 石头扫地机 / 万和热水器 / 路由器 / NAS ...
```

## 一、部署 HA

### 1.1 容器部署

- 用 **host 网络**跑容器，端口直通，避免端口映射麻烦：
```bash
docker run -d --name homeassistant --network host --privileged \
  -v /path/to/config:/config -v /path/to/data:/data \
  -v /etc/localtime:/etc/localtime:ro -v /run/dbus:/run/dbus:ro \
  -e TZ=Asia/Shanghai --restart unless-stopped \
  lscr.io/linuxserver/homeassistant:latest
```

### 1.2 镜像拉取坑（国内环境必看）

- 症状：官方源/daocloud/1ms.run 拉大镜像报 `invalid tar header: ApplyLayer failed`
- 诊断：**先拉一个极小镜像（alpine）验证存储层**——alpine 成功说明不是磁盘坏，是源对特定大镜像的同步层坏了
- 解法：换 **lscr.io**（linuxserver 构建版），一次成功
- ⚠️ 别把 invalid tar header 误判成硬盘故障去格式化

### 1.3 NAS 防火墙（群晖等）

- 群晖防火墙开启时，`INPUT_FIREWALL` 链末尾有 DROP，非白名单端口全丢
- 光在 DSM 界面加规则不够，必须：
  1. `iptables -I INPUT_FIREWALL 3 -p tcp -m multiport --dports 8123 -j RETURN`（插到 DROP 前）
  2. 写进防火墙 JSON 配置（否则防火墙 reload 清掉手工规则）
  3. 加开机自启脚本双保险

### 1.4 外网访问（Cloudflare Tunnel）

- 配置 `~/.cloudflared/config.yml` ingress：`ha.your-domain.com → http://<nas-ip>:8123`
- **反向代理 400 Bad Request 坑**：HA 新版把 http 配置迁移到 `.storage/http` 文件，configuration.yaml 里的 `http:` 块被忽略！必须直接改 storage 文件：
```python
# .storage/http
stable['use_x_forwarded_for'] = True
stable['trusted_proxies'] = ["127.0.0.1", "172.16.0.0/12", "10.0.0.0/8", "192.168.0.0/16"]
```
- 诊断：错误消息 `not set-up for reverse proxies` = use_x_forwarded_for 没读到；`untrusted proxy` = 源 IP 不在 trusted_proxies

## 二、设备接入（多品牌实战）

### 2.1 米家设备（净化器/净水器/空调伴侣）

- 官方 Xiaomi Home 集成登录常失败 → 用 **xiaomi_miot_auto**（HACS 第三方）
- 登录用**米家 App 绑定的手机号**（不是小米商城邮箱），地区选**中国**，推荐扫码
- 添加后注意检查是否产生重复卡片（同账号重复添加会实体重复）

### 2.2 海尔冰箱（国区账号鸿沟）

- hOn 集成只支持**海外账号**（固定连海外服务器），国区海尔智家账号登不上——不是密码问题
- 国区正解：**banto6/haier**（HACS 第三方），需要 client_id + refresh_token
- 抓包注意：海尔智家 **App 有 SSL Pinning**（Stream 只能抓到 CONNECT 隧道记录），要抓**微信小程序版**（WebView 无 Pinning）
- 进阶：有账号密码可直接调登录 API 换 token，免抓包；签名算法 `sha256(urlpath + body + appId + appKey + timestamp)`

### 2.3 美的/小天鹅洗衣机

- 用 **midea_ac_lan wuwentao fork v0.7.1**（旧版 georgezhao2010 在 HA 2026.8 报废弃常量错误）
- 配置时 server 选 **99 = Skip Login**，自动从局域网设备拿 token/key
- 最大的坑：**entry loaded 但 0 实体** = 实体默认全隐藏，必须走 options flow 提交 sensors/switches 数组才出现

### 2.4 石头扫地机

- HA 新版内置 Roborock 集成，扫码登录一次成功，最省心

### 2.5 路由器（爱快 iKuai）

- SPA 前端接口返回"会话已过期"是死路；**经典接口一直有效**：`POST /Action/login`，passwd 传 MD5、pass 传明文
- 装 HACS dscao/ikuai 即可

### 2.6 无现成集成的设备 → App 逆向（重头戏）

当某品牌没有现成集成（如万和热水器），且 App 抓包被 SSL Pinning 全堵死时，可以逆向 App：

1. **下载 APK**：APKPure 直链 `https://d.apkpure.com/b/XAPK/<package>?version=latest`（手机 UA）
2. **解包**：XAPK 解压；如果是 Ionic/Angular 混合 App，**业务逻辑在明文 JS 里**（assets/www/build/main.js），不用反编译 dex
3. **grep API 域名**：`grep -oE 'https?://[a-z0-9.-]+\.<brand>\.com' main.js` 直接拿全部 API 域名
4. **登录接口**：form-urlencoded POST 账号密码 → 拿 Uuid + Token + Domain（Domain 往往是 WebSocket 控制服务器地址）
5. **HTTP 控制可能是死路**：返回 200 但命令不生效 → 真正控制走 WebSocket 二进制协议
6. **WS 二进制帧**：`[OP码 1字节][长度 4字节大端][JSON]`，OP: LOGIN=0 / CONTROL=4 / HEARTBEAT=10 / 状态推送=34
7. **控制字段映射**：控制数组往往不是原始状态数组，而是**重排数组**（从 JS 的 updateStatus 映射函数里挖）
8. **写 HA 自定义集成**：`custom_components/<brand>/`，包含 config_flow + 平台实体（switch/number/sensor 等）

**单会话硬限制的解法**：厂商云如果按账号单会话（App 登录会踢掉 HA），用**家庭成员子账号**分离——手机 App 用主账号，HA 用家庭成员子账号登录，两个独立会话互不影响。

**⚠️ 运行期策略**：token 持久化到本地文件、运行期不主动重新登录（否则每次重连 login 都顶掉手机 App）、WS 收到错误码进入等待重配模式。

### 2.7 HA 2026.8 配置向导走 REST（新变化）

新版 HA **移除了 WebSocket 版 config_entries/flow 命令**（发 WS 报 unknown_command），创建集成只能走 REST：

```bash
# 创建 flow
curl -X POST -H "Authorization: Bearer $HA_TOKEN" \
  http://<nas-ip>:8123/api/config/config_entries/flow \
  -d '{"handler":"<integration-domain>"}'
# 提交表单 → {"type":"create_entry",...} = 成功
```

- 公网 POST 可能被 Cloudflare 拦（403 code 1010）→ 用 NAS 内网 IP
- ⚠️ 探测公网连通性用 curl 不用 Python urllib（CF 按 UA 拦 urllib 会返回假 403）

## 三、仪表盘布局

### 3.1 sections 布局

新版 HA 仪表盘默认 sections 布局：**一个区块一台设备**，卡片自动网格排列，手机上滑一屏看全屋。

经验：
- 每台设备挑 3-5 个最常用实体放区块，不要全塞
- 控制都在卡片上直接操作，不进详情页

### 3.2 卡片选择

| 设备类型 | 推荐卡片 | 说明 |
|---|---|---|
| 空调/温控 | **thermostat** | 开关、温度环、模式、风速全在一张卡上 |
| 扫地机 | tile 主卡 + "开始清洁"/"回充"按钮 | 按钮绑 vacuum.start / vacuum.return_to_base 服务 |
| 净化器 | tile + fan-preset-modes feature | 风速档位拉出来按钮组 |
| 开关/传感器 | tile | 最通用 |

- ⚠️ 老教程的 `climate` 卡片类型在新版已移除，配了报配置错误，用 `thermostat`
- tile 卡片对 climate 实体点击固定进详情页，空调要用专用卡片

### 3.3 设备改名

集成接入的设备名是英文/怪名字（zhimi_v6_437c 这种），在 设置 → 设备和服务 → 找到设备 → 改中文名，全系统生效（仪表盘/通知/语音控制）。

### 3.4 手机 App 连接坑

- 症状：HA App 连公网域名，隔一会儿提示"您已断开连接"，点重试能连上，过两分钟又断
- 根因：HA App 靠 WebSocket 长连接推状态，走 Cloudflare 隧道时 **CF 边缘约 100 秒空闲就掐断连接**
- 解法：App → 设置 → 连接 → **内部地址填内网 IP**（`http://<nas-ip>:8123`），在家连 Wi-Fi 直连 NAS 不走公网，永不掉线；外出才走公网域名

## 四、AI 助手接管

### 4.1 REST API 控制

```bash
# 查全部设备状态
curl -H "Authorization: Bearer $HA_TOKEN" http://<nas-ip>:8123/api/states

# 控制设备
curl -X POST -H "Authorization: Bearer $HA_TOKEN" \
  http://<nas-ip>:8123/api/services/switch/turn_on \
  -d '{"entity_id":"switch.xxx_power"}'
```

### 4.2 让 AI Agent 代劳一切

真正的懒人玩法：**整个部署、接入、调仪表盘的过程都可以交给 AI Agent 做**（如 Hermes Agent）：

- 它 SSH 进 NAS 改防火墙、改配置、重启容器
- 它下载 APK 逆向、破解协议、写自定义集成
- 它调 HA API 读全部实体、自动分组排版仪表盘
- 你只需要说"我要什么结果"，它负责"怎么做"

分工原则：**大方向你定（方案选择/账号决策），细节它执行**。关键决策点它停下来让你选，其余全自动。

## 排障速查

| 症状 | 根因 | 处理 |
|---|---|---|
| pull 报 invalid tar header | 源对大镜像同步损坏 | 拉 alpine 验证 → 换 lscr.io |
| 外网 https 400 Bad Request | HA 未配置反向代理信任 | 改 `.storage/http` 加 use_x_forwarded_for + trusted_proxies |
| 手机 App 反复"您已断开连接" | CF 边缘掐 WebSocket 长连接 | App 设内部地址内网 IP |
| 点集成报 Invalid handler | config_flow 导入失败（旧常量/类型被删） | 看 docker logs 真实报错，修 import 或换新 fork |
| 集成 entry loaded 但 0 实体 | 实体默认全隐藏 | options flow 提交实体数组 |
| App 有 SSL Pinning 抓不了包 | 证书校验 | 换同品牌小程序（WebView 无 Pinning）；或 APK 逆向 |
| 自定义集成换账号报 no_devices | config_flow 加载旧 token 文件 | 删 token 文件再重建 flow |

## 关键要点

1. 先想清楚要接哪些设备，查清楚有没有现成方案，再决定是否入坑
2. 智能家居的瓶颈从来不是硬件，是生态——每家一个 App、账号体系互不相通
3. 第三方集成优先选活跃 fork，旧版常与新版 HA 不兼容
4. 厂商 App 逆向优先看 JS（混合 App），不用反编译字节码
5. 单会话限制用子账号分离解决
6. 所有自动化配置都可通过 HA REST API 完成，可全自动脚本化
