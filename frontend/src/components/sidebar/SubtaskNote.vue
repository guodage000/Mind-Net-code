<template>
  <div class="subtask-note">
    <div class="st-row" :class="{ done: note.status === 'done', overdue: overdue }"
         :style="{ paddingLeft: depth * 16 + 28 + 'px' }"
         :draggable="true"
         @dragstart="$emit('drag-start', note.id, $event)"
         @dragend="$emit('drag-end')"
         @click="$emit('open', note.id)">
      <button v-if="hasSubtasks" class="expand-btn"
              :class="{ open: expanded }" @click.stop="expanded = !expanded">
        {{ expanded ? '▾' : '▸' }}
      </button>
      <span v-else class="expand-placeholder" />
      <span class="st-status" :style="{ color: statusColor }">{{ statusIcon }}</span>
      <span class="st-body">{{ note.title }}</span>
      <span v-if="note.priority" class="st-prio" :class="'p-' + note.priority">{{ prioLabel }}</span>
      <span v-if="note.deadline" class="st-date">{{ note.deadline }}{{ note.time ? ' ' + note.time : '' }}</span>
      <select class="st-select" :value="note.status" @change="change($event.target.value)" @click.stop>
        <option v-for="s in TASK_STATUSES" :key="s.key" :value="s.key">{{ s.label }}</option>
      </select>
    </div>
    <template v-if="expanded">
      <SubtaskNote v-for="subId in note.subtask_ids" :key="subId"
                   :note-id="subId" :depth="depth + 1" @open="$emit('open', $event)" @refresh="$emit('refresh')" />
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { notesApi, taskApi } from '../../composables/useApi'
import { TASK_STATUSES } from '../../composables/tasks'
import { isOverdue } from '../../composables/taskMarkers'

const props = defineProps({
  noteId: String,
  depth: { type: Number, default: 1 },
})
const emit = defineEmits(['open', 'refresh', 'drag-start', 'drag-end'])

const note = ref({ id: props.noteId, title: '加载中...', status: 'todo', subtask_ids: [] })
const expanded = ref(false)

const STATUS_COLOR = { todo: 'var(--color-text-dim)', in_progress: 'var(--color-warn)', done: 'var(--color-success)', blocked: 'var(--color-danger)' }
const STATUS_ICON = { todo: '○', in_progress: '◐', done: '●', blocked: '‖' }
const PRIO_LABEL = { high: '高', medium: '中', low: '低' }

const statusColor = computed(() => STATUS_COLOR[note.value.status] || STATUS_COLOR.todo)
const statusIcon = computed(() => STATUS_ICON[note.value.status] || STATUS_ICON.todo)
const prioLabel = computed(() => PRIO_LABEL[note.value.priority] || '')
const overdue = computed(() => note.value.status !== 'done' && note.value.deadline && isOverdue(note.value.deadline, note.value.time))
const hasSubtasks = computed(() => note.value.subtask_ids && note.value.subtask_ids.length > 0)

onMounted(async () => {
  try {
    const res = await notesApi.get(props.noteId)
    note.value = res.data
  } catch {
    note.value.title = '加载失败'
  }
})

async function change(status) {
  try {
    const res = await taskApi.setStatus(props.noteId, status)
    note.value = res.data
    emit('refresh')
  } catch (err) {
    alert('改状态失败：' + err.message)
  }
}
</script>

<style scoped>
.subtask-note { padding: 2px 0; }
.st-row { display: flex; align-items: center; gap: 5px; padding: 4px 8px 4px 0;
          border-radius: 4px; cursor: pointer; font-size: 12px; cursor: grab; }
.st-row:active { cursor: grabbing; }
.st-row:hover { background: var(--color-surface2); }
.st-row.done { opacity: .55; }
.st-row.done .st-body { text-decoration: line-through; }
.st-row.overdue { background: rgba(243,139,168,.08); }
.expand-btn { background: none; border: none; color: var(--color-text-dim); font-size: 11px;
              padding: 0 2px; width: 14px; flex-shrink: 0; cursor: pointer; }
.expand-btn:hover { color: var(--color-text); }
.expand-placeholder { width: 14px; flex-shrink: 0; }
.st-status { font-size: 10px; flex-shrink: 0; }
.st-body { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
.st-prio { font-size: 9px; border: 1px solid currentColor; border-radius: 3px; padding: 0 2px; flex-shrink: 0; }
.st-prio.p-high { color: var(--color-danger); }
.st-prio.p-medium { color: var(--color-warn); }
.st-prio.p-low { color: var(--color-text-dim); }
.st-date { font-size: 10px; color: var(--color-text-dim); flex-shrink: 0; }
.st-select { background: var(--color-surface2); color: var(--color-text); font-size: 10px;
             border: 1px solid var(--color-border); border-radius: 3px; padding: 1px 2px;
             max-width: 62px; flex-shrink: 0; }
</style>
