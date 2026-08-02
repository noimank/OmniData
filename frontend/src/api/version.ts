import request from './request'
import type { ApiResponse, RemoteVersion } from './types'

// 获取远端仓库最新版本信息
export const getRemoteVersion = (): Promise<ApiResponse<RemoteVersion>> => {
  return request.get<ApiResponse<RemoteVersion>>('/v1/version/check')
}
