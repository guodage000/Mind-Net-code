<template>
  <div class="subtask-tree">
    <div class="st-header">
      <span>子任务</span>
      <span class="st-count">{{ total }} 项，{{ doneCount }} 已完成</span>
    </div>
    <div class="st-scroll">
      <template v-if="tree.length">
        <SubtaskNode v-for="node in tree" :key="node.line"
                     :node="node" @open="openLine" />
      </template>
      <div v-else class="st-empty">这篇笔记还没有子任务。在正文里写 - [ ] 开头的那行就会出现。</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import SubtaskNode from './SubtaskNode.vue'
import { extractSubtasks } from '../../composables/subtasks.js'

const props = defineProps({
  content: { type: String, default: '' },
  noteId: { type: String, default: '' },
})
const emit = defineEmits(['open'])

const tree = computed(() => extractSubtasks(props.content, props.noteId))
const total = computed(() => countNodes(tree.value))
const doneCount = computed(() => countDone(tree.value))

function countNodes(nodes) { return nodes.reduce((s, n) => s + 1 + countNodes(n.children), 0) }
function countDone(nodes) { return nodes.reduce((s, n) => s + (n.status === 'done' ? 1 : 0) + countDone(n.children), 0) }

function openLine(payload) {
  emit('open', payload)
}

</script>

<style scoped>
.subtask-tree { display: flex; flex-direction: column; flex: 1; min-height: 0; }
.st-header { display: flex; align-items: center; justify-content: space-between;
             padding: 8px 12px 4px; font-size: 11px; font-weight: 600; letter-spacing: .08em;
             text-transform: uppercase; color: var(--color-text-dim); }
.st-count { font-weight: 400; text-transform: none; }
.st-scroll { flex: 1; overflow-y: auto; padding: 4px 0; }
.st-empty { padding: 16px 12px; color: var(--color-text-dim); font-size: 13px; line-height: 1.7; }
</style>
