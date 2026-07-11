<template>
  <el-header height="60px" class="app-header">
    <div class="header-content">
      <div class="title">
        <h3>{{ currentTitle }}</h3>
        <span class="build-version">v{{ buildVersion }}</span>
      </div>
      <div class="header-actions">
        <a href="https://github.com/noimank/OmniData" target="_blank" class="action-link github-link">
          <svg class="icon" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
            <path d="M512 42.666667A464.64 464.64 0 0 0 42.666667 502.186667 460.373333 460.373333 0 0 0 363.52 938.666667c23.466667 4.266667 32-9.813333 32-22.186667v-78.08c-130.56 27.733333-158.293333-61.44-158.293333-61.44a122.026667 122.026667 0 0 0-52.053334-67.413333c-42.666667-28.16 3.413333-27.733333 3.413334-27.733334a98.56 98.56 0 0 1 71.68 47.36 101.12 101.12 0 0 0 136.533333 37.973334 99.413333 99.413333 0 0 1 29.866667-61.44c-104.106667-11.52-213.333333-50.773333-213.333334-226.986667a177.066667 177.066667 0 0 1 47.36-124.16 161.28 161.28 0 0 1 4.693334-121.173333s39.68-12.373333 128 46.933333a455.68 455.68 0 0 1 234.666666 0c89.6-59.306667 128-46.933333 128-46.933333a161.28 161.28 0 0 1 4.693334 121.173333A177.066667 177.066667 0 0 1 810.666667 477.866667c0 176.64-110.08 215.466667-213.333334 226.986666a106.666667 106.666667 0 0 1 32 85.333334v125.866666c0 14.933333 8.533333 27.733333 32 22.186667A460.8 460.8 0 0 0 981.333333 502.186667 464.64 464.64 0 0 0 512 42.666667" fill="currentColor"/>
          </svg>
          <span>GitHub</span>
        </a>
        <a href="https://github.com/noimank/OmniData/issues" target="_blank" class="action-link">
          <svg class="icon" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
            <path d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm0 820c-205.4 0-372-166.6-372-372s166.6-372 372-372 372 166.6 372 372-166.6 372-372 372z" fill="currentColor"/>
            <path d="M464 336a48 48 0 1 0 96 0 48 48 0 1 0-96 0zm72 112h-48c-4.4 0-8 3.6-8 8v272c0 4.4 3.6 8 8 8h48c4.4 0 8-3.6 8-8V456c0-4.4-3.6-8-8-8z" fill="currentColor"/>
          </svg>
          <span>Issues</span>
        </a>
        <a href="https://noimank.github.io/OmniData/" target="_blank" class="action-link">
          <svg class="icon" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
            <path d="M832 64H192c-70.4 0-128 57.6-128 128v640c0 70.4 57.6 128 128 128h640c70.4 0 128-57.6 128-128V192c0-70.4-57.6-128-128-128zm0 768H192V192h640v640z" fill="currentColor"/>
            <path d="M288 320h448v64H288zm0 128h448v64H288zm0 128h320v64H288z" fill="currentColor"/>
          </svg>
          <span>文档</span>
        </a>
      </div>
    </div>
  </el-header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const currentTitle = computed(() => route.meta.title as string || 'OmniData')
const buildVersion = __BUILD_VERSION__
</script>

<style scoped lang="scss">
.app-header {
  background-color: #fff;
  border-bottom: 1px solid #e6e6e6;
  padding: 0 20px;

  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
    height: 100%;

    .title {
      display: flex;
      align-items: center;

      h3 {
        margin: 0;
        font-size: 18px;
        color: #303133;
      }

      .build-version {
        font-size: 12px;
        color: #909399;
        background: #f4f4f5;
        padding: 2px 8px;
        border-radius: 10px;
        margin-left: 10px;
        vertical-align: middle;
        font-family: 'SF Mono', 'Cascadia Code', monospace;
      }
    }

    .header-actions {
      display: flex;
      gap: 24px;
      align-items: center;

      .action-link {
        display: flex;
        align-items: center;
        gap: 6px;
        color: #606266;
        text-decoration: none;
        font-size: 14px;
        transition: all 0.3s;
        padding: 6px 12px;
        border-radius: 6px;

        .icon {
          width: 18px;
          height: 18px;
          fill: currentColor;
        }

        &:hover {
          color: #409eff;
          background-color: #f0f7ff;
        }

        &.github-link:hover {
          color: #24292e;
          background-color: #f6f8fa;
        }
      }
    }
  }
}
</style>
