<template>
  <div class="subtask-item">
    <div class="st-row" :class="{ done: node.status === 'done', overdue: overdue }"
         :style="{ paddingLeft: depth * 16 + 8 + 'px' }" @click="$emit('open', { noteId: node.noteId, line: node.line })">
      <span class="st-status" :style="{ color: statusColor }">{{ statusIcon }}</span>
      <span class="st-body">{{ node.body }}</span>
      <span v-if="node.priority" class="st-prio" :class="'p-' + node.priority">{{ node.priority === 'high' ? '高' : node.priority === 'medium' ? '中' : '低' }}</span>
      <span v-if="node.date" class="st-date">{{ node.date }}{{ node.time ? ' ' + node.time : '' }}</span>
    </div>
    <template v-if="node.children.length">
      <SubtaskNode v-for="child in node.children" :key="child.line"
                   :node="child" :depth="depth + 1" @open="$emit('open', $event)" />
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { isOverdue } from '../../composables/taskMarkers'

const props = defineProps({
  node: Object,
  depth: { type: Number, default: 0 },
})
defineEmits(['open'])

const STATUS_COLOR = { todo: 'var(--color-text-dim)', in_progress: 'var(--color-warn)', done: 'var(--color-success)', blocked: 'var(--color-danger)' }
const STATUS_ICON = { todo: '○', in_progress: '◐', done: '●', blocked: '‖' }
const statusColor = computed(() => STATUS_COLOR[props.node.status] || STATUS_COLOR.todo)
const statusIcon = computed(() => STATUS_ICON[props.node.status] || STATUS_ICON.todo)
const overdue = computed(() => props.node.status !== 'done' && props.node.date && isOverdue(props.node.date, props.node.time))
</script>

<style scoped>
.st-row { display: flex; align-items: center; gap: 6px; padding: 4px 8px 4px 0;
          border-radius: 4px; cursor: pointer; font-size: 13px; }
.st-row:hover { background: var(--color-surface2); }
.st-row.done { opacity: .55; }
.st-row.done .st-body { text-decoration: line-through; }
.st-row.overdue { background: rgba(243,139,168,.08); }
.st-status { font-size: 11px; flex-shrink: 0; }
.st-body { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.st-prio { font-size: 10px; border: 1px solid currentColor; border-radius: 3px; padding: 0 3px; flex-shrink: 0; }
.st-prio.p-high { color: var(--color-danger); }
.st-prio.p-medium { color: var(--color-warn); }
.st-prio.p-low { color: var(--color-text-dim); }
.st-date { font-size: 11px; color: var(--color-text-dim); flex-shrink: 0; }
</style>
