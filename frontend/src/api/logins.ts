import request from './request'
import type {
  LoginListResponse,
  LoginInfo,
  QrcodeRequest,
  QrcodeData,
  LoginStatusData,
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

// 获取二维码（数据嵌套在 ApiResponse.data 中）
export const getQrcode = (loginName: string, data: QrcodeRequest): Promise<ApiResponse<QrcodeData>> => {
  return request.post<ApiResponse<QrcodeData>>(`/v1/logins/${loginName}/qrcode`, data)
}

// 验证登录状态（轮询）（数据嵌套在 ApiResponse.data 中）
export const verifyLogin = (loginName: string): Promise<ApiResponse<LoginStatusData>> => {
  return request.post<ApiResponse<LoginStatusData>>(`/v1/logins/${loginName}/verify`)
}

// 检查登录状态（数据嵌套在 ApiResponse.data 中）
export const checkLoginStatus = (loginName: string): Promise<ApiResponse<LoginStatusData>> => {
  return request.get<ApiResponse<LoginStatusData>>(`/v1/logins/${loginName}/status`)
}

// 清除登录状态
export const clearLoginSession = (loginName: string): Promise<ApiResponse<{ login_name: string }>> => {
  return request.delete<ApiResponse<{ login_name: string }>>(`/v1/logins/${loginName}/session`)
}

// 清理二维码资源
export const cleanupQrcodeResources = (loginName: string): Promise<ApiResponse<{ login_name: string }>> => {
  return request.post<ApiResponse<{ login_name: string }>>(`/v1/logins/${loginName}/cleanup`)
}
