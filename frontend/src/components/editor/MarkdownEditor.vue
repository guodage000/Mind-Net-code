<template>
  <div ref="wrapEl" class="editor-wrap">
    <div class="toolbar">
      <button v-for="btn in toolbarBtns" :key="btn.label" class="tb-btn"
              :title="btn.label" @mousedown.prevent @click="insertFormat(btn)">{{ btn.icon }}</button>
      <span class="tb-sep" />
      <button class="tb-btn" :class="{ active: previewMode }" title="预览" @click="togglePreview">👁</button>
      <span class="tb-spacer" />
      <span class="tb-status" :class="{ error: saveStatus === '保存失败' }">{{ saveStatus }}</span>
    </div>

    <div class="hint-bar">{{ hint }}</div>

    <div class="editor-body">
      <div v-show="!previewMode" ref="editorEl" class="cm-host" />
      <div v-show="previewMode" class="preview" v-html="renderedHtml" />
    </div>

    <div v-if="slashOpen" class="slash-palette" :style="slashPos">
      <div v-if="filteredCmds.length === 0" class="slash-empty">没有匹配的格式，按 Esc 关闭</div>
      <div v-for="(cmd, i) in filteredCmds" :key="cmd.label"
           class="slash-item" :class="{ active: i === slashIdx }"
           @mousedown.prevent @click="applySlash(cmd)" @mouseenter="slashIdx = i">
        <span class="slash-icon">{{ cmd.icon }}</span>
        <span class="slash-label">{{ cmd.label }}</span>
        <span class="slash-desc">{{ cmd.desc }}</span>
      </div>
      <div class="slash-foot">↑↓ 选择 · 回车确认 · Esc 关闭</div>
    </div>

    <!-- 任务属性面板 -->
    <div v-if="propsOpen" class="props-overlay" @click.self="propsOpen = false">
      <div class="props-box">
        <div class="props-title">任务属性</div>
        <div class="props-body-text">{{ propsForm.body }}</div>
        <label>状态
          <div class="status-pills">
            <button v-for="s in STATUS_KEYS" :key="s" class="pill" :class="{ active: propsForm.status === s }"
                    @click="propsForm.status = s">{{ TAG_OF[s] }}</button>
          </div>
        </label>
        <label>优先级
          <div class="status-pills">
            <button v-for="p in ['', 'high', 'medium', 'low']" :key="p || 'none'" class="pill"
                    :class="{ active: propsForm.priority === p }"
                    @click="propsForm.priority = p">{{ p === '' ? '无' : ({high:'高',medium:'中',low:'低'}[p]) }}</button>
          </div>
        </label>
        <div class="props-row">
          <label>截止日期
            <input type="date" v-model="propsForm.date" />
          </label>
          <label>时间（可选）
            <input type="time" v-model="propsForm.time" />
          </label>
        </div>
        <div class="props-actions">
          <button class="btn-cancel" @click="propsOpen = false">取消</button>
          <button class="btn-ok" @click="applyTaskProps">应用</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { parseTaskLine, buildTaskLine, rollupStatus, isOverdue, STATUS_KEYS, TAG_OF } from '../../composables/taskMarkers.js'
import { EditorView, keymap, lineNumbers, Decoration } from '@codemirror/view'
import { EditorState, Prec, EditorSelection, StateField } from '@codemirror/state'
import { markdown } from '@codemirror/lang-markdown'
import { oneDark } from '@codemirror/theme-one-dark'
import { defaultKeymap, historyKeymap, history, indentWithTab } from '@codemirror/commands'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

// 每篇笔记一个编辑器实例（父组件用 :key 绑定笔记 id）。
// 保存通过 saver(text) 完成，并且在切换笔记、编辑器销毁前强制保存，避免内容丢失或串到别的笔记。
const props = defineProps({
  initialContent: { type: String, default: '' },
  saver: { type: Function, required: true },
})

const wrapEl = ref(null)
const editorEl = ref(null)
const previewMode = ref(false)
const previewText = ref('')
const saveStatus = ref('已保存')
const hint = ref('')

let view = null
let saveTimer = null
let dirty = false

const renderedHtml = computed(() =>
  previewMode.value ? DOMPurify.sanitize(marked.parse(previewText.value || '')) : '')

function togglePreview() {
  if (!previewMode.value && view) previewText.value = view.state.doc.toString()
  previewMode.value = !previewMode.value
  if (!previewMode.value) nextTick(() => view?.focus())
}

// ── 保存 ────────────────────────────────────────────────────────────────────
function scheduleSave() {
  dirty = true
  saveStatus.value = '未保存…'
  clearTimeout(saveTimer)
  saveTimer = setTimeout(flush, 800)
}

function flush() {
  clearTimeout(saveTimer)
  saveTimer = null
  if (!dirty || !view) return Promise.resolve()
  dirty = false
  const text = view.state.doc.toString()
  saveStatus.value = '保存中…'
  return Promise.resolve(props.saver(text)).then(
    () => { if (!dirty) saveStatus.value = '已保存' },
    () => { dirty = true; saveStatus.value = '保存失败' },
  )
}

// 删除笔记前调用：丢弃未保存的修改，避免对已删除的笔记再发保存请求
function discard() {
  clearTimeout(saveTimer)
  saveTimer = null
  dirty = false
}

// 打开笔记后，把光标定位到某一行（从左侧子任务列表跳过来时调用）
function gotoLine(line) {
  if (!view) return
  const num = Math.max(1, Math.min(line + 1, view.state.doc.lines))
  const l = view.state.doc.line(num)
  view.dispatch({ selection: { anchor: l.from }, scrollIntoView: true })
  view.focus()
}

defineExpose({ flush, discard, gotoLine })

// ── 工具栏 ──────────────────────────────────────────────────────────────────
const toolbarBtns = [
  { icon: 'B', label: '粗体 (Ctrl+B)', wrap: ['**', '**'] },
  { icon: 'I', label: '斜体 (Ctrl+I)', wrap: ['*', '*'] },
  { icon: '`', label: '行内代码', wrap: ['`', '`'] },
  { icon: 'H', label: '标题', prefix: '## ' },
  { icon: '≡', label: '列表', prefix: '- ' },
  { icon: '✓', label: '任务（Tab 缩进成子任务）', prefix: '- [ ] ' },
  { icon: '"', label: '引用', prefix: '> ' },
]

function wrapSelection(before, after) {
  if (!view) return true
  const tr = view.state.changeByRange(range => {
    const selected = view.state.sliceDoc(range.from, range.to)
    const body = selected || '文字'
    return {
      changes: { from: range.from, to: range.to, insert: before + body + after },
      range: EditorSelection.range(range.from + before.length, range.from + before.length + body.length),
    }
  })
  view.dispatch(tr)
  view.focus()
  return true
}

function prefixLines(prefix) {
  if (!view) return
  const { state } = view
  const changes = []
  const seen = new Set()
  for (const range of state.selection.ranges) {
    for (let pos = range.from; pos <= range.to;) {
      const line = state.doc.lineAt(pos)
      if (!seen.has(line.number)) {
        seen.add(line.number)
        const indent = line.text.match(/^\s*/)[0].length
        changes.push({ from: line.from + indent, insert: prefix })
      }
      pos = line.to + 1
    }
  }
  view.dispatch({ changes })
  view.focus()
}

function insertFormat(btn) {
  if (btn.wrap) wrapSelection(btn.wrap[0], btn.wrap[1])
  else prefixLines(btn.prefix)
}

// ── 斜杠命令 ────────────────────────────────────────────────────────────────
const SLASH_CMDS = [
  { icon: 'H1', label: '标题一', desc: '大标题', keys: 'h1 bt biaoti heading title', insert: '# ' },
  { icon: 'H2', label: '标题二', desc: '章节标题', keys: 'h2 bt biaoti heading', insert: '## ' },
  { icon: 'H3', label: '标题三', desc: '小节标题', keys: 'h3 bt biaoti heading', insert: '### ' },
  { icon: '✓', label: '任务', desc: 'Tab 缩进变子任务', keys: 'rw renwu task todo daiban', insert: '- [ ] ' },
  { icon: '•', label: '无序列表', desc: '要点', keys: 'lb liebiao list ul', insert: '- ' },
  { icon: '1.', label: '有序列表', desc: '步骤', keys: 'lb liebiao list ol', insert: '1. ' },
  { icon: '"', label: '引用', desc: '摘录、备注', keys: 'yy yinyong quote', insert: '> ' },
  { icon: '<>', label: '代码块', desc: '贴代码或日志', keys: 'dm daima code', insert: '```\n', after: '\n```' },
  { icon: '⊞', label: '表格', desc: '两列表格', keys: 'bg biaoge table', insert: '| 列1 | 列2 |\n| --- | --- |\n| ', after: ' |  |' },
  { icon: '—', label: '分隔线', desc: '分隔内容', keys: 'fgx fengexian line hr', insert: '---\n' },
]

const slashOpen = ref(false)
const slashFilter = ref('')
const slashIdx = ref(0)
const slashPos = ref({ top: '0px', left: '0px' })
let slashFrom = 0

const filteredCmds = computed(() => {
  const f = slashFilter.value.trim().toLowerCase()
  if (!f) return SLASH_CMDS
  return SLASH_CMDS.filter(c => c.label.includes(f) || c.keys.includes(f))
})

function closeSlash() {
  slashOpen.value = false
}

function applySlash(cmd) {
  if (!view || !cmd) return
  const head = view.state.selection.main.head
  const after = cmd.after || ''
  view.dispatch({
    changes: { from: slashFrom, to: head, insert: cmd.insert + after },
    selection: { anchor: slashFrom + cmd.insert.length },
  })
  closeSlash()
  view.focus()
}

function updateSlash(state) {
  const sel = state.selection.main
  if (!sel.empty) { closeSlash(); return }
  const line = state.doc.lineAt(sel.head)
  const before = line.text.slice(0, sel.head - line.from)
  // 只在行首（允许缩进）输入 / 时弹出，避免输入网址、路径时误触发
  const m = before.match(/^(\s*)\/(\S*)$/)
  if (!m) { closeSlash(); return }
  slashFrom = line.from + m[1].length
  if (!slashOpen.value || slashFilter.value !== m[2]) slashIdx.value = 0
  slashFilter.value = m[2]
  slashOpen.value = true
  const pos = sel.head
  nextTick(() => {
    if (!view || !wrapEl.value) return
    const coords = view.coordsAtPos(pos)
    if (!coords) return
    const rect = wrapEl.value.getBoundingClientRect()
    slashPos.value = { top: (coords.bottom - rect.top + 4) + 'px', left: (coords.left - rect.left) + 'px' }
  })
}

// 斜杠菜单打开时，方向键、回车、Tab、Esc 都由菜单处理，优先级必须最高
const slashKeymap = Prec.highest(keymap.of([
  { key: 'ArrowDown', run: () => {
    if (!slashOpen.value) return false
    if (filteredCmds.value.length) slashIdx.value = (slashIdx.value + 1) % filteredCmds.value.length
    return true
  } },
  { key: 'ArrowUp', run: () => {
    if (!slashOpen.value) return false
    const n = filteredCmds.value.length
    if (n) slashIdx.value = (slashIdx.value - 1 + n) % n
    return true
  } },
  { key: 'Enter', run: () => {
    if (!slashOpen.value) return false
    const cmd = filteredCmds.value[slashIdx.value]
    if (!cmd) { closeSlash(); return false }
    applySlash(cmd)
    return true
  } },
  { key: 'Tab', run: () => {
    if (!slashOpen.value) return false
    applySlash(filteredCmds.value[slashIdx.value])
    return true
  } },
  { key: 'Escape', run: () => {
    if (!slashOpen.value) return false
    closeSlash()
    return true
  } },
]))

// ── 任务勾选、状态/优先级/日期切换、父任务汇总 ─────────────────────────────

// 收集光标（或选区）覆盖到的任务行号
function targetTaskLines(state) {
  const nums = new Set()
  for (const range of state.selection.ranges) {
    for (let pos = range.from; pos <= range.to;) {
      const line = state.doc.lineAt(pos)
      if (parseTaskLine(line.text)) nums.add(line.number)
      pos = line.to + 1
    }
  }
  return [...nums]
}

// ── 父任务状态自动汇总 ──────────────────────────────────────────────────────
// 某条任务状态变了之后，沿缩进向上找父任务，用子任务的状态重算父任务。
// 只改动"有子任务"的那些行；没有任何子任务的行保持原样。
function rollupAncestors(state) {
  const rows = []
  for (let n = 1; n <= state.doc.lines; n++) {
    const t = parseTaskLine(state.doc.line(n).text)
    if (t) rows.push({ num: n, indent: t.indent.replace(/\t/g, '  ').length, t })
  }
  if (!rows.length) return []

  // 建立父子关系：下一个缩进更深的连续行是子任务
  const children = new Map()   // 行号 -> 子任务行号数组
  const parents = new Map()    // 行号 -> 父任务行号
  const stack = []
  for (const r of rows) {
    while (stack.length && stack[stack.length - 1].indent >= r.indent) stack.pop()
    if (stack.length) {
      const p = stack[stack.length - 1]
      if (!children.has(p.num)) children.set(p.num, [])
      children.get(p.num).push(r.num)
      parents.set(r.num, p.num)
    }
    stack.push(r)
  }
  if (!children.size) return []

  const byNum = new Map(rows.map(r => [r.num, r]))
  const latestStatus = new Map(rows.map(r => [r.num, r.t.status]))
  const changes = []

  // 从最深的父任务往上处理
  const depthOf = (num) => {
    let d = 0, cur = num
    while (parents.has(cur)) { cur = parents.get(cur); d++ }
    return d
  }
  const parentNums = [...children.keys()].sort((a, b) => depthOf(b) - depthOf(a))

  for (const num of parentNums) {
    const kids = children.get(num).map(k => latestStatus.get(k))
    const r = byNum.get(num)
    const rolled = rollupStatus(kids.map(s => ({ status: s })))
    if (!rolled || rolled.status === r.t.status) continue
    latestStatus.set(num, rolled.status)
    const line = state.doc.line(num)
    changes.push({
      from: line.from, to: line.to,
      insert: buildTaskLine({ ...r.t, status: rolled.status }),
    })
  }
  return changes
}

// 先改目标行，再在同一事务里汇总父任务，编辑器只记一次撤销
function dispatchWithRollup(changes) {
  if (!view || !changes.length) return
  const tr = view.state.update({ changes })
  const after = tr.state
  const extra = rollupAncestors(after)
  if (extra.length) {
    view.dispatch({ changes: [...changes, ...extra] })
  } else {
    view.dispatch(tr)
  }
}

function toggleTask() {
  if (!view) return true
  const { state } = view
  const changes = []
  for (const num of targetTaskLines(state)) {
    const line = state.doc.line(num)
    const t = parseTaskLine(line.text)
    const next = t.status === 'done' ? 'todo' : 'done'
    changes.push({ from: line.from, to: line.to, insert: buildTaskLine({ ...t, status: next }) })
  }
  dispatchWithRollup(changes)
  return true
}

// Ctrl+J：待做 → 进行中 → 已完成 → 搁置 循环
function cycleTaskStatus() {
  if (!view) return true
  const { state } = view
  const changes = []
  for (const num of targetTaskLines(state)) {
    const line = state.doc.line(num)
    const t = parseTaskLine(line.text)
    const next = STATUS_KEYS[(STATUS_KEYS.indexOf(t.status) + 1) % STATUS_KEYS.length]
    changes.push({ from: line.from, to: line.to, insert: buildTaskLine({ ...t, status: next }) })
  }
  dispatchWithRollup(changes)
  return true
}

// 优先级循环：无 → 高 → 中 → 低 → 无（Ctrl+Shift+J）
const PRIORITY_CYCLE = [null, 'high', 'medium', 'low']
function cyclePriority() {
  if (!view) return true
  const { state } = view
  const changes = []
  for (const num of targetTaskLines(state)) {
    const line = state.doc.line(num)
    const t = parseTaskLine(line.text)
    const next = PRIORITY_CYCLE[(PRIORITY_CYCLE.indexOf(t.priority) + 1) % PRIORITY_CYCLE.length]
    changes.push({ from: line.from, to: line.to, insert: buildTaskLine({ ...t, priority: next }) })
  }
  dispatchWithRollup(changes)
  return true
}

// 打开任务属性面板（Ctrl+Alt+J，或右键任务行）
const propsOpen = ref(false)
const propsLine = ref(0)
const propsForm = ref({ status: 'todo', priority: '', date: '', time: '', body: '' })

function openTaskProps() {
  const v = view
  if (!v || !v.state.selection.main.empty) return false
  const line = v.state.doc.lineAt(v.state.selection.main.head)
  const t = parseTaskLine(line.text)
  if (!t) {
    hint.value = '把光标放到任务行（以 - [ ] 开头的那行）再打开属性'
    return false
  }
  propsLine.value = line.number
  propsForm.value = {
    status: t.status, priority: t.priority || '', date: t.date || '',
    time: t.time || '', body: t.body,
  }
  propsOpen.value = true
  return true
}

function applyTaskProps() {
  const v = view
  if (!v || !propsLine.value) { propsOpen.value = false; return }
  const form = propsForm.value
  const line = v.state.doc.line(Math.min(propsLine.value, v.state.doc.lines))
  const t = parseTaskLine(line.text)
  if (!t) { propsOpen.value = false; return }
  const insert = buildTaskLine({
    ...t, status: form.status, priority: form.priority || null,
    date: form.date || null, time: form.time || null,
  })
  dispatchWithRollup([{ from: line.from, to: line.to, insert }])
  propsOpen.value = false
  v.focus()
}

// ── 任务状态着色 + 到期提醒 ────────────────────────────────────────────────
function taskDecorations(state) {
  const marks = []
  if (state.doc.lines <= 800) {
    for (let n = 1; n <= state.doc.lines; n++) {
      const line = state.doc.line(n)
      const t = parseTaskLine(line.text)
      if (!t) continue
      const cls = ['task-line', 'task-' + t.status]
      if (t.status !== 'done' && isOverdue(t.date, t.time)) cls.push('task-overdue')
      if (t.priority === 'high') cls.push('task-prio-high')
      marks.push(Decoration.line({ class: cls.join(' ') }).range(line.from))
    }
  }
  return Decoration.set(marks, true)
}

const taskStatusField = StateField.define({
  create: state => taskDecorations(state),
  update: (value, tr) => (tr.docChanged ? taskDecorations(tr.state) : value),
  provide: field => EditorView.decorations.from(field),
})

const editKeymap = Prec.high(keymap.of([
  { key: 'Mod-Enter', run: toggleTask },
  { key: 'Mod-j', run: cycleTaskStatus },
  { key: 'Mod-Shift-j', run: cyclePriority },
  { key: 'Mod-Alt-j', run: openTaskProps },
  { key: 'Mod-b', run: () => wrapSelection('**', '**') },
  { key: 'Mod-i', run: () => wrapSelection('*', '*') },
  { key: 'Mod-s', run: () => { flush(); return true } },
]))


// ── 光标所在行的操作提示 ───────────────────────────────────────────────────
function updateHint(state) {
  const line = state.doc.lineAt(state.selection.main.head)
  const text = line.text
  if (/^\s*[-*+]\s+\[[ xX/]\]/.test(text)) {
    hint.value = '任务：Ctrl+J 换状态 · Ctrl+Shift+J 换优先级 · Ctrl+Alt+J 打开属性（改日期/时间）· Tab 缩进成子任务'
  } else if (/^\s*([-*+]|\d+\.)\s/.test(text)) {
    hint.value = '列表：回车继续下一项 · Tab 缩进成子项 · Shift+Tab 退回上一级 · 空项连按两次回车结束'
  } else if (/^#{1,6}\s/.test(text)) {
    hint.value = '标题：# 越多级别越低，# 后面要有空格'
  } else if (/^\s*>/.test(text)) {
    hint.value = '引用：回车继续引用 · 空行再按回车结束'
  } else if (text.trim() === '') {
    hint.value = '在空行输入 / 选择要插入的格式，例如任务、标题、代码块'
  } else {
    hint.value = '选中文字后点工具栏加粗、斜体 · 在行首输入 / 插入格式 · Ctrl+S 立即保存'
  }
}

// ── CodeMirror ──────────────────────────────────────────────────────────────
onMounted(() => {
  const listener = EditorView.updateListener.of(update => {
    if (update.docChanged) scheduleSave()
    if (update.docChanged || update.selectionSet) {
      updateSlash(update.state)
      updateHint(update.state)
    }
  })

  view = new EditorView({
    state: EditorState.create({
      doc: props.initialContent || '',
      extensions: [
        slashKeymap,
        editKeymap,
        taskStatusField,
        history(),
        markdown(),
        keymap.of([indentWithTab, ...defaultKeymap, ...historyKeymap]),
        oneDark,
        lineNumbers(),
        EditorView.lineWrapping,
        listener,
        EditorView.domEventHandlers({ blur: () => { flush() } }),
      ],
    }),
    parent: editorEl.value,
  })
  updateHint(view.state)
})

onBeforeUnmount(() => {
  flush()
  view?.destroy()
  view = null
})
</script>

<style scoped>
.editor-wrap { display: flex; flex-direction: column; height: 100%; position: relative; min-height: 0; }
.toolbar { display: flex; align-items: center; gap: 2px; padding: 4px 8px;
           border-bottom: 1px solid var(--color-border); flex-shrink: 0; }
.tb-btn { background: none; border: none; color: var(--color-text-dim); font-size: 13px;
          padding: 4px 7px; border-radius: 4px; font-weight: 600; }
.tb-btn:hover, .tb-btn.active { background: var(--color-border); color: var(--color-text); }
.tb-sep { width: 1px; height: 16px; background: var(--color-border); margin: 0 4px; }
.tb-spacer { flex: 1; }
.tb-status { font-size: 11px; color: var(--color-text-dim); }
.tb-status.error { color: var(--color-danger); }
.hint-bar { font-size: 12px; color: var(--color-text-dim); padding: 4px 12px;
            background: var(--color-surface); border-bottom: 1px solid var(--color-border);
            flex-shrink: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.editor-body { flex: 1; overflow: hidden; min-height: 0; }
.cm-host { height: 100%; overflow-y: auto; }
.cm-host :deep(.cm-editor) { height: 100%; }
/* 任务行按状态着色，左侧一条色条 */
.cm-host :deep(.task-line) { border-left: 3px solid transparent; padding-left: 6px; margin-left: -9px; }
.cm-host :deep(.task-todo) { border-left-color: #7f849c; }
.cm-host :deep(.task-in_progress) { border-left-color: var(--color-warn); background: rgba(250,179,135,.06); }
.cm-host :deep(.task-done) { border-left-color: var(--color-success); opacity: .6; }
.cm-host :deep(.task-blocked) { border-left-color: var(--color-danger); background: rgba(243,139,168,.06); }
.preview { height: 100%; overflow-y: auto; padding: 24px 32px; line-height: 1.7; font-size: 15px; }
.preview :deep(h1), .preview :deep(h2), .preview :deep(h3) { margin: 1.2em 0 .4em; color: var(--color-accent); }
.preview :deep(ul), .preview :deep(ol) { padding-left: 1.6em; }
.preview :deep(code) { background: var(--color-surface2); padding: 2px 5px; border-radius: 3px; }
.preview :deep(pre) { background: var(--color-surface2); padding: 12px; border-radius: 6px; overflow-x: auto; }
.preview :deep(blockquote) { border-left: 3px solid var(--color-accent2); padding-left: 12px;
                             color: var(--color-text-dim); margin: 8px 0; }
.preview :deep(table) { border-collapse: collapse; margin: 8px 0; }
.preview :deep(th), .preview :deep(td) { border: 1px solid var(--color-border); padding: 4px 10px; }
.slash-palette { position: absolute; z-index: 100; background: var(--color-surface2);
                 border: 1px solid var(--color-border); border-radius: 8px; padding: 4px;
                 min-width: 260px; box-shadow: 0 8px 24px rgba(0,0,0,.4); }
.slash-item { display: flex; align-items: center; gap: 8px; padding: 6px 10px;
              border-radius: 5px; cursor: pointer; font-size: 13px; }
.slash-item.active { background: var(--color-border); }
.slash-icon { width: 24px; text-align: center; color: var(--color-accent); font-size: 11px; font-weight: 700; }
.slash-label { min-width: 64px; }
.slash-desc { color: var(--color-text-dim); font-size: 12px; }
.slash-empty { padding: 8px 10px; color: var(--color-text-dim); font-size: 12px; }
.slash-foot { padding: 4px 10px 2px; color: var(--color-text-dim); font-size: 11px;
              border-top: 1px solid var(--color-border); margin-top: 4px; }
/* 任务属性面板 */
.props-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.5); z-index: 300;
                 display: flex; align-items: center; justify-content: center; }
.props-box { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 10px;
             padding: 18px; width: 380px; }
.props-title { font-size: 14px; font-weight: 600; color: var(--color-accent); margin-bottom: 8px; }
.props-body-text { font-size: 13px; color: var(--color-text); background: var(--color-surface2);
                   padding: 6px 10px; border-radius: 5px; margin-bottom: 12px; }
.props-box label { display: flex; flex-direction: column; gap: 4px; font-size: 12px;
                   color: var(--color-text-dim); margin-bottom: 10px; }
.status-pills { display: flex; flex-wrap: wrap; gap: 4px; }
.pill { background: var(--color-surface2); border: 1px solid var(--color-border); color: var(--color-text-dim);
        font-size: 12px; padding: 4px 10px; border-radius: 12px; }
.pill.active { border-color: var(--color-accent); color: var(--color-accent); }
.props-row { display: flex; gap: 10px; }
.props-row label { flex: 1; }
.props-row input { background: var(--color-surface2); border: 1px solid var(--color-border);
                   color: var(--color-text); border-radius: 6px; padding: 6px 8px; font-size: 13px; }
.props-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 10px; }
.btn-cancel { background: none; border: 1px solid var(--color-border); color: var(--color-text-dim);
              padding: 6px 14px; border-radius: 6px; }
.btn-ok { background: var(--color-accent); border: none; color: var(--color-bg);
          padding: 6px 14px; border-radius: 6px; font-weight: 600; }
</style>
