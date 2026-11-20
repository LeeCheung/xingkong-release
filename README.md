# 星空媒体发稿 Skill（xingkong-release）

基于星空媒体官方用户 API 的发稿技能，供 WorkBuddy 使用。

## 能力
- 查询：账户余额、媒体分类、媒体检索、发稿记录、交易记录、稿件详情
- 发稿：选媒体建单 → 提交稿件 → 核对费用 → 确认后支付

## 安全设计
- **不内置密钥**：AK/SK 由使用者通过环境变量 `XK_ACCESS_KEY` / `XK_SECRET_KEY` 提供，不写入任何文件
- **支付二次确认**：`payRelease` 为真实扣款接口，必须用户明确确认后才调用
- **写操作闸门**：写接口需显式开关，dry-run 只打印不发请求

## 安装
1. 下载本仓库（Clone 或 Download ZIP）
2. 将 `xingkong-release` 目录放入 `~/.workbuddy/skills/`
3. 重启 WorkBuddy 会话，即可通过自然语言触发

也可在 WorkBuddy「技能 → 添加技能 → 上传技能」中上传打包好的 ZIP。

## 使用示例
- 查一下星空媒体余额
- 找几个汽车类媒体
- 用星空媒体 API 发一篇稿，标题是《XXX》，选媒体 1422

## 文件结构
- `SKILL.md` — 技能定义与发稿流程
- `references/api_reference.md` — 11 个接口的完整参数/响应/状态码说明
- `scripts/xk_api.py` — 通用 API 客户端（含安全闸门）

## 注意
接口域名为 `wx.xingkongmt.com/api/userkey/*`；文档页 `www.xingkongmt.com/user/api/*` 不可直接当接口调用。
