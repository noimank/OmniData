import request from './request'
import type {
  VerifyApiKeyRequest,
  VerifyApiKeyResponse,
  AuthConfig
} from './types'

// 验证 API KEY
export const verifyApiKey = (data: VerifyApiKeyRequest) => {
  return request.post<VerifyApiKeyResponse>('/v1/auth/verify', data)
}

// 获取认证配置
export const getAuthConfig = () => {
  return request.get<AuthConfig>('/v1/auth/config')
}

// 获取系统信息（用于检测是否需要 API KEY）
export const getSystemInfo = () => {
  return request.get('/')
}
