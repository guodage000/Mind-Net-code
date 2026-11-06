// 任务行的标记解析与回写。格式：
//   缩进 + "- [ ]" 或 "- [x]" 或 "- [/]" + 正文 + 可选的 [状态] [优先级] [日期] [时间]
// 例如：  - [ ] 画原理图 [进行中] [高] [2026-11-10] [18:00]
// 标记顺序不限，写在行尾；正文里出现的同名方括号不会被误认为标记。

export const STATUS_KEYS = ['todo', 'in_progress', 'done', 'blocked']
export const TAG_OF = { todo: '待做', in_progress: '进行中', done: '已完成', blocked: '搁置' }
export const STATUS_TAGS = { '待做': 'todo', '进行中': 'in_progress', '已完成': 'done', '搁置': 'blocked' }
export const PRIORITY_OF = { '高': 'high', '中': 'medium', '低': 'low' }
export const PRIORITY_TAG = { high: '高', medium: '中', low: '低' }

const TAG_RE = /\[(待做|进行中|已完成|搁置)\]\s*$/
const PRIO_RE = /\[(高|中|低)\]\s*$/
const DATE_RE = /\[(\d{4}-\d{2}-\d{2})\]\s*$/
const TIME_RE = /\[(\d{1,2}:\d{2})\]\s*$/

// 方框字符 → 状态。"/" 表示进行中（手工约定，Markdown 里不算勾选）
export function statusFromBox(box) {
  if (box === 'x' || box === 'X') return 'done'
  if (box === '/') return 'in_progress'
  return 'todo'
}

export function boxFromStatus(status) {
  if (status === 'done') return 'x'
  if (status === 'in_progress') return '/'
  return ' '
}

const LINE_RE = /^(\s*)([-*+])(\s+)\[([ xX/])\](\s*)(.*)$/

/**
 * 解析一行，不是任务行返回 null。
 * 返回 { indent, bullet, box, status, priority, date, time, body, hasMarkers }
 */
export function parseTaskLine(text) {
  const m = text.match(LINE_RE)
  if (!m) return null
  let rest = m[6] || ''
  let status = null
  let priority = null
  let date = null
  let time = null
  let hasMarkers = false
  // 从行尾往前剥标记，顺序不限
  for (let i = 0; i < 4; i++) {
    let mm
    if ((mm = rest.match(TIME_RE)) && !time) { time = mm[1]; rest = rest.slice(0, mm.index); hasMarkers = true; continue }
    if ((mm = rest.match(DATE_RE)) && !date) { date = mm[1]; rest = rest.slice(0, mm.index); hasMarkers = true; continue }
    if ((mm = rest.match(PRIO_RE)) && !priority) { priority = PRIORITY_OF[mm[1]]; rest = rest.slice(0, mm.index); hasMarkers = true; continue }
    if ((mm = rest.match(TAG_RE)) && !status) { status = STATUS_TAGS[mm[1]]; rest = rest.slice(0, mm.index); hasMarkers = true; continue }
    break
  }
  return {
    indent: m[1],
    bullet: m[2],
    box: m[4],
    status: status || statusFromBox(m[4]),
    explicitStatus: status,
    priority,
    date,
    time,
    body: rest.trim(),
    hasMarkers,
  }
}

/**
 * 按给定状态、优先级、日期时间重新拼出一行。null / '' 表示去掉该标记。
 * 状态标记只在状态和方框不一致时才写（进行中、搁置、以及显式"待做"需要写）。
 */
export function buildTaskLine({ indent = '', bullet = '-', status, priority, date, time, body }, keepStatusTag = true) {
  const parts = [`${indent}${bullet} [${boxFromStatus(status)}]`]
  if (body) parts.push(body)
  if (keepStatusTag && status) parts.push(`[${TAG_OF[status]}]`)
  if (priority) parts.push(`[${PRIORITY_TAG[priority]}]`)
  if (date) parts.push(`[${date}]`)
  if (time) parts.push(`[${time}]`)
  return parts.join(' ')
}

/**
 * 从整篇正文里收集所有任务行，附带行号和缩进层级。
 * 返回按文档顺序排列的数组。
 */
export function collectTasks(content) {
  const lines = (content || '').split('\n')
  const out = []
  lines.forEach((text, i) => {
    const t = parseTaskLine(text)
    if (t) out.push({ ...t, line: i, text })
  })
  return out
}

/**
 * 父任务状态汇总：根据子任务推断。
 * 规则（按优先级从高到低）：
 *   有子任务搁置且其他都完成 → 搁置
 *   有子任务未完成、且有已开始（进行中/已完成） → 进行中
 *   全部完成 → 已完成
 *   都没开始 → 待做
 * 返回 { status, total, finished, blocked, inProgress, children }
 */
export function rollupStatus(children) {
  if (!children.length) return null
  let finished = 0, blocked = 0, inProgress = 0
  for (const c of children) {
    if (c.status === 'done') finished++
    else if (c.status === 'blocked') blocked++
    else if (c.status === 'in_progress') inProgress++
  }
  const total = children.length
  let status
  if (finished === total) status = 'done'
  else if (blocked > 0 && finished + blocked === total) status = 'blocked'
  else if (finished > 0 || inProgress > 0) status = 'in_progress'
  else status = 'todo'
  return { status, total, finished, blocked, inProgress }
}

/**
 * 把任务行按缩进组织成树。缩进取当前行的宽度，作为层级依据。
 * 用于任务面板展开子任务。
 */
export function buildTaskTree(content) {
  const rows = collectTasks(content)
  const roots = []
  const stack = []
  for (const row of rows) {
    const node = { ...row, children: [] }
    const width = row.indent.replace(/\t/g, '  ').length
    while (stack.length && stack[stack.length - 1].width >= width) stack.pop()
    if (stack.length) stack[stack.length - 1].node.children.push(node)
    else roots.push(node)
    node.width = width
    stack.push({ width, node })
  }
  // 给每个父节点算汇总
  const annotate = node => {
    if (!node.children.length) return node
    node.children.forEach(annotate)
    node.rollup = rollupStatus(node.children.map(c => ({ status: c.rollup ? c.rollup.status : c.status })))
    return node
  }
  roots.forEach(annotate)
  return roots
}

/**
 * 子任务日期是否逾期（只到天，没时间的按当天结束算）
 */
export function isOverdue(date, time) {
  if (!date) return false
  const now = new Date()
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  if (date > today) return false
  if (date < today) return true
  if (!time) return false
  const [h, mi] = time.split(':').map(Number)
  return now.getHours() * 60 + now.getMinutes() > h * 60 + mi
}
