<template>
  <el-header height="60px" class="app-header">
    <div class="header-content">
      <div class="title">
        <h3>{{ currentTitle }}</h3>
      </div>
      <div class="actions">
        <el-button v-if="apiKey" type="danger" text @click="handleLogout">
          退出登录
        </el-button>
        <el-tag v-else type="success">无需认证</el-tag>
      </div>
    </div>
  </el-header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const currentTitle = computed(() => route.meta.title as string || 'OmniData')
const apiKey = computed(() => authStore.apiKey)

const handleLogout = () => {
  ElMessageBox.confirm('确定要退出登录吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    authStore.clearAuth()
    router.push('/login')
  })
}
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
