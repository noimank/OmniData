import request from './request'
import type {
  BrowserContextPoolStats,
  SystemStats
} from './types'

// 获取浏览器上下文池状态
export const getBrowserContextPool = () => {
  return request.get<BrowserContextPoolStats>('/v1/monitor/browser-pool')
}

// 获取系统资源状态
export const getSystemResource = () => {
  return request.get<SystemStats>('/v1/monitor/system')
}
