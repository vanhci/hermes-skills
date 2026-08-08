# 部署细节

## 1. 容器部署

用 **host 网络**跑容器，端口直通，避免端口映射麻烦：

```bash
docker run -d --name homeassistant --network host --privileged \
  -v /path/to/config:/config -v /path/to/data:/data \
  -v /etc/localtime:/etc/localtime:ro -v /run/dbus:/run/dbus:ro \
  -e TZ=Asia/Shanghai --restart unless-stopped \
  lscr.io/linuxserver/homeassistant:latest
```

## 2. 镜像拉取坑（国内环境必看）

- 症状：官方源/daocloud/1ms.run 拉大镜像报 `invalid tar header: ApplyLayer failed`
- 诊断：**先拉一个极小镜像（alpine）验证存储层**——alpine 成功说明不是磁盘坏，是源对特定大镜像的同步层坏了
- 解法：换 **lscr.io**（linuxserver 构建版），一次成功
- ⚠️ 别把 invalid tar header 误判成硬盘故障去格式化

## 3. NAS 防火墙（群晖等）

- 群晖防火墙开启时，`INPUT_FIREWALL` 链末尾有 DROP，非白名单端口全丢
- 光在 DSM 界面加规则不够，必须：
  1. `iptables -I INPUT_FIREWALL 3 -p tcp -m multiport --dports 8123 -j RETURN`（插到 DROP 前）
  2. 写进防火墙 JSON 配置（否则防火墙 reload 清掉手工规则）
  3. 加开机自启脚本双保险

## 4. 外网访问（Cloudflare Tunnel）

- 配置 `~/.cloudflared/config.yml` ingress：`ha.your-domain.com → http://<nas-ip>:8123`
- **反向代理 400 Bad Request 坑**：HA 新版把 http 配置迁移到 `.storage/http` 文件，configuration.yaml 里的 `http:` 块被忽略！必须直接改 storage 文件：

```python
# .storage/http
stable['use_x_forwarded_for'] = True
stable['trusted_proxies'] = ["127.0.0.1", "172.16.0.0/12", "10.0.0.0/8", "192.168.0.0/16"]
```

- 诊断：错误消息 `not set-up for reverse proxies` = use_x_forwarded_for 没读到；`untrusted proxy` = 源 IP 不在 trusted_proxies

## 5. 手机 App 连接坑

- 症状：HA App 连公网域名，隔一会儿提示"您已断开连接"，点重试能连上，过两分钟又断
- 根因：HA App 靠 WebSocket 长连接推状态，走 Cloudflare 隧道时 **CF 边缘约 100 秒空闲就掐断连接**
- 解法：App → 设置 → 连接 → **内部地址填内网 IP**（`http://<nas-ip>:8123`），在家连 Wi-Fi 直连 NAS 不走公网，永不掉线；外出才走公网域名
