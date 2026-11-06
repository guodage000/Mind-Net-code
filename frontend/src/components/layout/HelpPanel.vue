<template>
  <div class="overlay" @click.self="close">
    <div class="help">
      <div class="help-head">
        <h3>快速上手</h3>
        <button class="close-btn" @click="close">✕</button>
      </div>
      <div class="help-body">
        <section>
          <h4>1. 新建和整理笔记</h4>
          <p>点左上角文件列表旁的 <b>＋</b>。选「任务」会自动带上任务模板。</p>
          <p>「文件夹」可以填 <code>项目A/模块B</code>，会自动建好层级。标签用逗号分隔，例如 <code>工作, 学习</code>。</p>
        </section>
        <section>
          <h4>2. 不懂 Markdown 也能写</h4>
          <p>在<b>空行开头输入 /</b>，会弹出格式菜单。用 ↑↓ 选择，回车确认。也可以继续输入文字筛选，比如 <code>/rw</code> 找任务、<code>/dm</code> 找代码块。</p>
          <p>选中文字后点工具栏按钮，可以加粗、变成列表、变成任务。编辑区上方的提示条会根据光标所在行告诉你下一步怎么做。</p>
        </section>
        <section>
          <h4>3. 查看和管理任务状态</h4>
          <p>左侧点「任务」标签，所有任务按 <b>待做 / 进行中 / 已完成 / 搁置</b> 分组显示，点上面那排状态按钮可以只看某一类。每条任务右边的下拉框直接改状态。</p>
          <p>在笔记里写任务时，光标放在任务行：</p>
          <ul>
            <li><b>Ctrl+J</b> 循环切换 待做 / 进行中 / 已完成 / 搁置</li>
            <li><b>Ctrl+Shift+J</b> 循环切换 无 / 高 / 中 / 低 优先级</li>
            <li><b>Ctrl+Alt+J</b> 打开属性面板，改截止日期和时间</li>
            <li><b>Tab</b> 缩进成子任务，可以无限层级</li>
          </ul>
          <pre>- [ ] 准备下周汇报 [进行中] [高] [2026-11-10]
  - [x] 整理数据 [已完成]
    - [ ] 写演示稿 [待做] [中] [2026-11-08] [18:00]
  - [ ] 约会议室 [搁置]</pre>
          <p>父任务状态会根据子任务自动汇总：全部完成才算已完成，有进行中的就算进行中，有搁置的算搁置。任务面板里能看到每篇任务的最早截止日期和子任务进度。</p>
        </section>
        <section>
          <h4>4. 任务和子任务怎么排版</h4>
          <pre>- [ ] 准备下周汇报
  - [ ] 整理数据
  - [x] 联系场地</pre>
          <ul>
            <li>在任务行按<b>回车</b>，会自动生成下一条任务</li>
            <li>按 <b>Tab</b>，这一条缩进成上一条的子任务；<b>Shift+Tab</b> 退回上一级</li>
            <li><b>Ctrl+回车</b> 勾选或取消勾选</li>
            <li>空的子任务行按回车，退回上一级；最外层的空任务行连按两次回车，结束任务列表</li>
          </ul>
        </section>
        <section>
          <h4>5. 导入已有的 Markdown</h4>
          <p>点顶部 <b>⬇</b>，选文件夹（自动列出里面所有 .md，可以保留子文件夹层级）或者粘贴具体路径。导入的文件放在「导入」文件夹里，原文件不会动。同名文件会自动加序号。</p>
        </section>
        <section>
          <h4>6. 快捷键</h4>
          <table>
            <tr><td>Ctrl+K</td><td>搜索全部笔记</td></tr>
            <tr><td>Ctrl+S</td><td>立即保存（平时停止输入约 1 秒自动保存）</td></tr>
            <tr><td>Ctrl+B / Ctrl+I</td><td>加粗 / 斜体</td></tr>
            <tr><td>Ctrl+J</td><td>任务状态循环切换</td></tr>
            <tr><td>Ctrl+Shift+J</td><td>任务优先级循环</td></tr>
            <tr><td>Ctrl+Alt+J</td><td>打开任务属性（日期/时间）</td></tr>
            <tr><td>Ctrl+Z / Ctrl+Y</td><td>撤销 / 重做</td></tr>
          </table>
        </section>
        <section>
          <h4>7. 删除和同步</h4>
          <p>标题右边的 🗑，或者鼠标移到左侧文件上点 🗑，都可以删除。</p>
          <p>右下角 ⎇ 是 Git 同步状态。停止修改 30 秒后自动提交一次。已经提交过的版本，删除后也能从 Git 历史里找回。</p>
        </section>
      </div>
      <div class="help-foot">
        <button class="btn-ok" @click="close">知道了</button>
      </div>
    </div>
  </div>
</template>

<script setup>
const emit = defineEmits(['close'])
function close() {
  localStorage.setItem('mindnet-help-seen', '1')
  emit('close')
}
</script>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,.55); z-index: 300;
           display: flex; align-items: center; justify-content: center; }
.help { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 12px;
        width: 640px; max-height: 85vh; display: flex; flex-direction: column;
        box-shadow: 0 16px 48px rgba(0,0,0,.5); }
.help-head { display: flex; align-items: center; justify-content: space-between;
             padding: 16px 20px; border-bottom: 1px solid var(--color-border); }
h3 { color: var(--color-accent); }
.close-btn { background: none; border: none; color: var(--color-text-dim); font-size: 16px; }
.help-body { overflow-y: auto; padding: 8px 20px 16px; font-size: 14px; line-height: 1.7; }
section { margin-top: 14px; }
h4 { color: var(--color-accent2); margin-bottom: 4px; font-size: 14px; }
p { margin-bottom: 4px; }
ul { padding-left: 1.4em; }
code { background: var(--color-surface2); padding: 1px 5px; border-radius: 3px; font-size: 13px; }
pre { background: var(--color-surface2); padding: 10px 12px; border-radius: 6px; font-size: 13px;
      margin: 6px 0; }
table { border-collapse: collapse; }
td { padding: 3px 14px 3px 0; }
td:first-child { color: var(--color-accent); white-space: nowrap; font-family: monospace; }
.help-foot { padding: 12px 20px; border-top: 1px solid var(--color-border); text-align: right; }
.btn-ok { background: var(--color-accent); color: var(--color-bg); border: none;
          padding: 7px 20px; border-radius: 6px; font-weight: 600; }
</style>
