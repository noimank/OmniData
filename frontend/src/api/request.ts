import axios, { type AxiosError, type AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'

const baseURL = '/api'

// 创建 axios 实例
const instance = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 响应拦截器
instance.interceptors.response.use(
  (response) => {
    // 处理统一响应格式
    const { success, message, data } = response.data

    // 如果 success 为 false，抛出错误
    if (!success) {
      ElMessage.error(message || '请求失败')
      return Promise.reject(new Error(message))
    }

    // 返回 data 部分
    return data
  },
  (error: AxiosError<any>) => {
    // 处理错误响应
    const message = error.response?.data?.message || error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(message)
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
