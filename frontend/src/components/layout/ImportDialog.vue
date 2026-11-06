<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="dialog">
      <h3>导入 Markdown 文档</h3>
      <p class="tip">可以选单个 .md 文件，也可以选整个文件夹（按子文件夹保留层级）。原文件不会被修改。</p>

      <label>文件或文件夹路径
        <div class="path-row">
          <input v-model="pathInput" placeholder="例如 D:\我的笔记 或 D:\笔记\文档.md" @keydown.enter="addPaths" />
          <button class="mini" @click="pick" title="选择文件或文件夹">选择…</button>
        </div>
      </label>
      <button class="mini add" @click="addPaths">＋ 加入列表</button>

      <div v-if="paths.length" class="path-list">
        <div v-for="(p, i) in paths" :key="p" class="path-item">
          <span class="path-text">{{ p }}</span>
          <button class="mini" @click="paths.splice(i, 1)">移除</button>
        </div>
      </div>
      <p v-else class="tip dim">还没有选择任何文件或文件夹</p>

      <label>导入到
        <input v-model="folder" placeholder="导入" />
      </label>
      <label class="check"><input type="checkbox" v-model="keepFolders" /> 保留子文件夹层级</label>
      <label class="check"><input type="checkbox" v-model="convert" /> 统一任务复选框写法（各种 ✓ 变成 - [ ]）</label>
      <label>重名时
        <select v-model="onExisting">
          <option value="rename">自动加序号，保留两份</option>
          <option value="skip">跳过已存在的文件</option>
        </select>
      </label>

      <div v-if="result" class="result">
        <div>导入成功 {{ result.imported.length }} 篇</div>
        <div v-if="result.skipped.length" class="warn">跳过 {{ result.skipped.length }} 篇（已存在）</div>
        <div v-if="result.failed.length" class="err">失败 {{ result.failed.length }} 篇：
          <div v-for="f in result.failed" :key="f">{{ f }}</div>
        </div>
      </div>
      <div v-if="error" class="err">{{ error }}</div>

      <div class="dialog-actions">
        <button class="btn-cancel" @click="$emit('close')">关闭</button>
        <button class="btn-create" @click="run" :disabled="!paths.length || busy">
          {{ busy ? '导入中…' : '开始导入' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { importApi } from '../../composables/useApi'

const emit = defineEmits(['close', 'imported'])
const pathInput = ref('')
const paths = ref([])
const folder = ref('导入')
const keepFolders = ref(true)
const convert = ref(true)
const onExisting = ref('rename')
const busy = ref(false)
const error = ref('')
const result = ref(null)

function addPaths() {
  const v = pathInput.value.trim().replace(/^"|"$/g, '')
  if (v && !paths.value.includes(v)) paths.value.push(v)
  pathInput.value = ''
}

async function pick() {
  error.value = ''
  try {
    const res = await importApi.pick()
    if (res.data.path && !paths.value.includes(res.data.path)) paths.value.push(res.data.path)
  } catch (err) {
    error.value = '选择框没有打开：' + (err.response?.data?.detail || err.message)
  }
}

async function run() {
  if (!paths.value.length) return
  busy.value = true
  error.value = ''
  result.value = null
  try {
    const res = await importApi.run({
      folder: folder.value.trim() || '导入',
      files: paths.value,
      organize_subfolders: keepFolders.value,
      convert_checklists: convert.value,
      existing: onExisting.value,
    })
    result.value = res.data
    emit('imported', res.data)
  } catch (err) {
    error.value = '导入失败：' + (err.response?.data?.detail || err.message)
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,.5); z-index: 200;
           display: flex; align-items: center; justify-content: center; }
.dialog { background: var(--color-surface); border-radius: 10px; padding: 22px;
          width: 500px; max-height: 86vh; overflow-y: auto; border: 1px solid var(--color-border); }
h3 { margin-bottom: 8px; color: var(--color-accent); }
.tip { font-size: 12px; color: var(--color-text-dim); line-height: 1.6; margin-bottom: 12px; }
.tip.dim { opacity: .7; }
label { display: flex; flex-direction: column; gap: 4px; margin-bottom: 10px;
        font-size: 12px; color: var(--color-text-dim); }
label.check { flex-direction: row; align-items: center; gap: 6px; font-size: 13px; color: var(--color-text); }
input:not([type=checkbox]), select { background: var(--color-surface2); border: 1px solid var(--color-border);
                border-radius: 6px; padding: 7px 9px; color: var(--color-text); font-size: 13px; outline: none; }
input:focus, select:focus { border-color: var(--color-accent); }
.path-row { display: flex; gap: 6px; }
.path-row input { flex: 1; }
.mini { background: var(--color-surface2); border: 1px solid var(--color-border); color: var(--color-text);
        border-radius: 6px; padding: 6px 10px; font-size: 12px; }
.mini:hover { border-color: var(--color-accent); }
.mini.add { margin-bottom: 10px; }
.path-list { margin-bottom: 12px; }
.path-item { display: flex; align-items: center; gap: 8px; padding: 4px 6px;
             background: var(--color-surface2); border-radius: 5px; margin-bottom: 4px; }
.path-text { flex: 1; font-size: 12px; word-break: break-all; }
.result { font-size: 13px; background: var(--color-surface2); border-radius: 6px;
          padding: 8px 10px; margin: 8px 0; }
.warn { color: var(--color-warn); }
.err { color: var(--color-danger); font-size: 12px; margin: 6px 0; }
.dialog-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 10px; }
.btn-cancel { background: none; border: 1px solid var(--color-border); color: var(--color-text-dim);
              padding: 7px 16px; border-radius: 6px; }
.btn-create { background: var(--color-accent); border: none; color: var(--color-bg);
              padding: 7px 16px; border-radius: 6px; font-weight: 600; }
.btn-create:disabled { opacity: .4; cursor: not-allowed; }
</style>
