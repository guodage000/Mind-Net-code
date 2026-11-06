<template>
  <div class="tree-item">
    <div class="tree-row" :class="{ dir: node.is_dir, active: !node.is_dir && node.path === activeId }"
         :style="{ paddingLeft: depth * 12 + 6 + 'px' }" @click="onClick">
      <span class="tree-icon">{{ node.is_dir ? (open ? '▾' : '▸') : '📄' }}</span>
      <span class="tree-name">{{ displayName }}</span>
      <button v-if="!node.is_dir" class="del-btn" title="删除" @click.stop="$emit('delete', node.path)">🗑</button>
    </div>
    <template v-if="node.is_dir && open">
      <TreeNode v-for="child in node.children" :key="child.path"
                :node="child" :depth="depth + 1" :active-id="activeId"
                @open="$emit('open', $event)" @delete="$emit('delete', $event)" />
    </template>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
const props = defineProps({
  node: Object,
  depth: { type: Number, default: 0 },
  activeId: { type: String, default: '' },
})
const emit = defineEmits(['open', 'delete'])
const open = ref(props.depth < 2)
const displayName = computed(() => props.node.is_dir ? props.node.name : props.node.name.replace(/\.md$/i, ''))
function onClick() {
  if (props.node.is_dir) open.value = !open.value
  else emit('open', props.node.path)
}
</script>

<style scoped>
.tree-row { display: flex; align-items: center; gap: 6px; padding: 3px 6px 3px 0;
            border-radius: 4px; cursor: pointer; font-size: 13px; }
.tree-row:hover { background: var(--color-surface2); }
.tree-row.active { background: var(--color-surface2); color: var(--color-accent); }
.tree-icon { width: 16px; text-align: center; color: var(--color-text-dim); flex-shrink: 0; font-size: 11px; }
.tree-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.del-btn { background: none; border: none; font-size: 12px; padding: 0 4px; opacity: 0;
           border-radius: 3px; }
.tree-row:hover .del-btn { opacity: .6; }
.del-btn:hover { opacity: 1 !important; background: var(--color-border); }
</style>
