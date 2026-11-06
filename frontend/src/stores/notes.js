import { defineStore } from 'pinia'
import { ref } from 'vue'
import { notesApi, searchApi, taskApi } from '../composables/useApi'

export const useNotesStore = defineStore('notes', () => {
  const tree = ref(null)
  const currentNote = ref(null)
  const searchResults = ref([])
  const allTags = ref([])
  const loading = ref(false)
  const pendingSaves = new Map()

  async function fetchTree() {
    const res = await notesApi.tree()
    tree.value = res.data
  }

  async function openNote(id) {
    // 等这篇笔记未完成的保存结束，再从服务器读取，保证读到的是最新内容
    if (pendingSaves.has(id)) await pendingSaves.get(id).catch(() => {})
    loading.value = true
    try {
      const res = await notesApi.get(id)
      currentNote.value = res.data
    } finally {
      loading.value = false
    }
  }

  // patch 只包含要改的字段，例如 { content } 或 { title } 或 { status }。
  // 改标题、改状态时不带 content，后端会保留磁盘上最新的正文，不会用旧内容覆盖。
  async function saveNote(id, patch) {
    // 链式保存：等上一次保存完再开始新的
    const prev = (pendingSaves.get(id) || Promise.resolve()).catch(() => {})
    const promise = prev.then(async () => {
      const res = await notesApi.update(id, patch)
      // 只有还在看同一篇笔记时才更新 currentNote，避免覆盖已经切换到的新笔记
      if (currentNote.value?.id === id) {
        currentNote.value = res.data
      }
      return res.data
    }).finally(() => {
      if (pendingSaves.get(id) === promise) pendingSaves.delete(id)
    })
    pendingSaves.set(id, promise)
    return promise
  }

  async function fetchNote(id) {
    if (pendingSaves.has(id)) await pendingSaves.get(id).catch(() => {})
    const res = await notesApi.get(id)
    return res.data
  }

  async function createNote(data) {
    const res = await notesApi.create(data)
    await fetchTree()
    return res.data
  }

  async function deleteNote(id) {
    // 删除前先等待保存完成
    if (pendingSaves.has(id)) await pendingSaves.get(id).catch(() => {})
    await notesApi.delete(id)
    if (currentNote.value?.id === id) currentNote.value = null
    await fetchTree()
  }

  async function search(q, tags = []) {
    if (!q.trim()) { searchResults.value = []; return }
    const res = await searchApi.search(q, tags)
    searchResults.value = res.data
  }

  async function fetchTags() {
    const res = await searchApi.tags()
    allTags.value = res.data
  }

  // 任务列表：所有带状态的任务，按状态分组
  const tasks = ref([])
  const taskCounts = ref({})
  async function fetchTasks() {
    const res = await taskApi.list()
    tasks.value = res.data.tasks
    taskCounts.value = res.data.counts
  }

  return { tree, currentNote, searchResults, allTags, loading, tasks, taskCounts,
           fetchTree, openNote, saveNote, fetchNote, createNote, deleteNote,
           search, fetchTags, fetchTasks }
})
