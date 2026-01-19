import request from './request'
import type {
  McpService,
  McpServiceCreate,
  McpServiceUpdate,
  McpTool,
  McpToolCreate,
  SpiderPrompt,
  SpiderPromptCreate,
  SpiderPromptUpdate,
  PromptUsageInfo,
  ToolPromptVersionResponse,
  ToolPromptVersionUpdate,
  SpiderInfoForMcp,
} from './types'

const MCP_BASE = '/v1/mcp-services'
const SPIDER_PROMPT_BASE = '/v1/spider-prompts'

// ============== Spider 提示词管理 ==============

export async function listSpiderPrompts(params?: {
  spider_name?: string
  is_default?: boolean
}): Promise<SpiderPrompt[]> {
  const query = new URLSearchParams()
  if (params?.spider_name !== undefined) query.append('spider_name', params.spider_name)
  if (params?.is_default !== undefined) query.append('is_default', String(params.is_default))
  const queryString = query.toString()
  return request.get<SpiderPrompt[]>(`${SPIDER_PROMPT_BASE}${queryString ? `?${queryString}` : ''}`)
}

export async function getSpiderPrompt(promptId: number): Promise<SpiderPrompt> {
  return request.get<SpiderPrompt>(`${SPIDER_PROMPT_BASE}/${promptId}`)
}

export async function createSpiderPrompt(data: SpiderPromptCreate): Promise<SpiderPrompt> {
  return request.post<SpiderPrompt>(`${SPIDER_PROMPT_BASE}`, data)
}

export async function updateSpiderPrompt(promptId: number, data: SpiderPromptUpdate): Promise<SpiderPrompt> {
  return request.put<SpiderPrompt>(`${SPIDER_PROMPT_BASE}/${promptId}`, data)
}

export async function deleteSpiderPrompt(promptId: number): Promise<void> {
  return request.delete<void>(`${SPIDER_PROMPT_BASE}/${promptId}`)
}

export async function setSpiderPromptAsDefault(promptId: number): Promise<SpiderPrompt> {
  return request.put<SpiderPrompt>(`${SPIDER_PROMPT_BASE}/${promptId}/set-default`)
}

export async function getSpiderPromptUsage(promptId: number): Promise<PromptUsageInfo> {
  return request.get<PromptUsageInfo>(`${SPIDER_PROMPT_BASE}/${promptId}/usage`)
}

// Per-Spider 提示词端点

export async function listSpiderPromptsByName(spiderName: string): Promise<SpiderPrompt[]> {
  return request.get<SpiderPrompt[]>(`${SPIDER_PROMPT_BASE}/spiders/${spiderName}/prompts`)
}

export async function createSpiderPromptForSpider(
  spiderName: string,
  data: Omit<SpiderPromptCreate, 'spider_name'>
): Promise<SpiderPrompt> {
  return request.post<SpiderPrompt>(`${SPIDER_PROMPT_BASE}/spiders/${spiderName}/prompts`, data)
}

export async function getSpiderDefaultPrompt(spiderName: string): Promise<SpiderPrompt> {
  return request.get<SpiderPrompt>(`${SPIDER_PROMPT_BASE}/spiders/${spiderName}/default-prompt`)
}

// 获取所有可用的 Spider 列表（用于提示词管理）
export async function listAvailableSpidersForPrompts(): Promise<SpiderInfoForMcp[]> {
  return request.get<SpiderInfoForMcp[]>(`${SPIDER_PROMPT_BASE}/spiders/available`)
}

// ============== 服务 CRUD ==============

export async function listMcpServices(isActive?: boolean): Promise<McpService[]> {
  const params = isActive !== undefined ? `?is_active=${isActive}` : ''
  return request.get<McpService[]>(`${MCP_BASE}${params}`)
}

export async function getMcpService(serviceId: number): Promise<McpService> {
  return request.get<McpService>(`${MCP_BASE}/${serviceId}`)
}

export async function createMcpService(data: McpServiceCreate): Promise<McpService> {
  return request.post<McpService>(`${MCP_BASE}`, data)
}

export async function updateMcpService(serviceId: number, data: McpServiceUpdate): Promise<McpService> {
  return request.put<McpService>(`${MCP_BASE}/${serviceId}`, data)
}

export async function deleteMcpService(serviceId: number): Promise<void> {
  return request.delete<void>(`${MCP_BASE}/${serviceId}`)
}

export async function activateMcpService(serviceId: number): Promise<McpService> {
  return request.put<McpService>(`${MCP_BASE}/${serviceId}/activate`, {})
}

export async function deactivateMcpService(serviceId: number): Promise<McpService> {
  return request.put<McpService>(`${MCP_BASE}/${serviceId}/deactivate`, {})
}

// ============== 工具管理 ==============

export async function listTools(serviceId: number): Promise<McpTool[]> {
  return request.get<McpTool[]>(`${MCP_BASE}/${serviceId}/tools`)
}

export async function addTool(serviceId: number, data: McpToolCreate): Promise<McpTool> {
  return request.post<McpTool>(`${MCP_BASE}/${serviceId}/tools`, data)
}

export async function removeTool(serviceId: number, toolId: number): Promise<void> {
  return request.delete<void>(`${MCP_BASE}/${serviceId}/tools/${toolId}`)
}

// ============== 工具提示词版本管理 ==============

export async function getToolPromptVersion(
  serviceId: number,
  toolId: number
): Promise<ToolPromptVersionResponse> {
  return request.get<ToolPromptVersionResponse>(`${MCP_BASE}/${serviceId}/tools/${toolId}/prompt-version`)
}

export async function setToolPromptVersion(
  serviceId: number,
  toolId: number,
  data: ToolPromptVersionUpdate
): Promise<ToolPromptVersionResponse> {
  return request.put<ToolPromptVersionResponse>(`${MCP_BASE}/${serviceId}/tools/${toolId}/prompt-version`, data)
}

export async function clearToolPromptVersion(
  serviceId: number,
  toolId: number
): Promise<ToolPromptVersionResponse> {
  return request.delete<ToolPromptVersionResponse>(`${MCP_BASE}/${serviceId}/tools/${toolId}/prompt-version`)
}

// ============== Spider 信息 ==============

export async function listAvailableSpiders(): Promise<SpiderInfoForMcp[]> {
  return request.get<SpiderInfoForMcp[]>(`${MCP_BASE}/spiders/available`)
}
