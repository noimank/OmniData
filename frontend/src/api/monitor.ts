import request from './request'
import type {
  BrowserContextPoolStats,
  SystemStats,
  ContextInfo,
  ApiResponse
} from './types'

// 获取浏览器上下文池状态
export const getBrowserContextPool = (): Promise<ApiResponse<BrowserContextPoolStats>> => {
  return request.get<ApiResponse<BrowserContextPoolStats>>('/v1/monitor/browser-pool')
}

// 获取系统资源状态
export const getSystemResource = (): Promise<ApiResponse<SystemStats>> => {
  return request.get<ApiResponse<SystemStats>>('/v1/monitor/system')
}

// 获取 Context 列表
export const getContextList = (): Promise<ApiResponse<ContextInfo[]>> => {
  return request.get<ApiResponse<ContextInfo[]>>('/v1/monitor/contexts')
}
