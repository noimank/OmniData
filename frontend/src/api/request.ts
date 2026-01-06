import axios, { type AxiosError, type AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'

const baseURL = 'http://localhost:8380/api'

// 创建 axios 实例
const instance = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
instance.interceptors.request.use(
  (config) => {
    const apiKey = localStorage.getItem('x-api-key')
    if (apiKey) {
      config.headers.set('X-API-Key', apiKey)
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
instance.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error: AxiosError<any>) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(message)

    if (error.response?.status === 401) {
      // 清除认证信息
      localStorage.removeItem('x-api-key')

      // 避免重复跳转
      if (window.location.pathname !== '/login' && !window.location.pathname.startsWith('/login')) {
        // 延迟跳转，让错误消息先显示
        setTimeout(() => {
          window.location.href = '/login'
        }, 100)
      }
    }

    return Promise.reject(error)
  }
)

// 创建类型安全的请求方法
async function request<T = any>(config: AxiosRequestConfig): Promise<T> {
  return instance.request(config)
}

async function get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return instance.get(url, config)
}

async function post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
  return instance.post(url, data, config)
}

async function put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
  return instance.put(url, data, config)
}

async function del<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return instance.delete(url, config)
}

export default { request, get, post, put, delete: del }
