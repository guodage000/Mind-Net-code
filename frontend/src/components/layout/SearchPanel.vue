<template>
  <div class="search-overlay" @click.self="$emit('close')">
    <div class="search-box">
      <input ref="inputEl" v-model="query" placeholder="搜索笔记... (Esc 关闭)"
             @input="doSearch" @keydown.escape="$emit('close')" class="search-input" />
      <div class="search-results">
        <div v-if="store.searchResults.length === 0 && query" class="no-result">无结果</div>
        <div v-for="r in store.searchResults" :key="r.id" class="result-item"
             @click="$emit('open', r.id)">
          <div class="result-title">{{ r.title }}</div>
          <div class="result-snippet" v-html="r.snippet" />
          <div class="result-meta">
            <span v-for="t in r.tags" :key="t" class="tag">{{ t }}</span>
            <span class="result-date">{{ r.updated_at.slice(0,10) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useNotesStore } from '../../stores/notes'
const store = useNotesStore()
const query = ref('')
const inputEl = ref(null)
onMounted(() => inputEl.value?.focus())
let timer = null
function doSearch() {
  clearTimeout(timer)
  timer = setTimeout(() => store.search(query.value), 250)
}
defineEmits(['close', 'open'])
</script>

<style scoped>
.search-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.55); z-index: 200;
                  display: flex; align-items: flex-start; justify-content: center; padding-top: 80px; }
.search-box { background: var(--color-surface); border-radius: 12px; width: 620px;
              max-height: 70vh; display: flex; flex-direction: column;
              border: 1px solid var(--color-border); overflow: hidden; box-shadow: 0 16px 48px rgba(0,0,0,.5); }
.search-input { background: none; border: none; outline: none; padding: 16px 20px;
                font-size: 16px; color: var(--color-text); border-bottom: 1px solid var(--color-border); }
.search-results { overflow-y: auto; flex: 1; }
.result-item { padding: 12px 20px; cursor: pointer; border-bottom: 1px solid var(--color-border); }
.result-item:hover { background: var(--color-surface2); }
.result-title { font-weight: 600; margin-bottom: 4px; }
.result-snippet { font-size: 12px; color: var(--color-text-dim); margin-bottom: 6px; }
.result-snippet :deep(mark) { background: var(--color-accent); color: var(--color-bg); border-radius: 2px; padding: 0 2px; }
.result-meta { display: flex; gap: 6px; align-items: center; }
.tag { background: var(--color-surface2); color: var(--color-accent2); font-size: 10px; padding: 1px 6px; border-radius: 10px; }
.result-date { font-size: 11px; color: var(--color-text-dim); margin-left: auto; }
.no-result { padding: 24px; text-align: center; color: var(--color-text-dim); }
</style>
