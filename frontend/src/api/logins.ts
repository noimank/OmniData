import request from './request'
import type {
  LoginListResponse,
  LoginInfo,
  QrcodeRequest,
  QrcodeResponse,
  LoginStatus,
  ApiResponse
} from './types'

// 列出所有登录器
export const getLogins = (): Promise<ApiResponse<LoginListResponse>> => {
  return request.get<ApiResponse<LoginListResponse>>('/v1/logins')
}

// 获取登录器详情
export const getLoginDetail = (loginName: string): Promise<ApiResponse<LoginInfo>> => {
  return request.get<ApiResponse<LoginInfo>>(`/v1/logins/${loginName}`)
}

// 获取二维码（QrcodeResponse 本身就是完整响应格式，不需要包装）
export const getQrcode = (loginName: string, data: QrcodeRequest): Promise<QrcodeResponse> => {
  return request.post<QrcodeResponse>(`/v1/logins/${loginName}/qrcode`, data)
}

// 验证登录状态（轮询）(LoginStatus 本身就是完整响应格式)
export const verifyLogin = (loginName: string): Promise<LoginStatus> => {
  return request.post<LoginStatus>(`/v1/logins/${loginName}/verify`)
}

// 检查登录状态（LoginStatus 本身就是完整响应格式）
export const checkLoginStatus = (loginName: string): Promise<LoginStatus> => {
  return request.get<LoginStatus>(`/v1/logins/${loginName}/status`)
}

// 清除登录状态
export const clearLoginSession = (loginName: string): Promise<ApiResponse<{ login_name: string }>> => {
  return request.delete<ApiResponse<{ login_name: string }>>(`/v1/logins/${loginName}/session`)
}

// 清理二维码资源
export const cleanupQrcodeResources = (loginName: string): Promise<ApiResponse<{ login_name: string }>> => {
  return request.post<ApiResponse<{ login_name: string }>>(`/v1/logins/${loginName}/cleanup`)
}
