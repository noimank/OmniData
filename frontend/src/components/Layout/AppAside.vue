<template>
  <el-aside width="200px" class="app-aside">
    <div class="logo">
      <img src="/logo-icon.svg" alt="OmniData" class="logo-icon" />
      <h2>OmniData</h2>
    </div>
    <el-menu
      :default-active="activeMenu"
      router
      background-color="#304156"
      text-color="#bfcbd9"
      active-text-color="#409eff"
    >
      <el-menu-item index="/monitor">
        <el-icon><Monitor /></el-icon>
        <span>系统监控</span>
      </el-menu-item>
      <el-menu-item index="/login-manage">
        <el-icon><User /></el-icon>
        <span>登录管理</span>
      </el-menu-item>
      <el-menu-item index="/spider">
        <el-icon><Setting /></el-icon>
        <span>爬虫测试</span>
      </el-menu-item>
    </el-menu>
  </el-aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Monitor, User, Setting } from '@element-plus/icons-vue'

const route = useRoute()
const activeMenu = computed(() => route.path)
</script>

<style scoped lang="scss">
.app-aside {
  background-color: #304156;
  height: 100%;
  overflow-x: hidden;
  overflow-y: auto;

  .logo {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    background-color: #2b3a4a;
    padding: 0 10px;

    .logo-icon {
      width: 32px;
      height: 32px;
    }

    h2 {
      color: #fff;
      font-size: 18px;
      margin: 0;
      font-weight: 600;
    }
  }

  .el-menu {
    border-right: none;
  }
}
</style>
