<template>
  <div class="info-panel">
    <div class="info-section">
      <div class="info-label">类型</div>
      <div class="info-value">
        {{ typeLabel }}
        <span v-if="note.parent_id" class="parent-link" @click="openParent" title="点回父任务">
          ← {{ parentTitle }}
        </span>
      </div>
    </div>

    <div class="info-section">
      <div class="info-label">状态{{ note.note_type === 'task' ? '' : '（普通笔记也能标状态）' }}</div>
      <div class="status-row">
        <button v-for="s in TASK_STATUSES" :key="s.key" class="status-btn"
                :class="{ active: currentStatus === s.key }"
                :style="{ '--c': s.color }" @click="setStatus(s.key)">
          <span class="dot">{{ s.icon }}</span>{{ s.label }}
        </button>
      </div>
    </div>

    <div class="info-section">
      <div class="info-label">优先级</div>
      <div class="status-row">
        <button v-for="p in PRIORITIES" :key="p.key" class="prio-btn"
                :class="{ active: note.priority === p.key }" @click="setPriority(p.key)">{{ p.label }}</button>
        <button class="prio-btn" :class="{ active: !note.priority }" @click="setPriority('')">无</button>
      </div>
    </div>

    <div class="info-section">
      <div class="info-label">截止日期</div>
      <input type="date" class="date-input" :value="note.deadline || ''" @change="setDeadline($event.target.value)" />
    </div>

    <div class="info-section">
      <div class="info-label">标签（点击编辑）</div>
      <div v-if="!editingTags" class="tags-list" @click="startEditTags">
        <span v-for="t in note.tags" :key="t" class="tag">{{ t }}</span>
        <span v-if="!note.tags.length" class="tag empty">＋ 添加标签</span>
      </div>
      <div v-else class="tags-edit">
        <input v-model="tagsInput" class="tags-input" placeholder="工作, 学习（逗号分隔）"
               @keydown.enter="saveTags" @keydown.escape="editingTags = false" ref="tagsInputEl" />
        <div class="tags-actions">
          <button class="mini" @click="saveTags">保存</button>
          <button class="mini" @click="editingTags = false">取消</button>
        </div>
      </div>
    </div>

    <div class="info-section" v-if="stats.total">
      <div class="info-label">清单进度</div>
      <div class="progress-line">{{ stats.finished }} / {{ stats.total }} 项已完成</div>
      <div class="progress-bar"><div class="progress-fill" :style="{ width: pct + '%' }" /></div>
    </div>

    <div class="info-section">
      <div class="info-label">更新时间</div>
      <div class="info-value">{{ note.updated_at.slice(0, 16).replace('T', ' ') }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, nextTick } from 'vue'
import { useNotesStore } from '../../stores/notes'
import { TASK_STATUSES, PRIORITIES } from '../../composables/tasks'

const props = defineProps({ note: Object })
const store = useNotesStore()

const TYPE_MAP = { note: '普通笔记', task: '任务', ai_summary: 'AI 总结' }
const typeLabel = computed(() => {
  const base = TYPE_MAP[props.note.note_type] || props.note.note_type
  return props.note.parent_id ? '子任务' : base
})

// 父任务标题（从 store 里找）
const parentTitle = computed(() => {
  if (!props.note.parent_id) return ''
  const parent = store.tasks.find(t => t.id === props.note.parent_id)
  return parent?.title || '父任务'
})

function openParent() {
  if (props.note.parent_id) {
    store.openNote(props.note.parent_id)
  }
}

// 没有状态的任务显示成"待做"
const currentStatus = computed(() =>
  props.note.status || (props.note.note_type === 'task' ? 'todo' : ''))

const stats = computed(() => {
  const boxes = (props.note.content || '').match(/^\s*[-*+]\s+\[([ xX/])\]/gm) || []
  const finished = boxes.filter(b => /\[[xX]\]$/.test(b.trim())).length
  return { total: boxes.length, finished }
})
const pct = computed(() => stats.value.total ? Math.round(stats.value.finished / stats.value.total * 100) : 0)

// ── 标签编辑 ────────────────────────────────────────────────────────────────
const editingTags = ref(false)
const tagsInput = ref('')
const tagsInputEl = ref(null)

function startEditTags() {
  tagsInput.value = props.note.tags.join(', ')
  editingTags.value = true
  nextTick(() => tagsInputEl.value?.focus())
}

async function saveTags() {
  const tags = tagsInput.value.split(/[,，]/).map(t => t.trim()).filter(Boolean)
  await store.saveNote(props.note.id, { tags })
  editingTags.value = false
  await store.fetchTags()
}

async function setStatus(key) {
  await store.saveNote(props.note.id, { status: key })
  await store.fetchTasks()
}

async function setPriority(key) {
  await store.saveNote(props.note.id, { priority: key || null })
}

async function setDeadline(value) {
  await store.saveNote(props.note.id, { deadline: value || null })
}
</script>

<style scoped>
.info-panel { padding: 16px; }
.info-section { margin-bottom: 16px; }
.info-label { font-size: 11px; text-transform: uppercase; letter-spacing: .06em;
              color: var(--color-text-dim); margin-bottom: 6px; line-height: 1.5; }
.info-value { font-size: 13px; }
.status-row { display: flex; flex-wrap: wrap; gap: 4px; }
.status-btn, .prio-btn { display: flex; align-items: center; gap: 3px; font-size: 12px;
              background: var(--color-surface2); border: 1px solid var(--color-border);
              color: var(--color-text-dim); border-radius: 10px; padding: 3px 8px; }
.status-btn.active { border-color: var(--c); color: var(--c); }
.status-btn .dot { font-size: 10px; color: var(--c); }
.prio-btn.active { border-color: var(--color-accent); color: var(--color-accent); }
.date-input { background: var(--color-surface2); border: 1px solid var(--color-border);
              color: var(--color-text); border-radius: 6px; padding: 5px 8px; font-size: 13px; }
.tags-list { display: flex; flex-wrap: wrap; gap: 4px; cursor: pointer; }
.parent-link { color: var(--color-accent); cursor: pointer; margin-left: 6px; }
.parent-link:hover { text-decoration: underline; }
.tag { background: var(--color-surface2); color: var(--color-accent2); font-size: 11px;
       padding: 2px 8px; border-radius: 12px; }
.tag.empty { color: var(--color-text-dim); border: 1px dashed var(--color-border); background: none; }
.tags-edit { display: flex; flex-direction: column; gap: 6px; }
.tags-input { background: var(--color-surface2); border: 1px solid var(--color-accent);
              color: var(--color-text); border-radius: 6px; padding: 6px 8px; font-size: 13px; outline: none; }
.tags-actions { display: flex; gap: 6px; }
.mini { background: var(--color-surface2); border: 1px solid var(--color-border); color: var(--color-text);
        font-size: 12px; padding: 4px 10px; border-radius: 5px; }
.mini:hover { border-color: var(--color-accent); }
.progress-line { font-size: 12px; margin-bottom: 5px; }
.progress-bar { height: 5px; background: var(--color-surface2); border-radius: 3px; overflow: hidden; }
.progress-fill { height: 100%; background: var(--color-success); }
</style>
