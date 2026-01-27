import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/components/Layout/index.vue'),
    redirect: '/monitor',
    children: [
      {
        path: 'monitor',
        name: 'Monitor',
        component: () => import('@/views/Monitor.vue'),
        meta: { title: '系统监控', icon: 'Monitor' }
      },
      {
        path: 'login-manage',
        name: 'LoginManage',
        component: () => import('@/views/LoginManage.vue'),
        meta: { title: '登录管理', icon: 'User' }
      },
      {
        path: 'spider',
        name: 'SpiderTest',
        component: () => import('@/views/SpiderTest.vue'),
        meta: { title: '爬虫测试', icon: 'Setting' }
      },
      {
        path: 'mcp-manage',
        name: 'McpManage',
        component: () => import('@/views/McpManage.vue'),
        meta: { title: 'MCP 管理', icon: 'Connection' }
      },
      {
        path: 'spider-audit',
        name: 'SpiderAudit',
        component: () => import('@/views/SpiderAudit.vue'),
        meta: { title: '爬虫审计', icon: 'Document' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 导航守卫 - 设置页面标题
router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title || 'OmniData'} - 管理平台`
  next()
})

export default router
