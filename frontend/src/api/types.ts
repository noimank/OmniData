// API 类型定义

// ============== 统一响应格式 ==============

export interface ApiResponse<T = any> {
  success: boolean
  message: string
  data: T | null
}

// ============== 监控相关 ==============
// Browser Context Pool 统计（单 Browser + 多 Context 架构）
export interface BrowserContextPoolStats {
  browser_count: number
  context_count: number
  checked_out_contexts: number
  total_contexts_created: number
  total_contexts_reused: number
  reuse_rate: number
  total_contexts_evicted: number
  total_contexts_closed: number
  config: {
    max_pool_size: number
    idle_timeout: number
    headless: boolean
  }
}

// Context 信息
export interface ContextInfo {
  namespace: string
  key: string
  created_at: number
  last_used_at: number
  idle_time: number
  pages_count: number
}

// 系统资源统计
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
  login_status?: LoginStatusData
}

export interface LoginListResponse {
  count: number
  logins: LoginInfo[]
}

export interface QrcodeRequest {
  qr_type: string
}

// 二维码数据（嵌套在 ApiResponse.data 中）
export interface QrcodeData {
  login_name: string
  url: string
  qr_type: string
}

// 登录状态数据（嵌套在 ApiResponse.data 中）
export interface LoginStatusData {
  status: 'waiting' | 'success' | 'failed' | 'not_logged_in'
  message: string
  login_name?: string
}

// ============== 爬虫相关 ==============
// 爬虫基础信息
export interface SpiderInfo {
  name: string
  description: string
  platform: string
  version: string
  author?: string
}

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
  current_prompt_version_name?: string | null
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

// ============== 爬虫审计相关 ==============

export interface SpiderAuditRecord {
  id: number
  spider_name: string
  platform: string
  spider_version: string
  success: boolean
  error_message: string | null
  started_at: string
  completed_at: string | null
  duration_seconds: number
  params: string | null
  metadata: string | null
  created_at: string
}

export interface SpiderAuditStats {
  today_count: number
  today_success_count: number
  today_failure_count: number
  total_count: number
  platform_stats: Array<{
    platform: string
    count: number
    success_count: number
    failure_count: number
  }>
  recent_success_rate: number
  hourly_stats: Array<{
    hour: string
    count: number
    success_count: number
    failure_count: number
  }>
  spider_ranking: Array<{
    spider_name: string
    count: number
    success_count: number
    failure_count: number
  }>
  recent_failures: Array<{
    id: number
    spider_name: string
    platform: string
    error_message: string | null
    started_at: string
    duration_seconds: number
  }>
}

export interface SpiderAuditQuery {
  spider_name?: string
  platform?: string
  success?: boolean
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}

// 分页响应（统一格式，count 在 data 中）
export interface SpiderAuditResponse {
  items: SpiderAuditRecord[]
  count: number
}

// ============== 版本检查 ==============
// 远端仓库 main 分支最新提交信息
export interface RemoteVersion {
  commit_sha: string
  commit_date: string
  message: string
  html_url: string
}
