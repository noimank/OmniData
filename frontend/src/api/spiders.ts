import request from './request'
import type {
  SpiderInfo,
  SpiderRunRequest,
  SpiderResult,
  SpiderSchema,
  ValidateParamsRequest,
  ValidateParamsResponse,
  SpiderListResponse,
  ApiResponse
} from './types'

// 获取爬虫列表
export const getSpiders = () => {
  return request.get<ApiResponse<SpiderListResponse>>('/v1/spiders')
}

// 获取爬虫详情
export const getSpiderInfo = (spiderName: string) => {
  return request.get<ApiResponse<SpiderInfo>>(`/v1/spiders/${spiderName}`)
}

// 运行爬虫（返回 SpiderResult）
export const runSpider = (data: SpiderRunRequest) => {
  return request.post<SpiderResult>('/v1/spiders/run', data)
}

// 批量运行爬虫（返回批量结果）
export const runSpiderBatch = (data: {
  spider_name: string
  params_list: Record<string, any>[]
  max_concurrency?: number
}) => {
  return request.post<{ count: number; results: SpiderResult[] }>('/v1/spiders/run-batch', data)
}

// 获取爬虫参数 schema
export const getSpiderSchema = (spiderName: string) => {
  return request.get<ApiResponse<SpiderSchema>>(`/v1/spiders/${spiderName}/schema`)
}

// 验证爬虫参数
export const validateSpiderParams = (spiderName: string, data: ValidateParamsRequest) => {
  return request.post<ApiResponse<ValidateParamsResponse>>(`/v1/spiders/${spiderName}/validate`, data)
}
