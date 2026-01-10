<template>
  <el-header height="60px" class="app-header">
    <div class="header-content">
      <div class="title">
        <h3>{{ currentTitle }}</h3>
      </div>
    </div>
  </el-header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const currentTitle = computed(() => route.meta.title as string || 'OmniData')
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
      h3 {
        margin: 0;
        font-size: 18px;
        color: #303133;
      }
    }
  }
}
</style>
