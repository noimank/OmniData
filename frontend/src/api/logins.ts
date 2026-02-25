import request from './request'
import type {
  LoginListResponse,
  LoginInfo,
  QrcodeRequest,
  QrcodeResponse,
  LoginStatus
} from './types'

// 列出所有登录器
export const getLogins = () => {
  return request.get<LoginListResponse>('/v1/logins')
}

// 获取登录器详情
export const getLoginDetail = (loginName: string) => {
  return request.get<LoginInfo>(`/v1/logins/${loginName}`)
}

// 获取二维码
export const getQrcode = (loginName: string, data: QrcodeRequest) => {
  return request.post<QrcodeResponse>(`/v1/logins/${loginName}/qrcode`, data)
}

// 验证登录状态（轮询）
export const verifyLogin = (loginName: string) => {
  return request.post<LoginStatus>(`/v1/logins/${loginName}/verify`)
}

// 检查登录状态
export const checkLoginStatus = (loginName: string) => {
  return request.get<LoginStatus>(`/v1/logins/${loginName}/status`)
}

// 清除登录状态（返回 data 部分，只包含 login_name）
export const clearLoginSession = (loginName: string) => {
  return request.delete<{ login_name: string }>(`/v1/logins/${loginName}/session`)
}

// 清理二维码资源（返回 data 部分，只包含 login_name）
export const cleanupQrcodeResources = (loginName: string) => {
  return request.post<{ login_name: string }>(`/v1/logins/${loginName}/cleanup`)
}
