import request from './request'
import type {
  SpiderAuditQuery,
  SpiderAuditResponse,
  SpiderAuditStats,
  ApiResponse
} from './types'

/**
 * 获取审计统计信息
 */
export function getAuditStats(): Promise<ApiResponse<SpiderAuditStats>> {
  return request.get<ApiResponse<SpiderAuditStats>>('/v1/spider-audit/stats')
}

/**
 * 获取审计记录列表（分页）
 */
export function getAuditRecords(params: SpiderAuditQuery): Promise<ApiResponse<SpiderAuditResponse>> {
  return request.get<ApiResponse<SpiderAuditResponse>>('/v1/spider-audit/records', {
    params: {
      spider_name: params.spider_name,
      platform: params.platform,
      success: params.success,
      start_date: params.start_date,
      end_date: params.end_date,
      page: params.page || 1,
      page_size: params.page_size || 20,
    },
  })
}

/**
 * 获取平台列表
 */
export function getAuditPlatforms(): Promise<ApiResponse<string[]>> {
  return request.get<ApiResponse<string[]>>('/v1/spider-audit/platforms')
}

/**
 * 获取爬虫列表
 */
export function getAuditSpiders(platform?: string): Promise<ApiResponse<string[]>> {
  return request.get<ApiResponse<string[]>>('/v1/spider-audit/spiders', {
    params: platform ? { platform } : undefined,
  })
}

/**
 * 删除单条审计记录
 */
export function deleteAuditRecord(recordId: number): Promise<ApiResponse<{ id: number }>> {
  return request.delete<ApiResponse<{ id: number }>>(`/v1/spider-audit/records/${recordId}`)
}

/**
 * 清理指定天数之前的审计记录
 */
export function cleanupAuditRecords(days: number = 30): Promise<ApiResponse<{ count: number }>> {
  return request.delete<ApiResponse<{ count: number }>>('/v1/spider-audit/cleanup', {
    params: { days },
  })
}
