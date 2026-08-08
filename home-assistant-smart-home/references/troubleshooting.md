# 完整排障速查

| 症状 | 根因 | 处理 |
|---|---|---|
| pull 报 invalid tar header | 源对大镜像同步损坏 | 拉 alpine 验证 → 换 lscr.io |
| 外网 https 400 Bad Request | HA 未配置反向代理信任 | 改 `.storage/http` 加 use_x_forwarded_for + trusted_proxies |
| 手机 App 反复"您已断开连接" | CF 边缘掐 WebSocket 长连接 | App 设内部地址内网 IP |
| 点集成报 Invalid handler | config_flow 导入失败（旧常量/类型被删） | 看 docker logs 真实报错，修 import 或换新 fork |
| 集成 entry loaded 但 0 实体 | 实体默认全隐藏 | options flow 提交实体数组 |
| App 有 SSL Pinning 抓不了包 | 证书校验 | 换同品牌小程序（WebView 无 Pinning）；或 APK 逆向 |
| 自定义集成换账号报 no_devices | config_flow 加载旧 token 文件 | 删 token 文件再重建 flow |
| 公网 POST 403 code 1010 | Cloudflare 拦截 | 用 NAS 内网 IP 操作 |
| curl 正常但 urllib 假 403 | CF 按 UA 拦 urllib | 探测连通性用 curl 不用 urllib |
