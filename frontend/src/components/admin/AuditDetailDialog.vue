<script setup lang="ts">
import { computed } from 'vue'

import type { AuditLog } from '@/api/types'
import DateText from '@/components/common/DateText.vue'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import { formatDateTime } from '@/lib/date'
import { EMPTY_TEXT, emptyText } from '@/lib/format'
import {
  auditActorLabel,
  auditEntityLabel,
  formatAuditJson,
} from './audit-format'

const props = defineProps<{
  log: AuditLog | null
}>()

const open = defineModel<boolean>('open', { default: false })

const dialogDescription = computed(() =>
  props.log
    ? `${props.log.action} · ${formatDateTime(props.log.created_at)}`
    : undefined,
)

const beforeJson = computed(() => formatAuditJson(props.log?.before ?? null))
const afterJson = computed(() => formatAuditJson(props.log?.after ?? null))

const actor = computed(() =>
  props.log ? auditActorLabel(props.log) : EMPTY_TEXT,
)
const entity = computed(() =>
  props.log ? auditEntityLabel(props.log) : EMPTY_TEXT,
)

const ip = computed(() => emptyText(props.log?.ip))
const userAgent = computed(() => emptyText(props.log?.user_agent))
</script>

<template>
  <Dialog
    v-model:open="open"
    title="审计详情"
    :description="dialogDescription"
    width="lg"
  >
    <div v-if="log" class="space-y-5">
      <dl class="grid gap-4 sm:grid-cols-2">
        <div>
          <dt class="text-meta text-text-muted">时间</dt>
          <dd class="mt-0.5">
            <DateText :value="log.created_at" mode="datetime" />
          </dd>
        </div>

        <div>
          <dt class="text-meta text-text-muted">操作人</dt>
          <dd class="mt-0.5 text-body text-text">{{ actor }}</dd>
        </div>

        <div>
          <dt class="text-meta text-text-muted">动作</dt>
          <dd class="mt-0.5 font-mono text-table text-text">{{ log.action }}</dd>
        </div>

        <div>
          <dt class="text-meta text-text-muted">实体</dt>
          <dd class="mt-0.5 font-mono text-table text-text">{{ entity }}</dd>
        </div>

        <div>
          <dt class="text-meta text-text-muted">IP</dt>
          <dd class="mt-0.5 font-mono text-table text-text">{{ ip }}</dd>
        </div>

        <div class="sm:col-span-2">
          <dt class="text-meta text-text-muted">User-Agent</dt>
          <dd class="mt-0.5 break-words font-mono text-table text-text-secondary">
            {{ userAgent }}
          </dd>
        </div>
      </dl>

      <section class="space-y-2">
        <h3 class="text-heading font-semibold text-text">变更前</h3>
        <pre
          class="max-h-64 overflow-auto whitespace-pre-wrap break-words rounded-control border border-border bg-surface-muted p-3 font-mono text-meta text-text"
          aria-label="变更前 JSON"
        >{{ beforeJson }}</pre>
      </section>

      <section class="space-y-2">
        <h3 class="text-heading font-semibold text-text">变更后</h3>
        <pre
          class="max-h-64 overflow-auto whitespace-pre-wrap break-words rounded-control border border-border bg-surface-muted p-3 font-mono text-meta text-text"
          aria-label="变更后 JSON"
        >{{ afterJson }}</pre>
      </section>
    </div>

    <template #footer>
      <Button variant="secondary" @click="open = false">关闭</Button>
    </template>
  </Dialog>
</template>
