import { describe, expect, it } from 'vitest'

import type { ExtractionSettingsValues } from '@/api/types'
import {
  buildPayload,
  changedFieldLabels,
  toDraft,
  toggleChain,
  validateDraft,
  type ExtractionSettingsDraft,
} from '../extraction-settings'

function values(
  overrides: Partial<ExtractionSettingsValues> = {},
): ExtractionSettingsValues {
  return {
    provider: 'pdf_text',
    auto_chain: ['pdf_text', 'paddleocr_local'],
    paddleocr_endpoint: null,
    llm_endpoint: null,
    llm_model: null,
    llm_enabled: false,
    llm_api_key_set: false,
    llm_api_key_hint: null,
    prompt_version: 'v1',
    http_timeout: 10,
    max_attempts: 3,
    stale_minutes: 15,
    backoff_seconds: 30,
    ...overrides,
  }
}

function draft(
  overrides: Partial<ExtractionSettingsDraft> = {},
): ExtractionSettingsDraft {
  return { ...toDraft(values()), ...overrides }
}

const noSecret = { apiKey: '', clearApiKey: false }

describe('toDraft', () => {
  it('renders numbers as strings and null endpoints as empty strings', () => {
    const result = toDraft(values({ http_timeout: 2.5 }))
    expect(result.httpTimeout).toBe('2.5')
    expect(result.paddleocrEndpoint).toBe('')
    expect(result.autoChain).toEqual(['pdf_text', 'paddleocr_local'])
  })
})

describe('toggleChain', () => {
  it('keeps canonical order regardless of toggle sequence', () => {
    let chain = toggleChain([], 'multimodal_llm', true)
    chain = toggleChain(chain, 'pdf_text', true)
    expect(chain).toEqual(['pdf_text', 'multimodal_llm'])
  })

  it('removes unchecked providers', () => {
    expect(toggleChain(['pdf_text', 'mock'], 'pdf_text', false)).toEqual(['mock'])
  })
})

describe('buildPayload', () => {
  it('omits llm_api_key when the admin did not touch it', () => {
    const payload = buildPayload(draft(), noSecret)
    expect('llm_api_key' in payload).toBe(false)
    expect(payload.http_timeout).toBe(10)
    expect(payload.paddleocr_endpoint).toBeNull()
  })

  it('sends null to clear a stored key', () => {
    const payload = buildPayload(draft(), { apiKey: '', clearApiKey: true })
    expect(payload.llm_api_key).toBeNull()
  })

  it('sends a trimmed key when typed', () => {
    const payload = buildPayload(draft(), {
      apiKey: '  sk-abc  ',
      clearApiKey: false,
    })
    expect(payload.llm_api_key).toBe('sk-abc')
  })

  it('rounds integer parameters', () => {
    const payload = buildPayload(
      draft({ maxAttempts: '2.6', staleMinutes: '20' }),
      noSecret,
    )
    expect(payload.max_attempts).toBe(3)
    expect(payload.stale_minutes).toBe(20)
  })
})

describe('validateDraft', () => {
  it('accepts a default configuration', () => {
    expect(validateDraft(draft(), noSecret, values())).toEqual({})
  })

  it('requires at least one provider in the chain', () => {
    const errors = validateDraft(draft({ autoChain: [] }), noSecret, values())
    expect(errors.autoChain).toBeTruthy()
  })

  it('requires endpoint, model and key when the LLM is enabled', () => {
    const errors = validateDraft(
      draft({ llmEnabled: true }),
      noSecret,
      values(),
    )
    expect(errors.llmEndpoint).toBeTruthy()
    expect(errors.llmModel).toBeTruthy()
    expect(errors.llmEnabled).toBeTruthy()
  })

  it('accepts a stored key when enabling the LLM', () => {
    const errors = validateDraft(
      draft({
        llmEnabled: true,
        llmEndpoint: 'https://llm.example.com/v1',
        llmModel: 'vision-1',
      }),
      noSecret,
      values({ llm_api_key_set: true, llm_api_key_hint: '••••1234' }),
    )
    expect(errors).toEqual({})
  })

  it('rejects enabling the LLM when the stored key is being cleared', () => {
    const errors = validateDraft(
      draft({
        llmEnabled: true,
        llmEndpoint: 'https://llm.example.com/v1',
        llmModel: 'vision-1',
      }),
      { apiKey: 'sk-stale-input', clearApiKey: true },
      values({ llm_api_key_set: true, llm_api_key_hint: '••••1234' }),
    )
    expect(errors.llmEnabled).toBeTruthy()
  })

  it('rejects multimodal provider without an enabled LLM', () => {
    const errors = validateDraft(
      draft({ provider: 'multimodal_llm', llmEnabled: false }),
      noSecret,
      values(),
    )
    expect(errors.provider).toBeTruthy()
  })

  it('rejects non-http endpoints and out-of-range numbers', () => {
    const errors = validateDraft(
      draft({
        paddleocrEndpoint: 'ftp://ocr.local',
        httpTimeout: '0',
        maxAttempts: '0',
        staleMinutes: '0',
        backoffSeconds: '-1',
        promptVersion: '   ',
      }),
      noSecret,
      values(),
    )
    expect(errors.paddleocrEndpoint).toBeTruthy()
    expect(errors.httpTimeout).toBeTruthy()
    expect(errors.maxAttempts).toBeTruthy()
    expect(errors.staleMinutes).toBeTruthy()
    expect(errors.backoffSeconds).toBeTruthy()
    expect(errors.promptVersion).toBeTruthy()
  })
})

describe('changedFieldLabels', () => {
  it('lists changed fields against the previous snapshot', () => {
    const labels = changedFieldLabels(
      { provider: 'auto', max_attempts: 3 },
      { provider: 'pdf_text', max_attempts: 3 },
      'update',
    )
    expect(labels).toEqual(['识别引擎'])
  })

  it('labels the first saved revision as initial', () => {
    expect(changedFieldLabels({ provider: 'auto' }, null, 'update')).toEqual([
      '初始配置',
    ])
  })

  it('summarises resets', () => {
    expect(changedFieldLabels({}, { provider: 'auto' }, 'reset')).toEqual([
      '清除全部覆盖配置',
    ])
  })
})
