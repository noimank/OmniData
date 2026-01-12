// API 类型定义

// ============== 统一响应格式 ==============

export interface ApiResponse<T = any> {
  success: boolean
  message: string
  data: T | null
}

export interface PaginatedResponse<T = any> {
  success: boolean
  message: string
  data: T[] | null
  count: number
}

// ============== 监控相关 ==============
export interface BrowserPoolStats {
  browser_count: number
  config: {
    pool_initial_size: number
    headless: boolean
  }
}

export interface SpiderInfo {
  name: string
  description: string
  version: string
  author?: string
  platform: string
}

export interface SpiderStats {
  total_count: number
  spiders: SpiderInfo[]
}

export interface SystemStats {
  status: string
  uptime_seconds: number
  memory_usage_mb: number
  memory_percent: number
  cpu_percent: number
  redis_connected: boolean
  timestamp?: string
}

// ============== 登录管理相关 ==============
export interface LoginInfo {
  name: string
  platform: string
  description: string
  version: string
  author?: string
  qrcode_types?: string[]
  login_status?: LoginStatus
}

export interface LoginListResponse {
  count: number
  logins: LoginInfo[]
}

export interface QrcodeRequest {
  qr_type: string
}

export interface QrcodeResponse {
  success: boolean
  login_name: string
  url: string
  qr_type: string
  message: string
}

export interface LoginStatus {
  status: 'waiting' | 'success' | 'failed' | 'not_logged_in' | 'error'
  message: string
  login_name?: string
}

// ============== 爬虫相关 ==============
export interface SpiderListResponse {
  count: number
  spiders: SpiderInfo[]
}

export interface SpiderRunRequest {
  spider_name: string
  params: Record<string, any>
}

export interface SpiderResult {
  spider_name: string
  success: boolean
  data: any
  message: string | null
  error: string | null
  started_at: string
  completed_at: string | null
  duration_seconds: number
  metadata: Record<string, any>
}

export interface SpiderSchema {
  name: string
  description: string
  version: string
  params_schema: Record<string, ParamSchema>
  required: string[]
}

export interface ParamSchema {
  type: string
  title: string
  description: string
  default?: any
  enum?: any[]
}

export interface ValidateParamsRequest {
  params: Record<string, any>
}

export interface ValidateParamsResponse {
  valid: boolean
  errors: string[]
  warnings: string[]
}

// ============== MCP 服务相关 ==============
export type McpTransport = 'http' | 'streamable-http' | 'sse'

// Spider 提示词相关类型
export interface SpiderPrompt {
  id: number
  spider_name: string
  version_name: string
  description: string
  is_default: boolean
  usage_count: number
  created_at: string
  updated_at: string
}

export interface SpiderPromptCreate {
  spider_name: string
  version_name: string
  description: string
  is_default?: boolean
}

export interface SpiderPromptUpdate {
  version_name?: string
  description?: string
}

export interface PromptUsageInfo {
  prompt_id: number
  spider_name: string
  version_name: string
  usage_count: number
  tools: Array<{
    tool_id: number
    tool_name: string
    service_id: number
    service_name: string
    service_display_name: string
  }>
}

// 工具提示词版本相关类型
export interface ToolPromptVersionResponse {
  tool_id: number
  spider_name: string
  current_version: string | null
  current_description: string | null
  available_versions: Array<{
    version_name: string
    description: string
    is_default: boolean
  }>
}

export interface ToolPromptVersionUpdate {
  version_name: string
}

// Spider 信息相关类型
export interface SpiderInfoForMcp {
  name: string
  description: string
  platform: string
  version: string
  has_params_model: boolean
  parameter_info: SpiderParameterInfo[]
}

export interface McpToolCreate {
  spider_name: string
  tool_name?: string
}

export interface McpServiceCreate {
  name: string
  display_name: string
  description: string
  transport: McpTransport
  tools: McpToolCreate[]
}

export interface McpServiceUpdate {
  display_name?: string
  description?: string
  transport?: McpTransport
  tools?: McpToolCreate[]
}

export interface McpService {
  id: number
  name: string
  display_name: string
  description: string
  transport: McpTransport
  is_active: boolean
  created_at: string
  updated_at: string
  tool_count: number
}

export interface McpTool {
  id: number
  service_id: number
  spider_name: string
  tool_name: string
  enabled: boolean
  selected_prompt_version?: string | null
  current_prompt_description?: string | null
}

export interface SpiderParameterInfo {
  name: string
  type: string
  required: boolean
  description: string
  default?: any
  enum?: any[]
}
