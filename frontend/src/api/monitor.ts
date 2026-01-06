import request from './request'
import type {
  BrowserPoolStats,
  SpiderStats,
  SystemStats,
  AllStats
} from './types'

// 获取浏览器池状态
export const getBrowserPool = () => {
  return request.get<BrowserPoolStats>('/v1/monitor/browser-pool')
}

// 获取爬虫统计
export const getSpiderStats = () => {
  return request.get<SpiderStats>('/v1/monitor/spiders')
}

// 获取系统资源状态
export const getSystemResource = () => {
  return request.get<SystemStats>('/v1/monitor/system')
}

// 获取综合统计
export const getAllStats = () => {
  return request.get<AllStats>('/v1/monitor/stats')
}
