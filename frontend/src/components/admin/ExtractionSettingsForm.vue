<script setup lang="ts">
import { ref, watch } from 'vue'
import { TriangleAlert } from '@lucide/vue'

import type {
  ExtractionProviderName,
  ExtractionProviderSetting,
  ExtractionSettingKey,
  ExtractionSettingSource,
  ExtractionSettings,
  ExtractionSettingsValues,
  ExtractionSettingsUpdate,
} from '@/api/types'
import FormErrorAlert from '@/components/admin/FormErrorAlert.vue'
import SettingsSourceTag from '@/components/admin/SettingsSourceTag.vue'
import ToggleField from '@/components/admin/ToggleField.vue'
import Button from '@/components/ui/Button.vue'
import FormField from '@/components/ui/FormField.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import {
  CHAIN_OPTIONS,
  PROVIDER_OPTIONS,
  buildPayload,
  toDraft,
  toggleChain,
  validateDraft,
  type DraftErrors,
  type ExtractionSettingsDraft,
} from './extraction-settings'

const props = withDefaults(
  defineProps<{
    settings: ExtractionSettings
    saving?: boolean
    error?: string | null
  }>(),
  {
    saving: false,
    error: null,
  },
)

const emit = defineEmits<{
  (event: 'submit', payload: ExtractionSettingsUpdate): void
  (event: 'reset'): void
}>()

const provider = ref<ExtractionProviderSetting>('pdf_text')
const autoChain = ref<ExtractionProviderName[]>([])
const paddleocrEndpoint = ref('')
const llmEndpoint = ref('')
const llmModel = ref('')
const llmEnabled = ref(false)
const promptVersion = ref('v1')
const httpTimeout = ref('10')
const maxAttempts = ref('3')
const staleMinutes = ref('15')
const backoffSeconds = ref('30')

const apiKey = ref('')
const clearApiKey = ref(false)
const errors = ref<DraftErrors>({})

function hydrate(values: ExtractionSettingsValues): void {
  const draft = toDraft(values)
  provider.value = draft.provider
  autoChain.value = [...draft.autoChain]
  paddleocrEndpoint.value = draft.paddleocrEndpoint
  llmEndpoint.value = draft.llmEndpoint
  llmModel.value = draft.llmModel
  llmEnabled.value = draft.llmEnabled
  promptVersion.value = draft.promptVersion
  httpTimeout.value = draft.httpTimeout
  maxAttempts.value = draft.maxAttempts
  staleMinutes.value = draft.staleMinutes
  backoffSeconds.value = draft.backoffSeconds
  apiKey.value = ''
  clearApiKey.value = false
  errors.value = {}
}

hydrate(props.settings.values)

watch(
  () => props.settings,
  (next) => hydrate(next.values),
)

function currentDraft(): ExtractionSettingsDraft {
  return {
    provider: provider.value,
    autoChain: [...autoChain.value],
    paddleocrEndpoint: paddleocrEndpoint.value,
    llmEndpoint: llmEndpoint.value,
    llmModel: llmModel.value,
    llmEnabled: llmEnabled.value,
    promptVersion: promptVersion.value,
    httpTimeout: httpTimeout.value,
    maxAttempts: maxAttempts.value,
    staleMinutes: staleMinutes.value,
    backoffSeconds: backoffSeconds.value,
  }
}

function sourceOf(key: ExtractionSettingKey): ExtractionSettingSource {
  return props.settings.sources[key] ?? 'default'
}

function onChainChange(value: ExtractionProviderName, event: Event): void {
  const checked = (event.target as HTMLInputElement).checked
  autoChain.value = toggleChain(autoChain.value, value, checked)
  errors.value = { ...errors.value, autoChain: undefined }
}

function onApiKeyInput(): void {
  clearApiKey.value = false
  errors.value = { ...errors.value, llmEnabled: undefined }
}

function onSubmit(): void {
  const secrets = { apiKey: apiKey.value, clearApiKey: clearApiKey.value }
  const draft = currentDraft()
  const nextErrors = validateDraft(draft, secrets, props.settings.values)
  errors.value = nextErrors
  if (Object.keys(nextErrors).length > 0) return
  emit('submit', buildPayload(draft, secrets))
}
</script>

<template>
  <form class="space-y-6" novalidate @submit.prevent="onSubmit">
    <section class="rounded-card border border-border bg-surface p-6">
      <h2 class="text-section font-semibold tracking-heading text-text">
        识别引擎
      </h2>
      <p class="mt-1 text-body text-text-secondary">
        决定每个抽取任务使用哪个引擎；自动模式按链路依次尝试。
      </p>

      <div class="mt-4">
        <FormField
          id="settings-provider"
          label="识别引擎"
          :error="errors.provider"
        >
          <template #label-extra>
            <SettingsSourceTag :source="sourceOf('provider')" />
          </template>
          <Select
            id="settings-provider"
            v-model="provider"
            :options="PROVIDER_OPTIONS"
            :invalid="Boolean(errors.provider)"
            :disabled="saving"
          />
        </FormField>
      </div>

      <div class="mt-4 space-y-2">
        <div class="flex items-center justify-between gap-2">
          <p
            id="settings-auto-chain-label"
            class="text-body font-medium text-text"
          >
            自动链路
          </p>
          <SettingsSourceTag :source="sourceOf('auto_chain')" />
        </div>
        <p class="text-meta text-text-muted">
          仅在自动模式下使用，按下列顺序依次尝试；未配置的引擎会被跳过。
        </p>
        <div
          class="flex flex-wrap gap-x-6 gap-y-1"
          role="group"
          aria-labelledby="settings-auto-chain-label"
        >
          <label
            v-for="option in CHAIN_OPTIONS"
            :key="option.value"
            class="inline-flex min-h-11 cursor-pointer items-center gap-2 text-body text-text md:min-h-9"
          >
            <input
              type="checkbox"
              class="size-4 rounded-tag border-border accent-primary"
              :checked="autoChain.includes(option.value)"
              :disabled="saving"
              @change="onChainChange(option.value, $event)"
            />
            {{ option.label }}
          </label>
        </div>
        <p
          v-if="errors.autoChain"
          class="text-meta text-danger"
          aria-live="polite"
        >
          {{ errors.autoChain }}
        </p>
      </div>
    </section>

    <section class="rounded-card border border-border bg-surface p-6">
      <h2 class="text-section font-semibold tracking-heading text-text">
        本地 PaddleOCR
      </h2>
      <p class="mt-1 text-body text-text-secondary">
        留空表示未配置，自动模式下会跳过该引擎。
      </p>

      <div class="mt-4">
        <FormField
          id="settings-paddleocr-endpoint"
          label="OCR 接口地址"
          :error="errors.paddleocrEndpoint"
          hint="例如 http://127.0.0.1:8866/predict/ocr_system"
        >
          <template #label-extra>
            <SettingsSourceTag :source="sourceOf('paddleocr_endpoint')" />
          </template>
          <Input
            id="settings-paddleocr-endpoint"
            v-model="paddleocrEndpoint"
            :invalid="Boolean(errors.paddleocrEndpoint)"
            :disabled="saving"
            placeholder="http://"
            autocomplete="off"
            spellcheck="false"
          />
        </FormField>
      </div>
    </section>

    <section class="rounded-card border border-border bg-surface p-6">
      <h2 class="text-section font-semibold tracking-heading text-text">
        多模态大模型
      </h2>
      <p class="mt-1 text-body text-text-secondary">
        调用 OpenAI 兼容接口识别发票图片，默认关闭。
      </p>

      <div class="mt-4">
        <ToggleField
          id="settings-llm-enabled"
          v-model="llmEnabled"
          label="启用多模态大模型"
          description="关闭时该引擎不参与识别，也不会向外发送任何图片。"
          :disabled="saving"
        >
          <template #label-extra>
            <SettingsSourceTag :source="sourceOf('llm_enabled')" />
          </template>
        </ToggleField>
      </div>

      <p
        class="mt-4 flex items-start gap-2 rounded-control border border-warning bg-warning-soft p-3 text-body text-warning"
      >
        <TriangleAlert
          class="mt-1 shrink-0"
          :size="16"
          :stroke-width="1.75"
          aria-hidden="true"
        />
        <span>启用后，发票图片会发送到下方填写的外部接口，请确认数据合规。</span>
      </p>

      <p
        v-if="errors.llmEnabled"
        class="mt-2 text-meta text-danger"
        aria-live="polite"
      >
        {{ errors.llmEnabled }}
      </p>

      <div class="mt-4 grid gap-4 sm:grid-cols-2">
        <FormField
          id="settings-llm-endpoint"
          label="接口地址"
          :error="errors.llmEndpoint"
          hint="OpenAI 兼容地址，如 https://api.example.com/v1"
        >
          <template #label-extra>
            <SettingsSourceTag :source="sourceOf('llm_endpoint')" />
          </template>
          <Input
            id="settings-llm-endpoint"
            v-model="llmEndpoint"
            :invalid="Boolean(errors.llmEndpoint)"
            :disabled="saving"
            placeholder="https://"
            autocomplete="off"
            spellcheck="false"
          />
        </FormField>

        <FormField
          id="settings-llm-model"
          label="模型名"
          :error="errors.llmModel"
        >
          <template #label-extra>
            <SettingsSourceTag :source="sourceOf('llm_model')" />
          </template>
          <Input
            id="settings-llm-model"
            v-model="llmModel"
            :invalid="Boolean(errors.llmModel)"
            :disabled="saving"
            placeholder="例如 gpt-4o-mini"
            autocomplete="off"
            spellcheck="false"
          />
        </FormField>
      </div>

      <div class="mt-4">
        <FormField
          id="settings-llm-api-key"
          label="API Key"
          :hint="
            settings.values.llm_api_key_set
              ? '已配置，留空表示保持不变。'
              : '尚未配置。'
          "
        >
          <template #label-extra>
            <SettingsSourceTag :source="sourceOf('llm_api_key')" />
          </template>
          <Input
            id="settings-llm-api-key"
            v-model="apiKey"
            type="password"
            :disabled="saving || clearApiKey"
            :invalid="Boolean(errors.llmEnabled)"
            :placeholder="
              settings.values.llm_api_key_set
                ? (settings.values.llm_api_key_hint ?? '已配置')
                : '填写后保存'
            "
            autocomplete="new-password"
            spellcheck="false"
            @input="onApiKeyInput"
          />
        </FormField>

        <div
          v-if="settings.values.llm_api_key_set"
          class="mt-2 flex items-center gap-2 text-meta text-text-secondary"
        >
          <template v-if="clearApiKey">
            <span>保存后将清除已配置的 API Key。</span>
            <Button
              variant="ghost"
              size="sm"
              :disabled="saving"
              @click="clearApiKey = false"
            >
              撤销清除
            </Button>
          </template>
          <template v-else>
            <span>
              当前已配置 {{ settings.values.llm_api_key_hint ?? 'API Key' }}。
            </span>
            <Button
              variant="ghost"
              size="sm"
              :disabled="saving"
              @click="clearApiKey = true"
            >
              清除已配置的 Key
            </Button>
          </template>
        </div>
      </div>
    </section>

    <section class="rounded-card border border-border bg-surface p-6">
      <h2 class="text-section font-semibold tracking-heading text-text">
        高级参数
      </h2>
      <p class="mt-1 text-body text-text-secondary">
        调整识别调用的超时与重试策略，一般保持默认即可。
      </p>

      <div class="mt-4 grid gap-4 sm:grid-cols-2">
        <FormField
          id="settings-prompt-version"
          label="Prompt 版本"
          :error="errors.promptVersion"
        >
          <template #label-extra>
            <SettingsSourceTag :source="sourceOf('prompt_version')" />
          </template>
          <Input
            id="settings-prompt-version"
            v-model="promptVersion"
            :invalid="Boolean(errors.promptVersion)"
            :disabled="saving"
            autocomplete="off"
            spellcheck="false"
          />
        </FormField>

        <FormField
          id="settings-http-timeout"
          label="HTTP 超时（秒）"
          :error="errors.httpTimeout"
        >
          <template #label-extra>
            <SettingsSourceTag :source="sourceOf('http_timeout')" />
          </template>
          <Input
            id="settings-http-timeout"
            v-model="httpTimeout"
            type="number"
            min="0.1"
            max="300"
            step="0.1"
            inputmode="decimal"
            :invalid="Boolean(errors.httpTimeout)"
            :disabled="saving"
          />
        </FormField>

        <FormField
          id="settings-max-attempts"
          label="最大尝试次数"
          :error="errors.maxAttempts"
        >
          <template #label-extra>
            <SettingsSourceTag :source="sourceOf('max_attempts')" />
          </template>
          <Input
            id="settings-max-attempts"
            v-model="maxAttempts"
            type="number"
            min="1"
            max="10"
            step="1"
            inputmode="numeric"
            :invalid="Boolean(errors.maxAttempts)"
            :disabled="saving"
          />
        </FormField>

        <FormField
          id="settings-stale-minutes"
          label="超时回收（分钟）"
          :error="errors.staleMinutes"
        >
          <template #label-extra>
            <SettingsSourceTag :source="sourceOf('stale_minutes')" />
          </template>
          <Input
            id="settings-stale-minutes"
            v-model="staleMinutes"
            type="number"
            min="1"
            max="1440"
            step="1"
            inputmode="numeric"
            :invalid="Boolean(errors.staleMinutes)"
            :disabled="saving"
          />
        </FormField>

        <FormField
          id="settings-backoff-seconds"
          label="退避基数（秒）"
          :error="errors.backoffSeconds"
        >
          <template #label-extra>
            <SettingsSourceTag :source="sourceOf('backoff_seconds')" />
          </template>
          <Input
            id="settings-backoff-seconds"
            v-model="backoffSeconds"
            type="number"
            min="0"
            max="3600"
            step="1"
            inputmode="numeric"
            :invalid="Boolean(errors.backoffSeconds)"
            :disabled="saving"
          />
        </FormField>
      </div>
    </section>

    <FormErrorAlert :message="error" />

    <div
      class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
    >
      <p class="text-meta text-text-muted">
        保存后对新入队任务与重试立即生效，正在运行的任务不受影响。
      </p>
      <div class="flex items-center gap-2">
        <Button
          variant="secondary"
          type="button"
          :disabled="saving"
          @click="emit('reset')"
        >
          恢复默认
        </Button>
        <Button type="submit" :loading="saving">保存设置</Button>
      </div>
    </div>
  </form>
</template>
