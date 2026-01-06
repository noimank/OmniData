# OmniData 前端管理平台

基于 Vue 3.5 + Element Plus 2.13 的爬虫管理系统前端。

## 技术栈

- Vue 3.5 (Composition API + TypeScript)
- Vite 6.0
- Element Plus 2.13
- Vue Router 4.4
- Pinia 2.2
- Axios 1.7
- Sass (sass-embedded 1.81 - 现代 API)

## 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 开发模式

```bash
npm run dev
```

访问: http://localhost:3000

### 3. 构建生产版本

```bash
npm run build
```

构建产物在 `dist/` 目录

### 4. 预览生产构建

```bash
npm run preview
```

## 功能模块

| 路由 | 页面 | 功能 |
|------|------|------|
| `/login` | 登录页 | API KEY 可选认证 |
| `/monitor` | 系统监控 | 浏览器池、爬虫统计、系统资源 |
| `/login-manage` | 登录管理 | 二维码登录、状态管理 |
| `/spider` | 爬虫测试 | 动态表单、执行测试 |

## API KEY 认证（可选）

### 后端配置

在 `.env` 文件中添加：

```bash
OMNIDATA_AUTH__API_KEY=your-secret-api-key
```

### 认证流程

1. 前端自动检测后端是否配置了 API KEY
2. 如果配置了，跳转到登录页要求输入
3. 如果未配置，直接进入系统
4. 验证成功后，API KEY 存储在 localStorage

## 目录结构

```
frontend/
├── src/
│   ├── api/              # API 调用模块
│   │   ├── request.ts    # 类型安全的 axios 封装
│   │   ├── auth.ts       # 认证 API
│   │   ├── monitor.ts    # 监控 API
│   │   ├── logins.ts     # 登录管理 API
│   │   ├── spiders.ts    # 爬虫 API
│   │   └── types.ts      # 类型定义
│   ├── components/
│   │   └── Layout/       # 布局组件
│   ├── composables/      # 组合式函数
│   ├── router/           # 路由配置
│   ├── stores/           # Pinia 状态管理
│   │   ├── auth.ts       # 认证 store
│   │   ├── monitor.ts    # 监控 store
│   │   ├── login.ts      # 登录管理 store
│   │   └── spider.ts     # 爬虫 store
│   ├── styles/           # 全局样式
│   ├── views/            # 页面组件
│   ├── App.vue
│   └── main.ts
├── package.json
├── vite.config.ts
└── tsconfig.json
```

## 特性

- TypeScript 严格模式
- 响应式布局（左侧导航 + 右侧内容）
- 类型安全的 API 调用
- Pinia 状态管理
- 路由导航守卫
- 自动轮询（监控数据、登录状态）
- 动态表单（根据爬虫 schema 生成）

## 构建/开发检查清单

- [x] TypeScript 类型检查通过 (`vue-tsc --noEmit`)
- [x] 生产构建成功 (`npm run build`)
- [x] 使用现代 Sass API (Vite 6 + sass-embedded)
- [x] 无 ESLint 错误
- [x] 所有功能页面完成

## 常见问题

### Q: 如何修改 API 地址？

A: API 地址已硬编码为 `http://localhost:8380/api`，如需修改请编辑 `src/api/request.ts` 中的 `baseURL`

### Q: 如何禁用 API KEY 认证？

A: 不配置 `OMNIDATA_AUTH__API_KEY` 环境变量即可

### Q: 爬虫参数如何配置？

A: 爬虫参数根据 `params_model` 动态生成表单，在爬虫类的 Pydantic 模型中定义

## 部署

### 静态文件服务

构建后的 `dist/` 目录可以部署到任何静态文件服务器：

- Nginx
- Apache
- Vercel/Netlify
- 或使用 FastAPI 静态文件服务

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name omnidata.example.com;

    root /path/to/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://localhost:8380;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```
