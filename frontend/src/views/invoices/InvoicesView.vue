<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue'
import PageHeader from '@/components/common/PageHeader.vue'
</script>

<template>
  <div>
    <PageHeader
      title="发票"
      description="查询、维护发票及其明细。"
    />
    <div class="rounded-card border border-border bg-surface">
      <EmptyState
        title="页面建设中"
        description="该模块正在建设中，稍后开放。"
      />
    </div>
  </div>
</template>
