/**
 * fetch 封装：内存 access token、401 单次 refresh、统一 ApiError。
 * 组件中禁止直接 fetch，所有请求经 src/api。
 */

export type QueryValue = string | number | boolean | null | undefined
export type QueryParams = Record<string, QueryValue>
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export interface RequestOptions {
  method?: HttpMethod
  query?: QueryParams
  body?: unknown
  headers?: HeadersInit
  signal?: AbortSignal
  /** 登录 / 刷新 / 登出等认证端点跳过自动 refresh，避免递归。 */
  skipAuthRefresh?: boolean
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: Record<string, unknown> | null
  readonly traceId: string | null

  constructor(
    status: number,
    code: string,
    message: string,
    details: Record<string, unknown> | null = null,
    traceId: string | null = null,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
    this.traceId = traceId
  }
}

const envBaseUrl = import.meta.env.VITE_API_BASE_URL
const configuredBaseUrl =
  typeof envBaseUrl === 'string'
    ? envBaseUrl.trim().replace(/\/+$/, '')
    : ''

/** 默认走 Vite 代理的 /api/v1；部署时可用 VITE_API_BASE_URL 覆盖。 */
export const apiBaseUrl = configuredBaseUrl !== '' ? configuredBaseUrl : '/api/v1'

let accessToken: string | null = null
let accessTokenListener: ((token: string | null) => void) | null = null
let refreshPromise: Promise<boolean> | null = null

/** access token 只保存在内存中，不写 localStorage / sessionStorage。 */
export function setAccessToken(token: string | null): void {
  accessToken = token
  accessTokenListener?.(token)
}

export function getAccessToken(): string | null {
  return accessToken
}

/** auth store 用此监听自动 refresh 后的 token 变化。 */
export function setAccessTokenListener(
  listener: ((token: string | null) => void) | null,
): void {
  accessTokenListener = listener
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

/** 将查询对象转换成 QueryParams，并过滤空值（保留 0 / false）。 */
export function toQueryParams(input: object): QueryParams {
  const result: QueryParams = {}
  for (const [key, value] of Object.entries(input)) {
    if (value === undefined || value === null || value === '') continue
    if (
      typeof value === 'string' ||
      typeof value === 'number' ||
      typeof value === 'boolean'
    ) {
      result[key] = value
    }
  }
  return result
}

function buildUrl(path: string, query?: QueryParams): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const url = `${apiBaseUrl}${normalizedPath}`
  if (!query) return url

  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === '') continue
    search.append(key, String(value))
  }

  const queryString = search.toString()
  return queryString ? `${url}?${queryString}` : url
}

function defaultMessage(status: number): string {
  switch (status) {
    case 0:
      return '无法连接到服务器，请稍后重试'
    case 400:
      return '请求参数有误，请检查后重试'
    case 401:
      return '登录已过期，请重新登录'
    case 403:
      return '没有权限执行此操作'
    case 404:
      return '请求的数据不存在或已被删除'
    case 409:
      return '数据冲突，请刷新后重试'
    case 422:
      return '提交的数据不符合要求，请检查表单'
    case 500:
      return '服务器处理失败，请稍后重试'
    default:
      return '请求失败，请稍后重试'
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  let payload: unknown = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }

  const record = isRecord(payload) ? payload : null
  const code =
    record && typeof record.code === 'string' ? record.code : `http_${response.status}`
  const message =
    record && typeof record.message === 'string' && record.message.trim() !== ''
      ? record.message
      : defaultMessage(response.status)
  const details =
    record && isRecord(record.details) ? record.details : null
  const traceId =
    record && typeof record.trace_id === 'string' ? record.trace_id : null

  return new ApiError(response.status, code, message, details, traceId)
}

async function refreshAccessToken(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
          headers: { Accept: 'application/json' },
        })
        if (!response.ok) {
          setAccessToken(null)
          return false
        }

        const payload: unknown = await response.json()
        if (
          isRecord(payload) &&
          typeof payload.access_token === 'string' &&
          payload.access_token !== ''
        ) {
          setAccessToken(payload.access_token)
          return true
        }

        setAccessToken(null)
        return false
      } catch {
        setAccessToken(null)
        return false
      }
    })().finally(() => {
      refreshPromise = null
    })
  }

  return refreshPromise
}

function prepareBody(body: unknown): {
  payload: BodyInit | undefined
  isFormData: boolean
} {
  if (body === undefined || body === null) {
    return { payload: undefined, isFormData: false }
  }
  if (body instanceof FormData) {
    return { payload: body, isFormData: true }
  }
  return { payload: JSON.stringify(body), isFormData: false }
}

async function performRequest(
  path: string,
  options: RequestOptions = {},
): Promise<Response> {
  const url = buildUrl(path, options.query)
  const method = options.method ?? 'GET'
  const { payload, isFormData } = prepareBody(options.body)

  const execute = async (): Promise<Response> => {
    const headers = new Headers(options.headers)
    headers.set('Accept', 'application/json')
    if (accessToken) {
      headers.set('Authorization', `Bearer ${accessToken}`)
    }
    if (payload !== undefined && !isFormData && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json')
    }

    try {
      return await fetch(url, {
        method,
        headers,
        body: payload,
        credentials: 'include',
        signal: options.signal,
      })
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') throw error
      throw new ApiError(0, 'network_error', defaultMessage(0))
    }
  }

  let response = await execute()

  if (response.status === 401 && !options.skipAuthRefresh) {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      response = await execute()
    }
  }

  if (!response.ok) {
    throw await toApiError(response)
  }

  return response
}

/** 发起请求并解析 JSON；204 / 空响应返回 undefined。 */
export async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const response = await performRequest(path, options)
  if (response.status === 204) return undefined as T

  const text = await response.text()
  if (text === '') return undefined as T

  try {
    return JSON.parse(text) as T
  } catch {
    throw new ApiError(
      response.status,
      'invalid_response',
      '服务器返回了无法解析的数据',
    )
  }
}

/**
 * 带鉴权地获取二进制内容（文档预览 / 下载、xlsx 导出）。
 * 不得把鉴权 URL 直接塞进 iframe / img src。
 */
export async function getBlob(
  path: string,
  options: RequestOptions = {},
): Promise<Blob> {
  const response = await performRequest(path, options)
  return response.blob()
}
