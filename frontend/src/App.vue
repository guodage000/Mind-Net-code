<template>
  <div class="app-layout">
    <aside class="sidebar">
      <div class="sidebar-header">
        <span class="logo">🧠 MindNet</span>
        <button class="icon-btn" title="搜索 (Ctrl+K)" @click="showSearch = true">🔍</button>
        <button class="icon-btn" title="导入 Markdown" @click="showImport = true">⬇</button>
        <button class="icon-btn" title="帮助" @click="showHelp = true">?</button>
      </div>

      <div class="side-tabs">
        <button class="side-tab" :class="{ active: sidebarTab === 'files' }" @click="sidebarTab = 'files'">文件</button>
        <button class="side-tab" :class="{ active: sidebarTab === 'tasks' }" @click="switchToTasks">
          任务<span v-if="openTaskCount" class="tab-count">{{ openTaskCount }}</span>
        </button>
      </div>

      <FileTree v-if="sidebarTab === 'files'" :tree="store.tree" :active-id="store.currentNote?.id"
                @open="openNote" @new-note="showNewNote = true" @delete="confirmDelete" />
      <TaskPanel v-else-if="sidebarTab === 'tasks'" ref="taskPanelRef" @open="openNote" />
    </aside>

    <main class="main-area">
      <template v-if="store.currentNote">
        <div class="note-header">
          <div class="note-title-row">
            <input v-model="titleDraft" class="note-title" @blur="renameTitle" @keydown.enter.prevent="$event.target.blur()" />
            <button v-if="store.currentNote.note_type === 'task'" class="icon-btn" title="新建子任务" @click="createSubtask">＋</button>
            <span v-if="store.currentNote.status" class="header-status">{{ statusMeta(store.currentNote.status).label }}</span>
            <button class="icon-btn" title="删除笔记" @click="confirmDelete(store.currentNote.id)">🗑</button>
          </div>
          <div class="note-meta">
            <span v-for="tag in store.currentNote.tags" :key="tag" class="tag">{{ tag }}</span>
          </div>
        </div>
        <MarkdownEditor
          ref="editorRef"
          :key="store.currentNote.id"
          :initial-content="store.currentNote.content"
          :saver="saverFor(store.currentNote.id)"
        />
      </template>
      <div v-else class="empty-state">
        <div class="empty-content">
          <p class="empty-title">👈 从左侧打开笔记，或点击 ＋ 新建</p>
          <div class="empty-actions">
            <button class="btn-help" @click="showNewNote = true">新建笔记</button>
            <button class="btn-help ghost" @click="showImport = true">导入 Markdown</button>
            <button class="btn-help ghost" @click="showHelp = true">快速上手</button>
          </div>
        </div>
      </div>
    </main>

    <aside class="info-panel" v-if="store.currentNote">
      <InfoPanel :key="store.currentNote.id" :note="store.currentNote" />
    </aside>

    <SearchPanel v-if="showSearch" @close="showSearch = false" @open="openNote" />
    <NewNoteDialog v-if="showNewNote" @close="showNewNote = false" @created="handleCreated" :preset-parent-id="presetParentId" />
    <ImportDialog v-if="showImport" @close="showImport = false" @imported="handleImported" />
    <HelpPanel v-if="showHelp" @close="showHelp = false" />
    <GitBadge />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useNotesStore } from './stores/notes'
import { statusMeta } from './composables/tasks'
import FileTree from './components/sidebar/FileTree.vue'
import TaskPanel from './components/sidebar/TaskPanel.vue'
import MarkdownEditor from './components/editor/MarkdownEditor.vue'
import InfoPanel from './components/sidebar/InfoPanel.vue'
import SearchPanel from './components/layout/SearchPanel.vue'
import NewNoteDialog from './components/layout/NewNoteDialog.vue'
import ImportDialog from './components/layout/ImportDialog.vue'
import HelpPanel from './components/layout/HelpPanel.vue'
import GitBadge from './components/layout/GitBadge.vue'

const store = useNotesStore()
const showSearch = ref(false)
const showNewNote = ref(false)
const showImport = ref(false)
const showHelp = ref(false)
const sidebarTab = ref('files')
const editorRef = ref(null)
const taskPanelRef = ref(null)
const titleDraft = ref('')
const presetParentId = ref('')

const openTaskCount = computed(() =>
  (store.taskCounts.todo || 0) + (store.taskCounts.in_progress || 0))

onMounted(async () => {
  await store.fetchTree()
  await store.fetchTags()
  await store.fetchTasks()
  if (!localStorage.getItem('mindnet-help-seen')) showHelp.value = true
})

watch(() => store.currentNote?.id, (newId) => {
  if (newId) titleDraft.value = store.currentNote?.title || ''
})

function switchToTasks() {
  sidebarTab.value = 'tasks'
  nextTick(() => taskPanelRef.value?.refresh())
}

function createSubtask() {
  presetParentId.value = store.currentNote?.id || ''
  showNewNote.value = true
}

async function openNote(id) {
  // 切换前强制保存当前笔记
  if (editorRef.value) await editorRef.value.flush()
  await store.openNote(id)
  showSearch.value = false
  // 打开任务卡片后，任务面板的状态也跟着刷新
  if (sidebarTab.value === 'tasks') store.fetchTasks()
}

// 保存函数在渲染时就绑定笔记 id。切换笔记时，旧编辑器销毁前的最后一次保存
// 仍然写回它自己的笔记，不会写到刚打开的新笔记里。
function saverFor(id) {
  return text => store.saveNote(id, { content: text })
}

async function renameTitle() {
  const newTitle = titleDraft.value.trim()
  if (!newTitle || !store.currentNote || newTitle === store.currentNote.title) return
  try {
    await store.saveNote(store.currentNote.id, { title: newTitle })
  } catch (err) {
    alert('改标题失败：' + err.message)
  }
}

async function confirmDelete(id) {
  const note = store.currentNote?.id === id ? store.currentNote : { id }
  if (!confirm(`确认删除笔记？\n\n${note.title || id}\n\n已同步到 Git 的版本可以通过历史恢复，30 秒内新建的笔记没有历史。`)) return
  // 删除前先丢弃编辑器的未保存内容，避免对已删除的笔记再发保存请求
  if (store.currentNote?.id === id && editorRef.value) editorRef.value.discard()
  try {
    await store.deleteNote(id)
    await store.fetchTasks()
  } catch (err) {
    alert('删除失败：' + err.message)
  }
}

async function handleCreated(id) {
  showNewNote.value = false
  await store.fetchTasks()
  await openNote(id)
}

async function handleImported(result) {
  await store.fetchTree()
  if (result?.imported?.length) {
    await openNote(result.imported[0])
  }
}

function onKeydown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault()
    showSearch.value = !showSearch.value
  }
}
document.addEventListener('keydown', onKeydown)
</script>

<style scoped>
.app-layout { display: grid; grid-template-columns: var(--sidebar-width) 1fr var(--info-width);
              height: 100vh; overflow: hidden; }
.sidebar { background: var(--color-surface); border-right: 1px solid var(--color-border);
           display: flex; flex-direction: column; overflow: hidden; }
.sidebar-header { display: flex; align-items: center; gap: 4px;
                  padding: 10px 12px; border-bottom: 1px solid var(--color-border); flex-shrink: 0; }
.logo { font-weight: 700; font-size: 15px; color: var(--color-accent); flex: 1; }
.icon-btn { background: none; border: none; color: var(--color-text-dim);
            font-size: 16px; padding: 4px 6px; border-radius: 4px; }
.icon-btn:hover { background: var(--color-border); color: var(--color-text); }
.side-tabs { display: flex; gap: 4px; padding: 6px 10px; border-bottom: 1px solid var(--color-border); }
.side-tab { flex: 1; background: none; border: 1px solid transparent; color: var(--color-text-dim);
            font-size: 13px; padding: 4px 0; border-radius: 5px; }
.side-tab.active { background: var(--color-surface2); color: var(--color-text); border-color: var(--color-border); }
.tab-count { font-size: 10px; background: var(--color-warn); color: var(--color-bg);
             border-radius: 8px; padding: 0 5px; margin-left: 4px; }
.main-area { display: flex; flex-direction: column; overflow: hidden; background: var(--color-bg); }
.note-header { padding: 16px 32px 8px; border-bottom: 1px solid var(--color-border); flex-shrink: 0; }
.note-title-row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.note-title { font-size: 22px; font-weight: 700; color: var(--color-text); background: none;
              border: none; outline: none; flex: 1; padding: 2px 4px; border-radius: 4px; min-width: 0; }
.note-title:focus { background: var(--color-surface2); }
.header-status { font-size: 12px; padding: 2px 10px; border-radius: 12px;
                 background: var(--color-surface2); color: var(--color-accent); flex-shrink: 0; }
.note-meta { display: flex; gap: 6px; flex-wrap: wrap; }
.tag { background: var(--color-surface2); color: var(--color-accent2); font-size: 11px;
       padding: 2px 8px; border-radius: 12px; }
.info-panel { background: var(--color-surface); border-left: 1px solid var(--color-border); overflow-y: auto; }
.empty-state { flex: 1; display: flex; align-items: center; justify-content: center; }
.empty-content { text-align: center; }
.empty-title { color: var(--color-text-dim); font-size: 15px; margin-bottom: 16px; }
.empty-actions { display: flex; gap: 8px; justify-content: center; }
.btn-help { background: var(--color-accent); color: var(--color-bg); border: none;
            padding: 8px 18px; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-help.ghost { background: none; border: 1px solid var(--color-border); color: var(--color-text-dim); }
.btn-help:hover { opacity: .9; }
</style>
