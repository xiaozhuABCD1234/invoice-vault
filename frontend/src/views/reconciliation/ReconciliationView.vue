<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue'
import PageHeader from '@/components/common/PageHeader.vue'
</script>

<template>
  <div>
    <PageHeader
      title="对账"
      description="查看未付款、未分配与异常缺口。"
    />
    <div class="rounded-card border border-border bg-surface">
      <EmptyState
        title="页面建设中"
        description="该模块正在建设中，稍后开放。"
      />
    </div>
  </div>
</template>
