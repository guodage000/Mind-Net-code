// 从正文里提取子任务树，用于左侧栏显示和跳转
// 每个节点带 noteId、行号、状态、优先级、日期、时间

import { parseTaskLine, buildTaskTree } from './taskMarkers.js'

/**
 * 从一篇笔记的正文里提取子任务树。
 * 返回 [{ line, body, status, priority, date, time, children, hasDate, overdue }]
 */
export function extractSubtasks(content, noteId) {
  const tree = buildTaskTree(content || '')
  const walk = (nodes, depth = 0) => nodes.map(node => ({
    noteId,
    line: node.line,
    body: node.body || '（未命名子任务）',
    status: node.status,
    priority: node.priority,
    date: node.date,
    time: node.time,
    depth,
    children: walk(node.children, depth + 1),
  }))
  return walk(tree)
}

/**
 * 统计一篇笔记里未完成的子任务数（不含已完成）
 */
export function countOpenSubtasks(content) {
  const rows = (content || '').split('\n')
  let open = 0
  for (const line of rows) {
    const t = parseTaskLine(line)
    if (t && t.status !== 'done') open++
  }
  return open
}

/**
 * 生成用于跳转的锚点。CodeMirror 里用行号定位。
 */
export function lineAnchor(line) {
  return { line }
}
