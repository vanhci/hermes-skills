# 各品牌设备接入分步

按品牌逐个来。每接入一个，验证一次（设置 → 设备和服务 → 能看到设备且实体可控制）。

## 米家设备（净化器/净水器/空调伴侣）

- 官方 Xiaomi Home 集成登录常失败 → 用 **xiaomi_miot_auto**（HACS 第三方）
- 登录用**米家 App 绑定的手机号**（不是小米商城邮箱），地区选**中国**，推荐扫码
- 添加后注意检查是否产生重复卡片（同账号重复添加会实体重复）

## 海尔冰箱（国区账号鸿沟）

- hOn 集成只支持**海外账号**（固定连海外服务器），国区海尔智家账号登不上——不是密码问题
- 国区正解：**banto6/haier**（HACS 第三方），需要 client_id + refresh_token
- 抓包注意：海尔智家 **App 有 SSL Pinning**（Stream 只能抓到 CONNECT 隧道记录），要抓**微信小程序版**（WebView 无 Pinning）
- 进阶：有账号密码可直接调登录 API 换 token，免抓包；签名算法 `sha256(urlpath + body + appId + appKey + timestamp)`

## 美的/小天鹅洗衣机

- 用 **midea_ac_lan wuwentao fork v0.7.1**（旧版 georgezhao2010 在 HA 2026.8 报废弃常量错误）
- 配置时 server 选 **99 = Skip Login**，自动从局域网设备拿 token/key
- 最大的坑：**entry loaded 但 0 实体** = 实体默认全隐藏，必须走 options flow 提交 sensors/switches 数组才出现

## 石头扫地机

- HA 新版内置 Roborock 集成，扫码登录一次成功，最省心

## 路由器（爱快 iKuai）

- SPA 前端接口返回"会话已过期"是死路；**经典接口一直有效**：`POST /Action/login`，passwd 传 MD5、pass 传明文
- 装 HACS dscao/ikuai 即可

## 无现成集成的设备 → App 逆向

当某品牌没有现成集成（如万和热水器），且 App 抓包被 SSL Pinning 全堵死时，逆向 App 的完整方法论见 `references/app-reverse-engineering.md`。核心结论：

- 混合 App（Ionic/Angular）业务逻辑在明文 JS 里，不用反编译 dex
- HTTP 控制可能是死路（返回 200 但不生效），真正控制走 WebSocket 二进制协议
- 单会话硬限制 → 家庭成员子账号分离
- 写自定义集成放 `custom_components/<brand>/`，含 config_flow + 平台实体

## HA 2026.8 配置向导走 REST（新变化）

新版 HA **移除了 WebSocket 版 config_entries/flow 命令**（发 WS 报 unknown_command），创建集成只能走 REST：

```bash
# 创建 flow
curl -X POST -H "Authorization: Bearer ***" \
  http://<nas-ip>:8123/api/config/config_entries/flow \
  -d '{"handler":"<integration-domain>"}'
# 提交表单 → {"type":"create_entry",...} = 成功
```

- 公网 POST 可能被 Cloudflare 拦（403 code 1010）→ 用 NAS 内网 IP
- ⚠️ 探测公网连通性用 curl 不用 Python urllib（CF 按 UA 拦 urllib 会返回假 403）
