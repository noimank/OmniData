import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const apiKey = ref<string>(localStorage.getItem('x-api-key') || '')
  const isRequired = ref<boolean>(false)
  const isAuthenticated = ref<boolean>(false)

  // 检查是否需要 API KEY
  const checkRequired = async () => {
    try {
      const config = await api.getAuthConfig()
      isRequired.value = config.required
      return config.required
    } catch (error) {
      // 如果请求失败，默认不需要 API KEY
      isRequired.value = false
      return false
    }
  }

  // 验证 API KEY
  const verifyApiKey = async (key: string) => {
    try {
      const result = await api.verifyApiKey({ api_key: key })
      if (result.valid) {
        apiKey.value = key
        isAuthenticated.value = true
        localStorage.setItem('x-api-key', key)
        return true
      }
      return false
    } catch (error) {
      return false
    }
  }

  // 清除认证
  const clearAuth = () => {
    apiKey.value = ''
    isAuthenticated.value = false
    localStorage.removeItem('x-api-key')
  }

  // 检查登录状态
  const checkAuth = async () => {
    const savedKey = localStorage.getItem('x-api-key')
    if (savedKey) {
      const valid = await verifyApiKey(savedKey)
      if (valid) {
        isAuthenticated.value = true
        return true
      }
    }
    // 如果没有保存的 KEY 或验证失败，检查是否需要
    await checkRequired()
    return !isRequired.value
  }

  return {
    apiKey,
    isRequired,
    isAuthenticated,
    checkRequired,
    verifyApiKey,
    clearAuth,
    checkAuth
  }
})
