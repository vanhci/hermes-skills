# 厂商 App 逆向方法论

适用：某品牌没有现成 HA 集成，且 App 抓包被 SSL Pinning 全堵死（如万和热水器）。

## 标准流程

1. **下载 APK**：APKPure 直链 `https://d.apkpure.com/b/XAPK/<package>?version=latest`（手机 UA）
2. **解包**：XAPK 解压；如果是 Ionic/Angular 混合 App，**业务逻辑在明文 JS 里**（`assets/www/build/main.js`），不用反编译 dex
3. **grep API 域名**：`grep -oE 'https?://[a-z0-9.-]+\.<brand>\.com' main.js` 直接拿全部 API 域名
4. **登录接口**：form-urlencoded POST 账号密码 → 拿 Uuid + Token + Domain（Domain 往往是 WebSocket 控制服务器地址）
5. **HTTP 控制可能是死路**：返回 200 但命令不生效 → 真正控制走 WebSocket 二进制协议
6. **WS 二进制帧**：`[OP码 1字节][长度 4字节大端][JSON]`，OP: LOGIN=0 / CONTROL=4 / HEARTBEAT=10 / 状态推送=34
7. **控制字段映射**：控制数组往往不是原始状态数组，而是**重排数组**（从 JS 的 updateStatus 映射函数里挖）
8. **写 HA 自定义集成**：`custom_components/<brand>/`，包含 config_flow + 平台实体（switch/number/sensor 等）

## 单会话硬限制的解法

厂商云如果按账号单会话（App 登录会踢掉 HA），用**家庭成员子账号**分离——手机 App 用主账号，HA 用家庭成员子账号登录，两个独立会话互不影响。

## ⚠️ 运行期策略

- token 持久化到本地文件、运行期不主动重新登录（否则每次重连 login 都顶掉手机 App）
- WS 收到错误码进入等待重配模式
- 换账号报 no_devices → 删 token 文件再重建 flow
