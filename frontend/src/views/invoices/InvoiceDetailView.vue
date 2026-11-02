<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue'
import PageHeader from '@/components/common/PageHeader.vue'
</script>

<template>
  <div>
    <PageHeader
      title="发票详情"
      description="查看发票字段、明细与付款分配。"
    back-to="/invoices"
    />
    <div class="rounded-card border border-border bg-surface">
      <EmptyState
        title="页面建设中"
        description="该模块正在建设中，稍后开放。"
      />
    </div>
  </div>
</template>
