import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api/logins'
import type { LoginInfo, QrcodeResponse, LoginStatus } from '@/api/types'

export const useLoginStore = defineStore('login', () => {
  const logins = ref<LoginInfo[]>([])
  const currentLogin = ref<LoginInfo | null>(null)
  const qrcode = ref<QrcodeResponse | null>(null)
  const loginStatus = ref<LoginStatus | null>(null)
  const polling = ref<boolean>(false)
  const loading = ref<boolean>(false)

  // 获取登录器列表
  const fetchLogins = async () => {
    try {
      loading.value = true
      const response = await api.getLogins()
      if (response.data) {
        logins.value = response.data.logins
      }
    } catch (error) {
      console.error('Failed to fetch logins:', error)
    } finally {
      loading.value = false
    }
  }

  // 获取登录器详情
  const fetchLoginDetail = async (loginName: string) => {
    try {
      const response = await api.getLoginDetail(loginName)
      const detail = response.data
      if (detail) {
        const index = logins.value.findIndex((l) => l.name === loginName)
        if (index !== -1) {
          // 使用 Object.assign 保持引用不变，只更新属性
          Object.assign(logins.value[index], detail)
        }
        // 如果 currentLogin 指向的是同一个登录器，也需要更新
        if (currentLogin.value && currentLogin.value.name === loginName) {
          Object.assign(currentLogin.value, detail)
        }
      }
      return detail
    } catch (error) {
      console.error('Failed to fetch login detail:', error)
      return null
    }
  }

  // 获取二维码
  const fetchQrcode = async (loginName: string, qrType: string) => {
    try {
      loading.value = true
      const result = await api.getQrcode(loginName, { qr_type: qrType })
      qrcode.value = result
      return result
    } catch (error) {
      console.error('Failed to fetch qrcode:', error)
      return null
    } finally {
      loading.value = false
    }
  }

  // 开始轮询验证登录状态
  const startVerifyPolling = async (loginName: string) => {
    polling.value = true
    while (polling.value) {
      try {
        const status = await api.verifyLogin(loginName)
        loginStatus.value = status
        if (status.status === 'success' || status.status === 'failed') {
          polling.value = false
          break
        }
      } catch (error) {
        console.error('Failed to verify login:', error)
      }
      // 等待 2 秒后继续轮询
      await new Promise((resolve) => setTimeout(resolve, 2000))
    }
  }

  // 停止轮询
  const stopVerifyPolling = () => {
    polling.value = false
  }

  // 检查登录状态
  const checkStatus = async (loginName: string) => {
    try {
      const status = await api.checkLoginStatus(loginName)
      loginStatus.value = status
      return status
    } catch (error) {
      console.error('Failed to check login status:', error)
      return null
    }
  }

  // 清除登录状态
  const clearSession = async (loginName: string) => {
    try {
      await api.clearLoginSession(loginName)
      // 拦截器在 success=false 时会抛出异常，执行到这里说明成功
      loginStatus.value = null
      qrcode.value = null
      return true
    } catch (error) {
      console.error('Failed to clear login session:', error)
      return false
    }
  }

  // 清理二维码资源
  const cleanupQrcodeResources = async (loginName: string) => {
    try {
      await api.cleanupQrcodeResources(loginName)
      qrcode.value = null
      // 拦截器在 success=false 时会抛出异常，执行到这里说明成功
      return true
    } catch (error) {
      console.warn(`Failed to cleanup QR code resources for ${loginName}:`, error)
      qrcode.value = null
      return false
    }
  }

  // 设置当前登录器
  const setCurrentLogin = (login: LoginInfo | null) => {
    currentLogin.value = login
  }

  return {
    logins,
    currentLogin,
    qrcode,
    loginStatus,
    polling,
    loading,
    fetchLogins,
    fetchLoginDetail,
    fetchQrcode,
    startVerifyPolling,
    stopVerifyPolling,
    checkStatus,
    clearSession,
    cleanupQrcodeResources,
    setCurrentLogin
  }
})
