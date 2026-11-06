// 新建笔记时使用的模板和默认文件夹

export const DEFAULT_FOLDERS = {
  note: '笔记',
  task: '任务',
  ai_summary: 'AI总结',
}

// 把标题转成合法文件名：去掉 Windows 不允许的字符
export function safeName(title) {
  return (title || '').trim().replace(/[\\/:*?"<>|]/g, '_').replace(/[. ]+$/, '')
}

export const TEMPLATES = {
  note: `## 背景

## 要点

- 

## 参考
`,
  task: `## 目标


## 子任务

- [ ] 第一步 [待做]
  - [ ] 拆得更细的子任务（在任务行按 Tab 缩进）[待做]
- [ ] 第二步 [待做]

> 光标放在任务行按 Ctrl+J，可以在 待做 → 进行中 → 已完成 → 搁置 之间切换。

## 进展记录

`,
  ai_summary: `## 来源

- 工具：
- 对话主题：

## 摘要


## 要点

- 
`,
}
