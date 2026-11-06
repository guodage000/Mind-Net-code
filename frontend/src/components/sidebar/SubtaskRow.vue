<template>
  <div class="subtask-row" :class="{ done: node.status === 'done', overdue: overdue }"
       :style="{ paddingLeft: depth * 16 + 28 + 'px' }" @click="$emit('open', { noteId: node.noteId, line: node.line })">
    <span class="sub-status" :style="{ color: statusColor }">{{ statusIcon }}</span>
    <span class="sub-body">{{ node.body }}</span>
    <span v-if="node.priority" class="sub-prio" :class="'p-' + node.priority">{{ prioLabel }}</span>
    <span v-if="node.date" class="sub-date">{{ node.date }}{{ node.time ? ' ' + node.time : '' }}</span>
  </div>
  <template v-if="node.children.length">
    <SubtaskRow v-for="child in node.children" :key="child.line"
                :node="child" :depth="depth + 1" @open="$emit('open', $event)" />
  </template>
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
const PRIO_LABEL = { high: '高', medium: '中', low: '低' }

const statusColor = computed(() => STATUS_COLOR[props.node.status] || STATUS_COLOR.todo)
const statusIcon = computed(() => STATUS_ICON[props.node.status] || STATUS_ICON.todo)
const prioLabel = computed(() => PRIO_LABEL[props.node.priority] || '')
const overdue = computed(() => props.node.status !== 'done' && props.node.date && isOverdue(props.node.date, props.node.time))
</script>

<style scoped>
.subtask-row { display: flex; align-items: center; gap: 5px; padding: 3px 8px 3px 0;
               border-radius: 4px; cursor: pointer; font-size: 12px; }
.subtask-row:hover { background: var(--color-surface2); }
.subtask-row.done { opacity: .55; }
.subtask-row.done .sub-body { text-decoration: line-through; }
.subtask-row.overdue { background: rgba(243,139,168,.08); }
.sub-status { font-size: 10px; flex-shrink: 0; }
.sub-body { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
.sub-prio { font-size: 9px; border: 1px solid currentColor; border-radius: 3px; padding: 0 2px; flex-shrink: 0; }
.sub-prio.p-high { color: var(--color-danger); }
.sub-prio.p-medium { color: var(--color-warn); }
.sub-prio.p-low { color: var(--color-text-dim); }
.sub-date { font-size: 10px; color: var(--color-text-dim); flex-shrink: 0; }
</style>
