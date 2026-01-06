// API 类型定义

// ============== 认证相关 ==============
export interface VerifyApiKeyRequest {
  api_key: string
}

export interface VerifyApiKeyResponse {
  valid: boolean
  message: string
  required: boolean
}

export interface AuthConfig {
  required: boolean
  configured: boolean
}

// ============== 监控相关 ==============
export interface BrowserInfo {
  index: number
  idle_time_seconds: number
}

export interface BrowserPoolStats {
  browser_count: number
  browsers: BrowserInfo[]
  config: {
    pool_initial_size: number
    idle_timeout: number
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

export interface AllStats {
  browser_pool: {
    browser_count: number
    browsers: BrowserInfo[]
  }
  spiders: {
    total_count: number
    spiders: SpiderInfo[]
  }
  system: SystemStats
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
