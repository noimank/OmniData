<template>
  <div class="login-page">
    <el-card class="login-card">
      <template #header>
        <div class="card-header">
          <h2>OmniData 管理平台</h2>
        </div>
      </template>

      <!-- 检测中 -->
      <div v-if="checking" class="checking">
        <el-icon class="is-loading" :size="32">
          <Loading />
        </el-icon>
        <p>检测认证配置...</p>
      </div>

      <!-- 不需要认证 -->
      <div v-else-if="!isRequired" class="no-auth">
        <el-result icon="success" title="系统无需认证">
          <template #sub-title>
            <p>系统未配置 API KEY，可以直接访问</p>
          </template>
        </el-result>
        <el-button type="primary" size="large" @click="handleEnter">
          进入系统
        </el-button>
      </div>

      <!-- 需要认证 -->
      <div v-else class="auth-form">
        <el-form @submit.prevent="handleLogin">
          <el-form-item label="API KEY">
            <el-input
              v-model="inputKey"
              type="password"
              placeholder="请输入 API KEY"
              show-password
              :disabled="loading"
              @keyup.enter="handleLogin"
            />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              native-type="submit"
              :loading="loading"
              style="width: 100%"
            >
              验证
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()

const checking = ref(true)
const isRequired = ref(false)
const inputKey = ref('')
const loading = ref(false)

onMounted(async () => {
  // 检查是否需要 API KEY
  isRequired.value = await authStore.checkRequired()
  checking.value = false

  // 如果已有保存的 KEY，尝试验证
  const savedKey = localStorage.getItem('x-api-key')
  if (savedKey && isRequired.value) {
    inputKey.value = savedKey
    await handleLogin()
  }
})

const handleLogin = async () => {
  if (!inputKey.value.trim()) {
    ElMessage.warning('请输入 API KEY')
    return
  }

  loading.value = true
  try {
    const valid = await authStore.verifyApiKey(inputKey.value)
    if (valid) {
      ElMessage.success('验证成功')
      router.push('/')
    } else {
      ElMessage.error('API KEY 验证失败')
    }
  } catch (error) {
    ElMessage.error('验证失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

const handleEnter = () => {
  router.push('/')
}
</script>

<style scoped lang="scss">
.login-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

  .login-card {
    width: 400px;

    .card-header {
      text-align: center;

      h2 {
        margin: 0;
        color: #303133;
      }
    }
  }

  .checking,
  .no-auth,
  .auth-form {
    text-align: center;
    padding: 20px;
  }

  .checking {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    color: #909399;
  }

  .no-auth {
    .el-button {
      margin-top: 20px;
    }
  }

  .auth-form {
    text-align: left;
  }
}
</style>
