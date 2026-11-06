<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="dialog">
      <h3>新建笔记</h3>
      <label>标题
        <input ref="titleEl" v-model="form.title" placeholder="例如：准备下周汇报" @keydown.enter="create" />
      </label>
      <label>类型
        <select v-model="form.note_type">
          <option value="note">普通笔记 · 记录技术点</option>
          <option value="task">任务 · 带子任务清单</option>
          <option value="ai_summary">AI 总结 · 存放 AI 生成的内容</option>
        </select>
      </label>
      <label v-if="form.note_type === 'task'">挂在哪个任务下（可选）
        <select v-model="form.parent_id">
          <option value="">作为独立任务</option>
          <option v-for="task in availableTasks" :key="task.id" :value="task.id">{{ task.title }}</option>
        </select>
      </label>
      <label>文件夹（可选，不填按类型放）
        <input v-model="folder" placeholder="项目A/模块B" />
      </label>
      <label>标签（逗号分隔）
        <input v-model="tagsInput" placeholder="工作, 学习" />
      </label>
      <label class="check">
        <input type="checkbox" v-model="useTemplate" /> 使用模板（自动填好结构和示例）
      </label>
      <div class="path-preview">保存为：{{ previewPath }}</div>
      <div v-if="error" class="error">{{ error }}</div>
      <div class="dialog-actions">
        <button class="btn-cancel" @click="$emit('close')">取消</button>
        <button class="btn-create" @click="create" :disabled="!form.title.trim() || busy">创建</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useNotesStore } from '../../stores/notes'
import { TEMPLATES, DEFAULT_FOLDERS, safeName } from '../../composables/templates'
import { notesApi } from '../../composables/useApi'

const props = defineProps({
  presetParentId: { type: String, default: '' },
})
const store = useNotesStore()
const emit = defineEmits(['close', 'created'])
const titleEl = ref(null)
const form = ref({ title: '', note_type: 'note', parent_id: props.presetParentId || '' })
const folder = ref('')
const tagsInput = ref('')
const useTemplate = ref(true)
const busy = ref(false)
const error = ref('')
const availableTasks = ref([])

onMounted(async () => {
  titleEl.value?.focus()
  // 如果有预设父任务，自动选任务类型
  if (props.presetParentId) form.value.note_type = 'task'
  // 加载所有任务，供选择父任务
  try {
    const res = await notesApi.tree('任务')
    availableTasks.value = flattenTasks(res.data)
  } catch {
    availableTasks.value = []
  }
})

function flattenTasks(node) {
  const out = []
  const walk = (n, prefix = '') => {
    if (!n.is_dir && n.name.endsWith('.md')) {
      const title = n.name.replace(/\.md$/, '')
      out.push({ id: n.path, title: prefix + title })
    }
    if (n.children) {
      n.children.forEach(c => walk(c, prefix + (n.name !== 'vault' ? n.name + '/' : '')))
    }
  }
  walk(node)
  return out
}

const targetFolder = computed(() => {
  const f = folder.value.trim().replace(/\\/g, '/').replace(/^\/+|\/+$/g, '')
  return f || DEFAULT_FOLDERS[form.value.note_type]
})

const previewPath = computed(() => {
  const name = safeName(form.value.title) || '标题'
  if (form.value.note_type === 'task' && form.value.parent_id) {
    // 子任务：放在父任务同名文件夹下
    const parentTitle = availableTasks.value.find(t => t.id === form.value.parent_id)?.title || '父任务'
    return `任务/${parentTitle}/${name}.md`
  }
  return `${targetFolder.value}/${name}.md`
})

async function create() {
  if (!form.value.title.trim() || busy.value) return
  busy.value = true
  error.value = ''
  try {
    const tags = tagsInput.value.split(/[,，]/).map(t => t.trim()).filter(Boolean)
    const content = useTemplate.value ? TEMPLATES[form.value.note_type] : ''
    const data = {
      title: form.value.title.trim(),
      note_type: form.value.note_type,
      tags,
      content,
      parent_id: form.value.parent_id || null,
    }
    if (form.value.note_type === 'task') data.status = 'todo'
    // 如果有父任务，不传 id，让后端根据 parent_id 自动建文件夹
    if (!form.value.parent_id) {
      data.id = previewPath.value
    }
    const note = await store.createNote(data)
    emit('created', note.id)
  } catch (err) {
    error.value = '创建失败：' + (err.response?.data?.detail || err.message)
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,.5); z-index: 200;
           display: flex; align-items: center; justify-content: center; }
.dialog { background: var(--color-surface); border-radius: 10px; padding: 24px;
          width: 440px; border: 1px solid var(--color-border); }
h3 { margin-bottom: 16px; color: var(--color-accent); }
label { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px;
        font-size: 12px; color: var(--color-text-dim); }
label.check { flex-direction: row; align-items: center; gap: 6px; font-size: 13px; color: var(--color-text); }
input:not([type=checkbox]), select { background: var(--color-surface2); border: 1px solid var(--color-border);
                border-radius: 6px; padding: 8px 10px; color: var(--color-text); font-size: 14px; outline: none; }
input:focus, select:focus { border-color: var(--color-accent); }
.path-preview { font-size: 12px; color: var(--color-text-dim); margin-bottom: 8px; word-break: break-all; }
.error { color: var(--color-danger); font-size: 13px; margin-bottom: 8px; }
.dialog-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 8px; }
.btn-cancel { background: none; border: 1px solid var(--color-border); color: var(--color-text-dim);
              padding: 7px 16px; border-radius: 6px; }
.btn-create { background: var(--color-accent); border: none; color: var(--color-bg);
              padding: 7px 16px; border-radius: 6px; font-weight: 600; }
.btn-create:disabled { opacity: .4; cursor: not-allowed; }
</style>
