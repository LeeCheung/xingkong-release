# 星空媒体用户 API 参考

## 总览

用户给的 11 个 `https://www.xingkongmt.com/user/api/xxx` 链接是**接口文档页面**（需登录 + `CusUser.apiAuth`），不是能返回 JSON 的接口。真正可调用的接口在：

- **Base URL**：`https://wx.xingkongmt.com/api/userkey`
- **方法**：全部 `POST`
- **鉴权**：请求体里带 `accessKey` + `secretKey`，不走 session
- **必带请求头**：浏览器 `User-Agent` + `Referer: https://wx.xingkongmt.com/`（`scripts/xk_api.py` 已内置；实测不带会被 nginx 返回 403）
- **代理**：本机环境有 `HTTP_PROXY` 劫持，必须绕过（`xk_api.py` 已用 `ProxyHandler({})` 禁用代理）

> 生产接口的实现在另一仓库 `xksuper-editorv3` 的 `ApiController.js`（本地路径 `D:/bitProject/xksuper-editorv3`），文档页在 `xksuper-pc` 的 `views/api/*.ejs`。生产版本比本地代码新，个别字段以本文件「实测」为准。

## 状态码

| code | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 无效的 accessKey / secretKey（部分接口带 `apiCode:101`） |
| 3 | 用户不存在 |
| 4 | 数据库错误 |
| 5 | 参数错误 |
| 11 | 系统错误 |
| 19 | 余额不足（payRelease） |
| 22 | 权限错误（如 allInfo 传了不属于本 key 的 autoId） |
| 103 | 媒体不存在/已暂停，或触犯违禁词 |
| 102 | 代理商无客户权限 |

金额单位均为**人民币元**。`autoId` 是 17~19 位数字字符串（稿件/订单号）。

## 接口逐项

### money — 账户余额（只读）
`POST /money`，参数：仅 AK/SK。
返回：`{"code":0,"msg":"获取数据成功","user":{"money":92,"gift":50,"disCount":10}}`
- `money` 余额、`gift` 红包（支付时默认抵扣）、`disCount` 星空会员次数。
- 实测返回的是**数字**，文档示例写字符串，按数字处理。

### mediaClass — 媒体分类全表（只读）
`POST /mediaClass`，参数：仅 AK/SK。
返回：`{"code":0,"mediaClassMenu":{...}}`，含 7 大类：
`wzmt`网站媒体、`zmt`自媒体、`wx`微信、`wb`微博、`sVideo`短视频、`overseas`海外、`other`其它。
每类是 `{分类type: [{id, name}, ...]}`。用于把分类名映射到 id，配合 mediaList 的 `params`。

### mediaList — 媒体列表（只读）
`POST /mediaList`，参数：
- `page`（默认 1）
- `mediaType`：`2`网站媒体（默认）、`1009`自媒体、`2219`微信公众号、`2220`微博、`2125`短视频、`2392`海外、`2207`其它
- `params`：数组，按媒体类型的分类维度顺序传分类 id，`0`=不限。例网站媒体：`[industryType, portal, attribute, area, entryLevel, link, newsSource, geo]`
- `price`：`0-20 / 20-100 / 100-500 / 500-1000 / 1000-5000 / 5000-`
- `follower`：`0-5000 / 5000-10000 / 10000-50000 / 50000-100000 / 100000-`
- `sort`：`0`默认、`3`权重降序、`4`价格降序、`5`价格升序
- `keyWord`：媒体名关键词

返回：
```
{"code":0,"mediaArr":[{id, mediaName, price, isDiscount, vipPrice, mediaType,
  mediaTypeStr, industryTypeStr, portalStr, entryLevelStr, linkStr, newsSourceStr,
  geoStr, attributeStr, area, case, baiduWeight, webRecordRate, newsRecordRate,
  hour, subscriptions, note}, ...],
 "totolCount": 总数, "totalPage": 总页数}
```
- ⚠️ 字段拼写是 **`totolCount`**（源码如此），不是 totalCount，文档写的是 totalCount。
- `id` 是选媒体时要用的媒体数字 id；`price` 是刊例价；`isDiscount=1` 表示可用会员折扣。
- 分页大小：文档写 `pageSize` 可选（30/50/100/200），但本地实现未读取该参数；**实测每页返回 30 条**（2026-11-19，mediaType=2 返回 30 条、`totolCount=16153`）。不要依赖 pageSize 生效，按实际返回的 `mediaArr.length` 处理。

### releaselist — 发稿记录（只读）
`POST /releaseList`，参数：`page`（默认"1"）、`autoId`（可选数组，按订单号筛）。
返回：
```
{"code":0,"releases":[{id, autoId, title, state, stateStr, requirements,
   requirementsStr, createdAt, releaseTime}, ...],
 "releaseMediaObj": {"<release.id>": {totalMoney, rmArr:[{id, mediaName,
   priceIndex, mediaPrice, realMediaPrice, mediaTypeStr, releaseTime, link,
   linkAt, mState, refuseMsg}, ...]}},
 "page", "totalPage", "totalCount"}
```
- `state`：`0`选择媒体、`1`等待付款、`2`已付款、`3`发布完成、`10`订单关闭。
- `requirements`：`0`可适当修改、`1`按原稿不改、`3`不能带联系方式、`4`不能带全部图片。

### allInfo — 稿件及媒体全部信息（只读）
`POST /allInfo`，参数：`autoId`（必填，且必须属于本 key 的用户）。
返回：`{"code":0,"release":{autoId,title,state,stateStr,createdAt,requirements,requirementsStr,releaseTime,note,totalMoney},"mediaArr":[{id,mediaType,mediaTypeStr,mediaName,realMediaPrice,priceIndex,mediaPrice,createdAt,case,releaseTime,mState,link,linkAt,refuseMsg,note,releasePayType},...]}`
- 传无效/不属于本 key 的 autoId 返回 `{"code":22,"msg":"权限错误"}`。
- **支付前用它核对媒体清单与 totalMoney。**

### rechargelist — 交易记录（只读）
`POST /rechargelist`（全小写），参数：`page`。
返回：`{"code":0,"recharges":[{no, money, note, id, createdAt, state, type},...], "totalPage", "totalCount"}`
- `type`：充值/在线退款/结余发票等；`money` 可能带 `+` 前缀（如 `"+1"`）。
- 本地 editorv3 代码里找不到该 action，但**生产实测可用**，以生产为准。

### confirmMedia — 发稿第一步：选媒体建单（写）
`POST /confirmMedia`，参数：
- `selectMedias`（必填）：`[{"media": 媒体id, "priceIndex": 1}, ...]`，`priceIndex` 只能为 1
- `autoId`（可选）：传已有稿件 autoId 则复用，否则新建

返回：`{"code":0,"autoId":"...","msg":"获取数据成功"}` —— 这个 autoId 是后续所有步骤的钥匙。
副作用：创建/复用 Release（state=1 待付款），写入未付款媒体。**空数组返回 code:5。**

### parseDocx — 上传解析 docx（写，但不扣款）
`POST /parseDocx`，`multipart/form-data`，文件字段名 **`file`**，另带 AK/SK。限 .docx、≤10MB。
返回：`{"code":0,"html":"<p>...</p>","msg":"文件上传成功"}`；非 docx 返回 `{"code":2,"msg":"不支持的文件，请使用标准的docx文件！"}`。
- 已知缺陷：docx 内嵌图片时因实现里 `userResult` 未定义会报错；**纯文字 docx 不受影响**。

### create — 发稿第二步：提交稿件内容（写）
`POST /create`，参数：`autoId`（必填）、`title`（必填）、`content`（必填，HTML；通常来自 parseDocx 的 html）、`note`（选填，来源链接）。
返回：`{"code":0,"autoId":"..."}`。
副作用：更新 Release 的标题/内容。会做违禁词过滤（命中 code:103）、过滤非法 script。

### confirmRelease → 真实端点 payRelease — 发稿第三步：支付（**真实扣款**）
`POST /payRelease`（注意不是 /confirmRelease），参数：
- `autoId`（必填）
- `requirements`（选填，默认 0）：`0`可适当修改 / `1`按原稿不改 / `3`不能带联系方式 / `4`不能带全部图片
- `releaseTime`（选填，默认当天）：提交审核日期，必须 ≥ 今天，格式 `YYYY-MM-DD`
- `discount`（文档列了，但本地实现未读取，实测前不要依赖）

返回：`{"code":0,"msg":"获取数据成功"}`；余额不足 `code:19`；无未付款媒体 `code:5`。
副作用（**不可逆**）：扣减余额与红包、生成扣款 Recharge 记录、订单转已付款、媒体转已付款并触发自动发稿。

### delMedia — 删除未付款媒体（写）
`POST /deleteMedia`，参数：`autoId`（必填）、`mId`（媒体 id，必填）。
返回：`{"code":0}`。只能删未付款媒体，已付款的删不掉。

## 标准发稿流程

```
1. money            → 确认余额够不够
2. mediaClass       → 拿到分类 id（可选，已知媒体 id 可跳过）
3. medialist        → 检索媒体，记下选中的 id 与 price
4. confirmMedia     → selectMedias=[{media:id,priceIndex:1}]  → 得到 autoId
5. parseDocx        → （稿件来自 docx 时）得到 html
6. create           → autoId + title + content
7. allInfo          → 核对媒体清单、totalMoney  ← 到此为止，向用户报告并等待确认
8. payRelease       → 仅在用户明确确认支付后调用
```
任意时刻可用 `delMedia(autoId, mId)` 从待付款订单里剔除媒体。
