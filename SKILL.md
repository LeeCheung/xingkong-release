---
name: xingkong-release
display_name: 星空媒体发稿
display_name_en: Xingkong Media Release
description: 通过星空媒体用户 API 查询余额/媒体/发稿记录，并完成发稿流程（选媒体建单→提交稿件→核对→支付）。当用户要求用星空媒体 API 发稿、查媒体、查余额、查交易/发稿记录，或提到 xingkongmt 的用户 API、AK/SK、autoId 时使用本技能。支付为真实扣款，必须用户二次确认。
description_zh: 星空媒体（www.xingkongmt.com）为企业和品牌提供网络媒体、微信大号、微博大号、GEO优化、社交媒体、自媒体、KOL等媒体营销,4A团队全程一对一服务,为企业策划品效合一的营销方案。
description_en: Xingkong Media (www.xingkongmt.com) provides media marketing services for enterprises and brands, including online media, WeChat official accounts, Weibo official accounts, GEO optimization, social media, We-Media, KOL, and more. Our 4A team provides one-on-one service throughout the entire process
version: 1.0.0
author: leecheung
examples_zh:
  - 查一下星空媒体余额
  - 找几个汽车类媒体
  - 用星空媒体 API 发一篇稿，标题是《XXX》，选媒体 1422
examples_en:
  - Check my Xingkong Media balance
  - Find some automotive media outlets
  - Publish an article via Xingkong Media API with media 1422
agent_created: true
---

# 星空媒体发稿 Skill

## 用途

封装星空媒体面向客户/代理商的用户 API（`https://wx.xingkongmt.com/api/userkey/*`），提供两类能力：

1. **查询**：账户余额、媒体分类、媒体检索、发稿记录、交易记录、稿件详情。
2. **发稿**：按标准流程完成选媒体建单、提交稿件内容、核对费用，最终（且仅在用户明确确认后）支付扣款。

## 铁律（不可绕过）

1. **密钥不落盘**：本技能不保存 AK/SK。每次使用前向用户索取，或让用户设置环境变量 `XK_ACCESS_KEY`、`XK_SECRET_KEY`。绝不把密钥写进任何文件、日志、回复或 git。
2. **支付必须二次确认**：`payRelease` 是真实扣款接口，会扣余额、发起发稿，不可逆。流程走到 `allInfo` 核对后必须停下，把媒体清单与金额清单报给用户，得到明确的"确认支付"才调用。任何模糊表述都不算确认。
3. **写操作显式授权**：`confirmMedia` / `create` / `deleteMedia` 会写数据库，调用前确认用户意图；脚本要求 `--i-know-this-writes` 开关。
4. **不凭记忆猜字段**：接口字段名有坑（`totolCount` 拼写、`confirmRelease` 路径实为 `payRelease`、`rechargelist` 全小写）。调用细节查 `references/api_reference.md`。

## 如何使用

### 1. 准备密钥

向用户索取 AK/SK 后，在本轮会话里用环境变量传给脚本（不要把值写进文件）：

```bash
export XK_ACCESS_KEY='<用户提供的AK>'
export XK_SECRET_KEY='<用户提供的SK>'
```

若用户明确表示"用环境变量"，则只读取已设置的环境变量，不再询问。

### 2. 调用接口

统一用 `scripts/xk_api.py`（路径：本技能目录下）。脚本已内置浏览器 UA、Referer、禁用代理，并做写操作与支付闸门。

```bash
SKILL=<本技能目录>

# 查询类（直接可调）
python "$SKILL/scripts/xk_api.py" money
python "$SKILL/scripts/xk_api.py" mediaclass
python "$SKILL/scripts/xk_api.py" medialist --param mediaType=2 --param page=1 --param 'keyWord=汽车'
python "$SKILL/scripts/xk_api.py" releaselist --param page=1
python "$SKILL/scripts/xk_api.py" rechargelist --param page=1
python "$SKILL/scripts/xk_api.py" allInfo --param autoId=12345678901234567

# 先看将要发什么（强烈建议写操作前先 dry-run）
python "$SKILL/scripts/xk_api.py" confirmMedia --param 'selectMedias=[{"media":1422,"priceIndex":1}]' --dry-run

# 写操作（需 --i-know-this-writes）
python "$SKILL/scripts/xk_api.py" confirmMedia --param 'selectMedias=[{"media":1422,"priceIndex":1}]' --i-know-this-writes
python "$SKILL/scripts/xk_api.py" create --param autoId=... --param title=... --param content='<html>' --i-know-this-writes
python "$SKILL/scripts/xk_api.py" delMedia --param autoId=... --param mId=... --i-know-this-writes

# docx 解析
python "$SKILL/scripts/xk_api.py" parseDocx --file /path/to/article.docx --i-know-this-writes

# 支付（真实扣款：需要双开关，缺一不可）
python "$SKILL/scripts/xk_api.py" confirmRelease --param autoId=... --i-know-this-writes --confirm-pay
```

参数用 `--param key=value`，可重复；value 会尝试按 JSON 解析（数字、数组、对象），解析失败按字符串。`--dry-run` 只打印脱敏后的请求，不发网络请求。

### 3. 标准发稿流程

严格按序执行：

1. `money` — 确认余额足够。
2. `mediaClass` — 取分类 id（用户只说媒体名时可跳过）。
3. `medialist` — 检索媒体，让用户确认选中的媒体 id 与价格。
4. `confirmMedia` — 传 `selectMedias=[{media:id,priceIndex:1}]`，拿到 `autoId`。
5. `parseDocx` — 稿件来自 docx 时解析出 HTML（纯文字 docx 可靠；含图片 docx 有已知缺陷，注意提醒用户）。
6. `create` — 传 `autoId` + `title` + `content`。
7. `allInfo` — **核对**：列出媒体清单、单价、`totalMoney`，与用户确认无误。
8. **停止并向用户报告费用清单，等待明确"确认支付"。**
9. 收到确认后，才调用 `confirmRelease`（即 payRelease）。

流程中可用 `delMedia(autoId, mId)` 剔除尚未付款的媒体。

### 4. 结果呈现

- 金额以人民币元呈现，保留两位小数；余额、红包、总费用分开列。
- 发稿记录用 `stateStr` / `requirementsStr` 展示中文状态，不要只报数字。
- 任何 `code != 0` 都停止流程，把 `msg` 原样告知用户，不要猜测或重试写入类接口。

## 参考资源

- `references/api_reference.md` — 11 个接口的完整参数、响应字段、状态码、字段名坑。**调用任何接口前先读它。**
- `scripts/xk_api.py` — 通用 API 客户端。密钥从环境变量读取；含 dry-run、写操作闸门、支付双确认闸门。

## 已知限制

- `mediaList` 的 `pageSize` 参数服务端不读取，实测每页返回 30 条；按实际 `mediaArr.length` 处理，不要假设 pageSize 生效。
- `parseDocx` 处理含图片 docx 会因服务端缺陷失败，纯文字可用。
- `discount` 参数文档有列但服务端未读取，不要向用户承诺会员折扣生效。
- 文档页 `www.xingkongmt.com/user/api/*` 需登录查看，不能直接当接口调用；接口一律走 `wx.xingkongmt.com/api/userkey/*`。
