import type {
  ExtractionProviderName,
  ExtractionProviderSetting,
  ExtractionSettingKey,
  ExtractionSettingsRevisionAction,
  ExtractionSettingsUpdate,
  ExtractionSettingsValues,
} from '@/api/types'

/** 表单内部状态：数值用字符串承载，提交时统一校验转换。 */
export interface ExtractionSettingsDraft {
  provider: ExtractionProviderSetting
  autoChain: ExtractionProviderName[]
  paddleocrEndpoint: string
  llmEndpoint: string
  llmModel: string
  llmEnabled: boolean
  promptVersion: string
  httpTimeout: string
  maxAttempts: string
  staleMinutes: string
  backoffSeconds: string
}

export interface DraftSecrets {
  /** 新输入的 API Key；空串表示不修改。 */
  apiKey: string
  /** 勾选「清除」时提交 null。 */
  clearApiKey: boolean
}

export type DraftErrors = Partial<Record<keyof ExtractionSettingsDraft, string>>

export const PROVIDER_OPTIONS: Array<{
  value: ExtractionProviderSetting
  label: string
}> = [
  { value: 'auto', label: '自动（按链路依次尝试）' },
  { value: 'pdf_text', label: 'PDF 文本层' },
  { value: 'paddleocr_local', label: '本地 PaddleOCR' },
  { value: 'multimodal_llm', label: '多模态大模型' },
  { value: 'mock', label: '模拟引擎（仅测试）' },
]

export const CHAIN_OPTIONS: Array<{
  value: ExtractionProviderName
  label: string
}> = [
  { value: 'pdf_text', label: 'PDF 文本层' },
  { value: 'paddleocr_local', label: '本地 PaddleOCR' },
  { value: 'multimodal_llm', label: '多模态大模型' },
  { value: 'mock', label: '模拟引擎' },
]

export const SOURCE_LABELS = {
  database: '数据库',
  env: '环境变量',
  default: '默认值',
} as const

export const FIELD_LABELS: Partial<Record<ExtractionSettingKey, string>> = {
  provider: '识别引擎',
  auto_chain: '自动链路',
  paddleocr_endpoint: 'OCR 接口地址',
  llm_endpoint: '大模型接口地址',
  llm_model: '模型名',
  llm_api_key: 'API Key',
  llm_enabled: '启用大模型',
  prompt_version: 'Prompt 版本',
  http_timeout: 'HTTP 超时',
  max_attempts: '最大尝试次数',
  stale_minutes: '超时回收',
  backoff_seconds: '退避基数',
}

export function settingsActionLabel(
  action: ExtractionSettingsRevisionAction,
): string {
  if (action === 'rollback') return '回滚'
  if (action === 'reset') return '恢复默认'
  return '保存'
}

function toText(value: string | null): string {
  return value ?? ''
}

export function toDraft(
  values: ExtractionSettingsValues,
): ExtractionSettingsDraft {
  return {
    provider: values.provider,
    autoChain: [...values.auto_chain],
    paddleocrEndpoint: toText(values.paddleocr_endpoint),
    llmEndpoint: toText(values.llm_endpoint),
    llmModel: toText(values.llm_model),
    llmEnabled: values.llm_enabled,
    promptVersion: values.prompt_version,
    httpTimeout: String(values.http_timeout),
    maxAttempts: String(values.max_attempts),
    staleMinutes: String(values.stale_minutes),
    backoffSeconds: String(values.backoff_seconds),
  }
}

/** 勾选顺序固定为 CHAIN_OPTIONS，保存时按该顺序作为尝试顺序。 */
export function toggleChain(
  chain: ExtractionProviderName[],
  value: ExtractionProviderName,
  checked: boolean,
): ExtractionProviderName[] {
  const next = new Set(chain)
  if (checked) next.add(value)
  else next.delete(value)
  return CHAIN_OPTIONS.filter((option) => next.has(option.value)).map(
    (option) => option.value,
  )
}

function parseNumber(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined) return null
  const text = String(value).trim()
  if (text === '') return null
  const parsed = Number(text)
  return Number.isFinite(parsed) ? parsed : null
}

function isHttpUrl(value: string): boolean {
  return /^https?:\/\/[^\s]+$/i.test(value.trim())
}

function cleanText(value: string): string | null {
  const text = value.trim()
  return text === '' ? null : text
}

export function validateDraft(
  draft: ExtractionSettingsDraft,
  secrets: DraftSecrets,
  values: ExtractionSettingsValues,
): DraftErrors {
  const errors: DraftErrors = {}

  if (draft.autoChain.length === 0) {
    errors.autoChain = '至少选择一个要尝试的识别引擎'
  }
  if (draft.provider === 'multimodal_llm' && !draft.llmEnabled) {
    errors.provider = '选择多模态大模型作为引擎前，请先启用大模型'
  }
  if (!draft.promptVersion.trim()) {
    errors.promptVersion = 'Prompt 版本不能为空'
  }

  const ocrEndpoint = draft.paddleocrEndpoint.trim()
  if (ocrEndpoint !== '' && !isHttpUrl(ocrEndpoint)) {
    errors.paddleocrEndpoint = '请填写 http:// 或 https:// 开头的地址'
  }
  const llmEndpoint = draft.llmEndpoint.trim()
  if (llmEndpoint !== '' && !isHttpUrl(llmEndpoint)) {
    errors.llmEndpoint = '请填写 http:// 或 https:// 开头的地址'
  }

  const httpTimeout = parseNumber(draft.httpTimeout)
  if (httpTimeout === null || httpTimeout <= 0 || httpTimeout > 300) {
    errors.httpTimeout = '请输入 0 到 300 之间的秒数'
  }
  const maxAttempts = parseNumber(draft.maxAttempts)
  if (
    maxAttempts === null ||
    !Number.isInteger(maxAttempts) ||
    maxAttempts < 1 ||
    maxAttempts > 10
  ) {
    errors.maxAttempts = '请输入 1 到 10 之间的整数'
  }
  const staleMinutes = parseNumber(draft.staleMinutes)
  if (
    staleMinutes === null ||
    !Number.isInteger(staleMinutes) ||
    staleMinutes < 1 ||
    staleMinutes > 1440
  ) {
    errors.staleMinutes = '请输入 1 到 1440 之间的整数（分钟）'
  }
  const backoffSeconds = parseNumber(draft.backoffSeconds)
  if (backoffSeconds === null || backoffSeconds < 0 || backoffSeconds > 3600) {
    errors.backoffSeconds = '请输入 0 到 3600 之间的秒数'
  }

  if (draft.llmEnabled) {
    if (llmEndpoint === '') {
      errors.llmEndpoint = '启用大模型时必须填写接口地址'
    }
    if (!draft.llmModel.trim()) {
      errors.llmModel = '启用大模型时必须填写模型名'
    }
    // 勾选「清除」后，即使输入框里还残留着文字，也不能再视为已配置
    const hasKey =
      !secrets.clearApiKey &&
      (values.llm_api_key_set || secrets.apiKey.trim() !== '')
    if (!hasKey) {
      errors.llmEnabled = '启用大模型前必须填写 API Key'
    }
  }

  return errors
}

/** 组装 PUT 请求体；llm_api_key 缺省表示保持原值。 */
export function buildPayload(
  draft: ExtractionSettingsDraft,
  secrets: DraftSecrets,
): ExtractionSettingsUpdate {
  const payload: ExtractionSettingsUpdate = {
    provider: draft.provider,
    auto_chain: [...draft.autoChain],
    paddleocr_endpoint: cleanText(draft.paddleocrEndpoint),
    llm_endpoint: cleanText(draft.llmEndpoint),
    llm_model: cleanText(draft.llmModel),
    llm_enabled: draft.llmEnabled,
    prompt_version: draft.promptVersion.trim(),
    http_timeout: Number(draft.httpTimeout),
    max_attempts: Math.round(Number(draft.maxAttempts)),
    stale_minutes: Math.round(Number(draft.staleMinutes)),
    backoff_seconds: Number(draft.backoffSeconds),
  }

  if (secrets.clearApiKey) {
    payload.llm_api_key = null
  } else if (secrets.apiKey.trim() !== '') {
    payload.llm_api_key = secrets.apiKey.trim()
  }

  return payload
}

/** 与上一版本比较，返回发生变化的配置项文案。 */
export function changedFieldLabels(
  currentValues: Record<string, unknown>,
  previousValues: Record<string, unknown> | null,
  action: ExtractionSettingsRevisionAction,
): string[] {
  if (action === 'reset') return ['清除全部覆盖配置']
  const keys = Object.keys(FIELD_LABELS) as ExtractionSettingKey[]
  if (previousValues === null) return ['初始配置']
  return keys
    .filter((key) => {
      const before = previousValues[key] ?? null
      const after = currentValues[key] ?? null
      return JSON.stringify(before) !== JSON.stringify(after)
    })
    .map((key) => FIELD_LABELS[key] ?? key)
}
