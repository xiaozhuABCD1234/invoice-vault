<script setup lang="ts">
import { computed } from 'vue'

import MoneyText from '@/components/common/MoneyText.vue'
import type { JsonObject } from '@/api/types'

import { normalizeDiff } from './extraction-diff'

const props = defineProps<{
  diff: JsonObject | null
}>()

const entries = computed(() => normalizeDiff(props.diff))

function isMoneyKey(key: string): boolean {
  return /(_cents|Cents)$/.test(key)
}

function centsOf(text: string): number | null {
  const value = Number(text)
  return Number.isSafeInteger(value) ? value : null
}
</script>

<template>
  <section
    v-if="entries.length > 0"
    class="rounded-card border border-border bg-surface p-4"
    aria-labelledby="review-diff-title"
  >
    <h3 id="review-diff-title" class="text-heading font-semibold text-text">
      与上次结果的差异
    </h3>
    <p class="mt-1 text-body text-text-secondary">
      下列字段与上一次抽取或审核结果不同，请重点核对。
    </p>

    <div class="mt-3 overflow-x-auto">
      <table class="w-full border-collapse text-table">
        <thead>
          <tr>
            <th
              scope="col"
              class="whitespace-nowrap border-b border-border bg-surface-muted px-3 py-2 text-left font-medium text-text-secondary"
            >
              字段
            </th>
            <th
              scope="col"
              class="whitespace-nowrap border-b border-border bg-surface-muted px-3 py-2 text-left font-medium text-text-secondary"
            >
              上次值
            </th>
            <th
              scope="col"
              class="whitespace-nowrap border-b border-border bg-surface-muted px-3 py-2 text-left font-medium text-text-secondary"
            >
              本次值
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="entry in entries"
            :key="entry.key"
            class="border-b border-border last:border-b-0"
          >
            <th
              scope="row"
              class="whitespace-nowrap px-3 py-2 text-left font-medium text-text-secondary"
            >
              {{ entry.label }}
            </th>
            <td class="whitespace-pre-wrap break-words px-3 py-2 text-text-muted">
              <MoneyText
                v-if="isMoneyKey(entry.key)"
                :cents="centsOf(entry.previous)"
                align="left"
              />
              <template v-else>{{ entry.previous }}</template>
            </td>
            <td class="whitespace-pre-wrap break-words px-3 py-2 text-text">
              <MoneyText
                v-if="isMoneyKey(entry.key)"
                :cents="centsOf(entry.next)"
                align="left"
              />
              <template v-else>{{ entry.next }}</template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
