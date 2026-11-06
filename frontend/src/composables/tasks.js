// 任务状态、优先级等共用的显示规则

export const TASK_STATUSES = [
  { key: 'todo', label: '待做', icon: '○', color: 'var(--color-text-dim)' },
  { key: 'in_progress', label: '进行中', icon: '◐', color: 'var(--color-warn)' },
  { key: 'done', label: '已完成', icon: '●', color: 'var(--color-success)' },
  { key: 'blocked', label: '搁置', icon: '‖', color: 'var(--color-danger)' },
]

export const PRIORITIES = [
  { key: 'high', label: '高' },
  { key: 'medium', label: '中' },
  { key: 'low', label: '低' },
]

export function statusMeta(key) {
  return TASK_STATUSES.find(s => s.key === key) || TASK_STATUSES[0]
}

export function priorityLabel(key) {
  return (PRIORITIES.find(p => p.key === key) || {}).label || ''
}

// 行首任务复选框标记（用于编辑器高亮）
export function findTaskLine(text) {
  return text.match(/^(\s*[-*+]\s+\[)([ xX])(\]\s*)(.*)$/)
}
