#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""星空媒体用户 API 通用客户端。

密钥只从环境变量读取，脚本内不保存任何 AK/SK：
    XK_ACCESS_KEY / XK_SECRET_KEY
可选：XK_API_BASE 覆盖默认域名（默认 https://wx.xingkongmt.com/api/userkey）。

安全设计：
  - 只读接口（money/mediaclass/medialist/releaselist/rechargelist/allInfo）直接可调。
  - 写接口（confirmMedia/create/deleteMedia/payRelease）必须显式带 --i-know-this-writes。
  - payRelease 是真实扣款接口，还需要额外带 --confirm-pay 才会发出请求。
  - 未确认时写接口只打印"预演"信息，绝不发请求。

用法示例：
  python xk_api.py money
  python xk_api.py medialist --param mediaType=2 --param page=1 --param 'keyWord=汽车'
  python xk_api.py allInfo --param autoId=12345678901234567
  python xk_api.py confirmMedia --param 'selectMedias=[{"media":1422,"priceIndex":1}]' --i-know-this-writes
  python xk_api.py payRelease --param autoId=... --param requirements=0 --i-know-this-writes --confirm-pay
  python xk_api.py parseDocx --file /path/to/doc.docx --i-know-this-writes
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
import uuid

DEFAULT_BASE = "https://wx.xingkongmt.com/api/userkey"
# 实测：不带浏览器 UA + Referer 会被 nginx 403；必须带。
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# 接口端点映射（文档 URL 与 action 命名的坑都在这里对齐）
ENDPOINTS = {
    "money":         "money",
    "mediaclass":    "mediaClass",
    "medialist":     "mediaList",
    "releaselist":   "releaseList",
    "rechargelist":  "rechargelist",       # 注意：全小写，与文档一致
    "allInfo":       "allInfo",
    "confirmMedia":  "confirmMedia",
    "parseDocx":     "parseDocx",
    "create":        "create",
    "confirmRelease": "payRelease",        # 路径名 confirmRelease → 真实端点 payRelease
    "delMedia":      "deleteMedia",
}

# 只读 / 写入 / 扣款 分级
READ_ONLY = {"money", "mediaclass", "medialist", "releaselist", "rechargelist", "allInfo"}
PAY = {"confirmRelease"}


def parse_param(s):
    """把 key=value 解析成 (key, value)；value 尝试解析 JSON（数字/数组/对象）。"""
    if "=" not in s:
        raise ValueError("参数格式应为 key=value，收到: %s" % s)
    k, v = s.split("=", 1)
    try:
        v = json.loads(v)
    except Exception:
        pass  # 保持字符串
    return k, v


def build_opener():
    """绕过本机 HTTP_PROXY（环境里有劫持代理），禁用代理。"""
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def post_json(url, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", UA)
    req.add_header("Referer", "https://wx.xingkongmt.com/")
    resp = build_opener().open(req, timeout=30)
    return resp.read().decode("utf-8", "replace")


def post_file(url, payload, file_path):
    """parseDocx 走 multipart/form-data，文件字段名 file。"""
    boundary = "----xk" + uuid.uuid4().hex
    parts = []
    for k, v in payload.items():
        parts.append(
            ("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"
             % (boundary, k, v)).encode("utf-8")
        )
    with open(file_path, "rb") as f:
        data = f.read()
    filename = os.path.basename(file_path)
    parts.append(
        ("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"%s\"\r\n"
         "Content-Type: application/octet-stream\r\n\r\n" % (boundary, filename)).encode("utf-8")
    )
    parts.append(data)
    parts.append(("\r\n--%s--\r\n" % boundary).encode("utf-8"))
    body = b"".join(parts)
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "multipart/form-data; boundary=%s" % boundary)
    req.add_header("User-Agent", UA)
    req.add_header("Referer", "https://wx.xingkongmt.com/")
    resp = build_opener().open(req, timeout=60)
    return resp.read().decode("utf-8", "replace")


def main():
    ap = argparse.ArgumentParser(description="星空媒体用户 API 客户端")
    ap.add_argument("api", choices=sorted(ENDPOINTS.keys()), help="接口名（见 choices）")
    ap.add_argument("--param", action="append", default=[], help="业务参数 key=value，可重复")
    ap.add_argument("--file", help="parseDocx 的 docx 文件路径")
    ap.add_argument("--i-know-this-writes", action="store_true",
                    help="写接口必须带此开关，否则只预演不请求")
    ap.add_argument("--confirm-pay", action="store_true",
                    help="payRelease（真实扣款）必须再带此开关，否则拒绝")
    ap.add_argument("--dry-run", action="store_true", help="只打印将要发送的请求，不执行")
    args = ap.parse_args()

    ak = os.environ.get("XK_ACCESS_KEY", "")
    sk = os.environ.get("XK_SECRET_KEY", "")

    payload = {"accessKey": ak, "secretKey": sk}
    for p in args.param:
        k, v = parse_param(p)
        payload[k] = v

    base = os.environ.get("XK_API_BASE", DEFAULT_BASE).rstrip("/")
    url = base + "/" + ENDPOINTS[args.api]

    # 密钥检查（支付场景必须早失败）
    if not ak or not sk:
        print(json.dumps({"code": -1,
                          "msg": "缺少密钥：请设置环境变量 XK_ACCESS_KEY / XK_SECRET_KEY"},
                         ensure_ascii=False))
        sys.exit(2)

    # 写操作闸门
    if args.api not in READ_ONLY and not args.i_know_this_writes and not args.dry_run:
        print(json.dumps({"code": -2,
                          "msg": "写接口 %s 需要显式带 --i-know-this-writes；未发送任何请求" % args.api},
                         ensure_ascii=False))
        sys.exit(3)
    if args.api in PAY and not args.confirm_pay and not args.dry_run:
        print(json.dumps({"code": -3,
                          "msg": "payRelease 是真实扣款接口，需额外带 --confirm-pay；未发送任何请求"},
                         ensure_ascii=False))
        sys.exit(4)
    # 扣款必须给 autoId
    if args.api in PAY and not args.dry_run and not payload.get("autoId"):
        print(json.dumps({"code": -4, "msg": "payRelease 必须传 autoId"}, ensure_ascii=False))
        sys.exit(5)

    safe_payload = dict(payload)
    safe_payload["accessKey"] = ak[:4] + "****" + ak[-4:] if len(ak) > 8 else "****"
    safe_payload["secretKey"] = sk[:4] + "****" + sk[-4:] if len(sk) > 8 else "****"
    plan = {"api": args.api, "url": url, "method": "POST", "payload": safe_payload}
    if args.file:
        plan["file"] = args.file

    if args.dry_run:
        print(json.dumps({"dry_run": True, "request": plan}, ensure_ascii=False, indent=2))
        return

    try:
        if args.api == "parseDocx":
            if not args.file or not os.path.isfile(args.file):
                print(json.dumps({"code": -5, "msg": "parseDocx 需要 --file 指向存在的 docx"},
                                 ensure_ascii=False))
                sys.exit(6)
            raw = post_file(url, payload, args.file)
        else:
            raw = post_json(url, payload)
        # 输出原样 JSON，便于机器解析；同时保证是合法 JSON（失败时给出原始文本）
        try:
            parsed = json.loads(raw)
            print(json.dumps(parsed, ensure_ascii=False, indent=2))
        except Exception:
            print(json.dumps({"code": -99, "raw": raw[:2000]}, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"code": -100, "msg": "请求失败: %s" % e}, ensure_ascii=False))
        sys.exit(7)


if __name__ == "__main__":
    main()
