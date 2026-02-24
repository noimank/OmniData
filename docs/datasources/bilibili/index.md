# Bilibili

Bilibili 视频平台数据接口。

---

## 接口概览

该平台接口需要登录后使用。

[![二维码登录](https://img.shields.io/badge/登录支持-orange)](javascript:)

---

## 特点

- 部分接口需要登录
- 支持高清视频信息获取

---

## 登录支持

使用 Bilibili 二维码登录：

```bash
# 启动登录
curl -X POST http://localhost:8380/logins/start \
  -H "Content-Type: application/json" \
  -d '{"login_name": "bilibili"}'

# 获取二维码后，使用 Bilibili App 扫码登录
```
