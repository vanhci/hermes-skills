# Hermes Skills

我在使用 Hermes Agent（Nous Research 的 AI 助手）过程中沉淀的可复用技能集合。

> 🌐 **个人博客与实战专栏**：[vanhci.top](https://vanhci.top)  
> 🛠️ **免费纯前端私密工具箱**：[tools.vanhci.top](https://tools.vanhci.top)

每个目录是一个独立 skill，符合 Hermes Agent 的 skill 格式（SKILL.md + 可选 references/scripts），可直接放入 `~/.hermes/skills/<category>/` 使用。

## 技能列表

| Skill | 说明 | 对应实战长文 |
|-------|------|--------------|
| `home-assistant-smart-home` | 全屋智能接入 Home Assistant 完整流程：部署、多品牌设备接入、App 逆向、仪表盘布局、AI 助手接管 | [从七个 App 到一个界面](https://vanhci.top/blog/home-assistant-smart-home-guide.html) |
| `macos-printbridge` | Mac 打印桥：老打印机接入 CUPS + 公网打印页 + HA 面板整合。云打印服务停止后的低成本远程打印方案 | [佳能老打印机云打印复活记](https://vanhci.top/blog/printer-cloud-revival.html) |

## 使用方式

1. 克隆本仓库：`git clone git@github.com:vanhci/hermes-skills.git`
2. 把需要的 skill 目录复制到 `~/.hermes/skills/<category>/` 下
3. 重启 Hermes 或执行 `hermes skills reload` 即可加载

## 说明与规范

所有技能文档均来自真实项目实战，敏感信息已脱敏为占位符（`<nas-ip>`、`<your-domain>` 等）。
