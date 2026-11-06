<template>
  <div class="git-badge" :class="statusClass" :title="tooltip" @click="manualSync">
    <span>⎇</span>
    <span v-if="status.pending_changes > 0">{{ status.pending_changes }}</span>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { gitApi } from '../../composables/useApi'
const status = ref({ enabled: false, pending_changes: 0, last_sync: null, error: null })
const statusClass = computed(() => {
  if (!status.value.enabled) return 'disabled'
  if (status.value.error) return 'error'
  if (status.value.pending_changes > 0) return 'pending'
  return 'synced'
})
const tooltip = computed(() => {
  if (!status.value.enabled) return 'Git 未初始化'
  if (status.value.error) return '同步错误: ' + status.value.error
  if (status.value.pending_changes > 0) return status.value.pending_changes + ' 个变更待同步'
  return '已同步 ' + (status.value.last_sync?.slice(0,16) || ''  )
})
async function refresh() { const r = await gitApi.status(); status.value = r.data }
async function manualSync() { await gitApi.sync(); await refresh() }
let timer = null
onMounted(() => { refresh(); timer = setInterval(refresh, 30000) })
onBeforeUnmount(() => clearInterval(timer))
</script>

<style scoped>
.git-badge { position: fixed; bottom: 16px; right: 16px; display: flex; align-items: center;
             gap: 4px; padding: 5px 10px; border-radius: 20px; font-size: 12px;
             cursor: pointer; background: var(--color-surface2); border: 1px solid var(--color-border); }
.synced  { border-color: var(--color-success); color: var(--color-success); }
.pending { border-color: var(--color-warn);    color: var(--color-warn); }
.error   { border-color: var(--color-danger);  color: var(--color-danger); }
.disabled{ opacity: .4; }
</style>
