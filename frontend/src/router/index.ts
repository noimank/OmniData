import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: 'API KEY 登录' }
  },
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
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 导航守卫
router.beforeEach(async (to, _from, next) => {
  // 设置页面标题
  document.title = `${to.meta.title || 'OmniData'} - 管理平台`

  // 如果是登录页，直接放行
  if (to.path === '/login') {
    next()
    return
  }

  // 检查认证状态
  const authStore = useAuthStore()

  // 检查是否已认证
  const savedKey = localStorage.getItem('x-api-key')
  if (savedKey) {
    // 有保存的 API KEY，尝试验证
    const valid = await authStore.verifyApiKey(savedKey)
    if (valid) {
      next()
      return
    }
  }

  // 没有保存的 KEY 或验证失败，检查是否需要 API KEY
  const required = await authStore.checkRequired()
  if (required) {
    // 需要认证，跳转到登录页
    next('/login')
  } else {
    // 不需要认证，直接进入
    next()
  }
})

export default router
