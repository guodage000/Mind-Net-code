<template>
  <div class="file-tree">
    <div class="tree-header">
      <span>文件</span>
      <div class="head-actions">
        <button class="icon-btn" @click="$emit('new-note')" title="新建笔记">＋</button>
      </div>
    </div>
    <div class="tree-scroll">
      <template v-if="tree">
        <template v-for="child in filteredChildren(tree)" :key="child.path">
          <TreeNode :node="child" :depth="0" :active-id="activeId"
                    @open="$emit('open', $event)" @delete="$emit('delete', $event)" />
        </template>
        <div v-if="!filteredChildren(tree).length" class="tree-empty">
          还没有笔记，点上面的 ＋ 新建，或点顶部 ⬇ 导入
        </div>
      </template>
      <div v-else class="tree-empty">加载中...</div>
    </div>
  </div>
</template>

<script setup>
import TreeNode from './TreeNode.vue'
defineProps({ tree: Object, activeId: { type: String, default: '' } })
defineEmits(['open', 'new-note', 'delete'])

// 文件栏不显示任务文件，也不显示只装任务的文件夹
function filteredChildren(node) {
  if (!node?.children) return []
  return node.children.filter(c => {
    if (!c.is_dir) return c.note_type !== 'task'
    return filteredChildren(c).length > 0
  })
}
</script>

<style scoped>
.file-tree { display: flex; flex-direction: column; flex: 1; min-height: 0; }
.tree-header { display: flex; align-items: center; justify-content: space-between;
               padding: 6px 12px 2px; font-size: 11px; font-weight: 600; letter-spacing: .08em;
               text-transform: uppercase; color: var(--color-text-dim); }
.icon-btn { background: none; border: none; color: var(--color-text-dim); font-size: 18px;
            line-height: 1; padding: 0 4px; border-radius: 4px; }
.icon-btn:hover { background: var(--color-border); color: var(--color-text); }
.tree-scroll { flex: 1; overflow-y: auto; padding: 4px 0; }
.tree-empty { padding: 16px 12px; color: var(--color-text-dim); font-size: 13px; line-height: 1.7; }
</style>
