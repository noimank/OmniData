<template>
  <el-container class="layout-container">
    <AppAside />
    <el-container class="main-container">
      <AppHeader />
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import AppAside from './AppAside.vue'
import AppHeader from './AppHeader.vue'
</script>

<style scoped lang="scss">
.layout-container {
  height: 100vh;

  .main-container {
    display: flex;
    flex-direction: column;
  }

  :deep(.el-main) {
    background-color: #f0f2f5;
    padding: 20px;
  }
}
</style>
