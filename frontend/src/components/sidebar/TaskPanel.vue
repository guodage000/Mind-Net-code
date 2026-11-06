<template>
  <div class="task-panel">
    <div class="task-head">
      <span>任务</span>
      <button class="icon-btn" title="刷新" @click="refresh">⟳</button>
    </div>

    <div class="status-tabs">
      <button v-for="s in groups" :key="s.key" class="status-tab"
              :class="{ active: filter === s.key }" :style="{ '--c': s.color }"
              @click="filter = filter === s.key ? '' : s.key">
        <span class="dot">{{ s.icon }}</span>{{ s.label }}
        <span class="count">{{ countOf(s.key) }}</span>
      </button>
    </div>

    <div class="sort-row">
      <button class="sort-btn" :class="{ on: sortBy === 'updated' }" @click="sortBy = 'updated'">按更新</button>
      <button class="sort-btn" :class="{ on: sortBy === 'deadline' }" @click="sortBy = 'deadline'">按截止</button>
      <button class="sort-btn" :class="{ on: sortBy === 'priority' }" @click="sortBy = 'priority'">按优先级</button>
    </div>

    <div class="task-scroll" @dragover.prevent="onDragOver" @drop.prevent="onDropToRoot">
      <template v-if="visibleTasks.length">
        <div v-for="task in visibleTasks" :key="task.id" class="task-item"
             :class="{ 'drag-over': dragOverId === task.id }"
             @dragover.prevent.stop="onDragOverTask(task.id, $event)"
             @drop.prevent.stop="onDropOnTask(task.id, $event)">
          <!-- 父任务行 -->
          <div class="task-row" :class="{ overdue: isOverdueTask(task), done: task.status === 'done' }"
               :draggable="true"
               @dragstart="onDragStart(task.id, $event)"
               @dragend="onDragEnd"
               @click="$emit('open', task.id)">
            <button v-if="task.subtaskIds.length" class="expand-btn"
                    :class="{ open: expanded.has(task.id) }" @click.stop="toggleExpand(task.id)">
              {{ expanded.has(task.id) ? '▾' : '▸' }}
            </button>
            <span v-else class="expand-placeholder" />
            <span class="task-dot" :style="{ color: statusOf(task.status).color }"
                  :title="statusOf(task.status).label">{{ statusOf(task.status).icon }}</span>
            <span class="task-title" :class="{ done: task.status === 'done' }">{{ task.title }}</span>
            <span v-if="task.priority === 'high'" class="prio">高</span>
            <span class="task-meta-inline">
              <span v-if="task.deadline" class="deadline" :class="{ overdue: isOverdueTask(task) }">
                {{ isOverdueTask(task) ? '逾期 ' : '' }}{{ task.deadline }}{{ task.time ? ' ' + task.time : '' }}
              </span>
              <span v-if="task.subtaskIds.length" class="progress">{{ subtaskDone(task.id) }}/{{ task.subtaskIds.length }} 项</span>
            </span>
            <select class="status-select" :value="task.status"
                    :title="'改为 ' + statusOf(task.status).label"
                    @change="change(task, $event.target.value)" @click.stop>
              <option v-for="s in TASK_STATUSES" :key="s.key" :value="s.key">{{ s.label }}</option>
            </select>
          </div>

          <!-- 子任务（独立笔记，展开时显示） -->
          <template v-if="expanded.has(task.id)">
            <div v-for="subId in task.subtaskIds" :key="subId" class="subtask-item">
              <SubtaskNote :note-id="subId" :depth="1" @open="$emit('open', $event)" @refresh="refresh"
                           @drag-start="onDragStart" @drag-end="onDragEnd" />
            </div>
          </template>
        </div>
      </template>
      <div v-else class="empty">
        还没有任务。点左上角 ＋ 新建，类型选「任务」。
      </div>

      <!-- 拖拽提示 -->
      <div v-if="dragging" class="drag-hint">
        {{ dragHint }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useNotesStore } from '../../stores/notes'
import { taskApi } from '../../composables/useApi'
import { TASK_STATUSES, statusMeta } from '../../composables/tasks'
import { isOverdue } from '../../composables/taskMarkers'
import SubtaskNote from './SubtaskNote.vue'

const emit = defineEmits(['open'])
const store = useNotesStore()
const filter = ref('')
const sortBy = ref('updated')
const groups = TASK_STATUSES
const expanded = ref(new Set())

const statusOf = key => statusMeta(key)
const countOf = key => store.taskCounts[key] || 0

const PRIO_ORDER = { high: 0, medium: 1, low: 2, null: 3 }

// 拖拽状态
const dragging = ref(false)
const dragOverId = ref(null)
const dragSourceId = ref(null)

const visibleTasks = computed(() => {
  // 只显示顶层任务（没有 parent_id 的），子任务在父任务下面展开显示
  let list = store.tasks.filter(t => !t.parentId)
  if (filter.value) list = list.filter(t => t.status === filter.value)
  if (sortBy.value === 'deadline') {
    list = [...list].sort((a, b) => {
      const da = a.deadline ? (a.deadline + (a.time || '23:59')) : '9999'
      const db = b.deadline ? (b.deadline + (b.time || '23:59')) : '9999'
      return da.localeCompare(db)
    })
  } else if (sortBy.value === 'priority') {
    list = [...list].sort((a, b) => (PRIO_ORDER[a.priority] ?? 3) - (PRIO_ORDER[b.priority] ?? 3))
  }
  return list
})

const dragHint = computed(() => {
  if (!dragging.value) return ''
  if (dragOverId.value) {
    const target = store.tasks.find(t => t.id === dragOverId.value)
    return `拖到「${target?.title}」下作为子任务`
  }
  return '拖到空白区域，变成独立顶层任务'
})

function isOverdueTask(task) {
  if (task.status === 'done' || !task.deadline) return false
  return isOverdue(task.deadline, task.time)
}

function toggleExpand(id) {
  if (expanded.value.has(id)) expanded.value.delete(id)
  else expanded.value.add(id)
  expanded.value = new Set(expanded.value)
}

// 子任务完成数（从 store 里取子任务的状态）
function subtaskDone(parentId) {
  const task = store.tasks.find(t => t.id === parentId)
  if (!task || !task.subtaskIds.length) return 0
  return task.subtaskIds.filter(subId => {
    const sub = store.tasks.find(t => t.id === subId)
    return sub && sub.status === 'done'
  }).length
}

// ── 拖拽 ────────────────────────────────────────────────────────────────────
function onDragStart(taskId, event) {
  dragging.value = true
  dragSourceId.value = taskId
  event.dataTransfer.setData('text/plain', taskId)
  event.dataTransfer.effectAllowed = 'move'
}

function onDragEnd() {
  dragging.value = false
  dragOverId.value = null
  dragSourceId.value = null
}

function onDragOverTask(taskId, event) {
  if (!dragging.value || dragSourceId.value === taskId) return
  dragOverId.value = taskId
  event.dataTransfer.dropEffect = 'move'
}

function onDragOver(event) {
  if (!dragging.value) return
  dragOverId.value = null
  event.dataTransfer.dropEffect = 'move'
}

async function onDropOnTask(targetId, event) {
  const sourceId = event.dataTransfer.getData('text/plain')
  if (!sourceId || sourceId === targetId) return
  event.dataTransfer.dropEffect = 'move'
  try {
    await taskApi.move(sourceId, targetId)
    await refresh()
    emit('open', sourceId)
  } catch (err) {
    alert('移动失败：' + (err.response?.data?.detail || err.message))
  }
  onDragEnd()
}

async function onDropToRoot(event) {
  const sourceId = event.dataTransfer.getData('text/plain')
  if (!sourceId) return
  // 拖到空白区域，变成顶层任务
  try {
    await taskApi.move(sourceId, null)
    await refresh()
  } catch (err) {
    alert('移动失败：' + (err.response?.data?.detail || err.message))
  }
  onDragEnd()
}

async function refresh() {
  await store.fetchTasks()
}

async function change(task, status) {
  const res = await taskApi.setStatus(task.id, status)
  task.status = res.data.status || status
  if (store.currentNote?.id === task.id) store.currentNote = res.data
  await store.fetchTasks()
}

onMounted(refresh)
defineExpose({ refresh })
</script>

<style scoped>
.task-panel { display: flex; flex-direction: column; flex: 1; min-height: 0; }
.task-head { display: flex; align-items: center; justify-content: space-between;
             padding: 8px 12px 4px; font-size: 11px; font-weight: 600; letter-spacing: .08em;
             text-transform: uppercase; color: var(--color-text-dim); }
.icon-btn { background: none; border: none; color: var(--color-text-dim); font-size: 14px;
            padding: 0 4px; border-radius: 4px; }
.icon-btn:hover { background: var(--color-border); color: var(--color-text); }
.status-tabs { display: flex; flex-wrap: wrap; gap: 4px; padding: 4px 10px 6px;
               border-bottom: 1px solid var(--color-border); }
.status-tab { display: flex; align-items: center; gap: 4px; font-size: 12px; padding: 3px 8px;
              border-radius: 12px; border: 1px solid var(--color-border); background: none;
              color: var(--color-text-dim); }
.status-tab.active { border-color: var(--c); color: var(--c); }
.dot { color: var(--c); font-size: 11px; }
.count { opacity: .7; }
.sort-row { display: flex; gap: 4px; padding: 6px 10px; border-bottom: 1px solid var(--color-border); }
.sort-btn { background: none; border: 1px solid var(--color-border); color: var(--color-text-dim);
            font-size: 11px; padding: 2px 8px; border-radius: 10px; }
.sort-btn.on { border-color: var(--color-accent); color: var(--color-accent); }
.task-scroll { flex: 1; overflow-y: auto; padding: 4px 0; position: relative; }
.task-item { padding: 2px 0; }
.task-item.drag-over { background: rgba(137, 180, 250, .1); border-radius: 4px; }
.task-row { display: flex; align-items: center; gap: 4px; padding: 5px 10px 5px 8px;
            cursor: pointer; font-size: 13px; cursor: grab; }
.task-row:active { cursor: grabbing; }
.task-row:hover { background: var(--color-surface2); }
.task-row.overdue { background: rgba(243,139,168,.08); }
.task-row.done .task-title { text-decoration: line-through; color: var(--color-text-dim); }
.expand-btn { background: none; border: none; color: var(--color-text-dim); font-size: 12px;
              padding: 0 2px; width: 16px; flex-shrink: 0; cursor: pointer; }
.expand-btn:hover { color: var(--color-text); }
.expand-placeholder { width: 16px; flex-shrink: 0; }
.task-dot { font-size: 11px; flex-shrink: 0; }
.task-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
.prio { font-size: 10px; color: var(--color-danger); border: 1px solid var(--color-danger);
        border-radius: 3px; padding: 0 3px; flex-shrink: 0; }
.task-meta-inline { display: flex; gap: 6px; font-size: 11px; color: var(--color-text-dim); flex-shrink: 0; }
.deadline.overdue { color: var(--color-danger); font-weight: 600; }
.progress { font-size: 11px; }
.status-select { background: var(--color-surface2); color: var(--color-text); font-size: 11px;
                 border: 1px solid var(--color-border); border-radius: 4px; padding: 2px 2px;
                 max-width: 68px; flex-shrink: 0; }
.subtask-item { padding-left: 0; }
.empty { padding: 16px 12px; color: var(--color-text-dim); font-size: 13px; line-height: 1.7; }
.drag-hint { position: sticky; bottom: 8px; margin: 8px 12px; padding: 8px 12px;
             background: var(--color-accent); color: var(--color-bg); border-radius: 6px;
             font-size: 12px; text-align: center; pointer-events: none; }
</style>
