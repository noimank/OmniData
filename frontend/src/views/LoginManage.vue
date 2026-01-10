<template>
  <div class="login-manage-page">
    <!-- 加载进度提示 -->
    <el-alert
      v-if="loading"
      title="正在检查登录状态..."
      type="info"
      :closable="false"
      show-icon
      class="loading-alert"
    >
      <template #default>
        <div class="loading-info">
          <span>并发检查中，请稍候...</span>
          <el-text type="info" size="small">
            预计需要几秒钟时间
          </el-text>
        </div>
      </template>
    </el-alert>

    <el-row :gutter="20">
      <!-- 左侧：登录器列表 -->
      <el-col :span="8">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>登录器列表</span>
              <el-button :icon="Refresh" @click="fetchLogins" :loading="loading" circle />
            </div>
          </template>

          <!-- 骨架屏 -->
          <el-skeleton v-if="loading" :rows="5" animated />

          <!-- 实际内容 -->
          <el-table
            v-else
            :data="logins"
            highlight-current-row
            @current-change="handleSelectLogin"
            max-height="500"
          >
            <el-table-column prop="name" label="名称" show-overflow-tooltip />
            <el-table-column prop="platform" label="平台" width="100" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="getLoginStatusType(row.name)" size="small">
                  {{ getLoginStatusText(row.name) }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-if="!loading && logins.length === 0" description="暂无登录器" />
        </el-card>
      </el-col>

      <!-- 右侧：登录详情 -->
      <el-col :span="16">
        <el-card v-if="currentLogin">
          <template #header>
            <div class="card-header">
              <span>{{ currentLogin.name }} - {{ currentLogin.description }}</span>
              <el-tag v-if="loginStatus" :type="getAlertType(loginStatus.status)" size="small">
                {{ loginStatus.message || '未登录' }}
              </el-tag>
            </div>
          </template>

          <!-- 登录器基本信息 -->
          <el-descriptions :column="2" border class="info-section">
            <el-descriptions-item label="平台">{{ currentLogin.platform }}</el-descriptions-item>
            <el-descriptions-item label="版本">{{ currentLogin.version }}</el-descriptions-item>
            <el-descriptions-item label="描述" :span="2">{{ currentLogin.description }}</el-descriptions-item>
          </el-descriptions>

          <!-- 登录操作区域 -->
          <div class="action-section">
            <!-- 已登录状态 -->
            <div v-if="loginStatus?.status === 'success'" class="logged-in-state">
              <el-result icon="success" title="登录成功" sub-title="您已成功登录，可以使用相关功能">
                <template #extra>
                  <el-button type="danger" @click="handleClearSession">清除登录状态</el-button>
                </template>
              </el-result>
            </div>

            <!-- 未登录状态 - 显示登录选项 -->
            <div v-else class="login-options">
              <!-- 二维码类型选择 -->
              <div class="qr-type-selector">
                <div class="selector-label">
                  <el-icon><Position /></el-icon>
                  <span>选择登录方式</span>
                </div>
                <el-radio-group v-model="selectedQrType" size="large" :disabled="canStartLogin === false">
                  <el-radio-button
                    v-for="type in currentLogin.qrcode_types || ['default']"
                    :key="type"
                    :label="type"
                  >
                    {{ type }}
                  </el-radio-button>
                </el-radio-group>
              </div>

              <!-- 开始登录按钮 -->
              <div class="start-login-btn">
                <el-tooltip
                  v-if="!canStartLogin"
                  effect="dark"
                  placement="top"
                  :content="loginStatus?.message || '当前状态不允许登录'"
                >
                  <el-button
                    type="primary"
                    size="large"
                    :loading="qrcodeLoading"
                    :disabled="true"
                  >
                    无法登录
                  </el-button>
                </el-tooltip>
                <el-button
                  v-else
                  type="primary"
                  size="large"
                  :loading="qrcodeLoading"
                  :disabled="polling"
                  @click="handleStartLogin"
                >
                  {{ qrcodeLoading ? '生成二维码中...' : polling ? '等待扫码...' : '开始登录' }}
                </el-button>
              </div>

              <!-- 二维码显示区域 -->
              <div v-if="qrcode && qrcode.url" class="qrcode-display">
                <el-divider content-position="left">
                  <span class="divider-text">
                    <el-icon><Cellphone /></el-icon>
                    扫码登录
                  </span>
                </el-divider>

                <div class="qrcode-wrapper">
                  <el-image :src="qrcode.url" fit="contain" class="qrcode-image">
                    <template #error>
                      <div class="image-error">
                        <el-icon :size="48"><PictureFilled /></el-icon>
                        <span>二维码加载失败</span>
                        <el-button size="small" @click="handleGetQrcode">重新获取</el-button>
                      </div>
                    </template>
                    <template #placeholder>
                      <div class="image-loading">
                        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
                      </div>
                    </template>
                  </el-image>

                  <!-- 刷新按钮 -->
                  <el-button
                    v-if="!polling"
                    class="refresh-qr-btn"
                    :icon="RefreshRight"
                    circle
                    size="small"
                    @click="handleGetQrcode"
                  />
                </div>

                <!-- 倒计时进度条 -->
                <div v-if="countdown > 0" class="countdown-section">
                  <div class="countdown-info">
                    <span class="countdown-text">二维码有效期</span>
                    <span class="countdown-time">{{ formatCountdown(countdown) }}</span>
                  </div>
                  <el-progress
                    :percentage="(countdown / QR_CODE_EXPIRE_TIME) * 100"
                    :color="getProgressColor(countdown)"
                    :show-text="false"
                    class="countdown-progress"
                  />
                </div>

                <!-- 二维码已过期 -->
                <div v-else-if="qrcodeExpired" class="qrcode-expired">
                  <el-alert
                    title="二维码已过期"
                    type="warning"
                    :closable="false"
                    show-icon
                  >
                    <el-button type="primary" size="small" @click="handleGetQrcode">
                      刷新二维码
                    </el-button>
                  </el-alert>
                </div>

                <!-- 轮询提示 -->
                <div v-if="polling && countdown > 0" class="polling-status">
                  <el-icon class="is-loading"><Loading /></el-icon>
                  <span>请使用手机扫码确认登录...</span>
                </div>

                <!-- 取消按钮 -->
                <div v-if="polling" class="cancel-btn">
                  <el-button size="small" @click="handleCancelLogin">取消登录</el-button>
                </div>
              </div>
            </div>
          </div>
        </el-card>

        <el-card v-else>
          <el-empty description="请从左侧选择登录器">
            <template #image>
              <el-icon :size="80" color="#909399"><Select /></el-icon>
            </template>
          </el-empty>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useLoginStore } from '@/stores/login'
import {
  Refresh,
  Loading,
  PictureFilled,
  Position,
  Cellphone,
  RefreshRight,
  Select
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { LoginInfo, LoginStatus } from '@/api/types'

const loginStore = useLoginStore()

// 二维码过期时间（秒）
const QR_CODE_EXPIRE_TIME = 30

const logins = computed(() => loginStore.logins)
const currentLogin = computed(() => loginStore.currentLogin)
const qrcode = computed(() => loginStore.qrcode)
const loginStatus = computed(() => loginStore.loginStatus)
const polling = computed(() => loginStore.polling)
const loading = computed(() => loginStore.loading)
const qrcodeLoading = ref(false)

const selectedQrType = ref('')
const statusCache = ref<Record<string, LoginStatus>>({})
const countdown = ref(0)
const qrcodeExpired = ref(false)
let countdownTimer: number | null = null

// 是否可以开始登录（只有未登录状态才可以，或二维码已过期）
const canStartLogin = computed(() => {
  if (!loginStatus.value) return true
  // 二维码过期或未登录/失败状态都可以触发登录
  return qrcodeExpired.value ||
         loginStatus.value.status === 'not_logged_in' ||
         loginStatus.value.status === 'failed'
})

// 格式化倒计时
const formatCountdown = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return mins > 0 ? `${mins}:${secs.toString().padStart(2, '0')}` : `${secs}s`
}

// 获取进度条颜色
const getProgressColor = (seconds: number) => {
  const percentage = (seconds / QR_CODE_EXPIRE_TIME) * 100
  if (percentage > 50) return '#67c23a'
  if (percentage > 20) return '#e6a23c'
  return '#f56c6c'
}

// 开始倒计时
const startCountdown = () => {
  stopCountdown()
  countdown.value = QR_CODE_EXPIRE_TIME
  qrcodeExpired.value = false

  countdownTimer = window.setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      stopCountdown()
      qrcodeExpired.value = true
      loginStore.stopVerifyPolling()
      // 重置为未登录状态
      loginStore.loginStatus = { status: 'not_logged_in', message: '未登录' }
      ElMessage.warning('二维码已过期，请刷新')
    }
  }, 1000)
}

// 停止倒计时
const stopCountdown = () => {
  if (countdownTimer !== null) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
  // 注意：不在这里重置 qrcodeExpired，让调用者决定
}

// 监听 polling 状态，登录成功或取消时停止倒计时
watch(polling, (newVal, oldVal) => {
  // 轮询停止时
  if (!newVal && oldVal) {
    stopCountdown()
    // 如果不是成功状态，重置为未登录
    if (loginStatus.value?.status !== 'success') {
      loginStore.loginStatus = { status: 'not_logged_in', message: '未登录' }
    }
  }
})

const fetchLogins = async () => {
  await loginStore.fetchLogins()
  // 初始化状态缓存，从列表中的 login_status 字段获取
  logins.value.forEach((login: any) => {
    if (login.login_status) {
      statusCache.value[login.name] = login.login_status
    }
  })
}

const handleSelectLogin = async (login: LoginInfo | null) => {
  loginStore.setCurrentLogin(login)
  loginStore.stopVerifyPolling()
  stopCountdown()

  if (login) {
    // 先从缓存中设置状态，避免闪烁
    loginStore.qrcode = null
    if (statusCache.value[login.name]) {
      loginStore.loginStatus = statusCache.value[login.name]
    } else {
      loginStore.loginStatus = null
    }

    // 获取登录器详情（已包含登录状态）
    const detail = await loginStore.fetchLoginDetail(login.name)
    if (detail && detail.qrcode_types && detail.qrcode_types.length > 0) {
      selectedQrType.value = detail.qrcode_types[0]
    } else {
      selectedQrType.value = 'default'
    }

    // 从详情中获取登录状态（后端已返回）
    if (detail?.login_status) {
      loginStore.loginStatus = detail.login_status
      statusCache.value[login.name] = detail.login_status
    }
  }
}

const handleStartLogin = async () => {
  if (!currentLogin.value || !canStartLogin.value) {
    ElMessage.warning('当前状态不允许登录')
    return
  }
  await handleGetQrcode()
}

const handleGetQrcode = async () => {
  if (!currentLogin.value || !canStartLogin.value) {
    ElMessage.warning('当前状态不允许登录')
    return
  }

  qrcodeLoading.value = true
  stopCountdown()
  qrcodeExpired.value = false  // 重置过期状态

  try {
    const result = await loginStore.fetchQrcode(currentLogin.value.name, selectedQrType.value)
    if (!result || !result.url) {
      ElMessage.error('获取二维码失败：返回数据为空')
      qrcodeLoading.value = false
      return
    }

    // 开始倒计时
    startCountdown()

    // 开始轮询验证（不阻塞）
    loginStore.startVerifyPolling(currentLogin.value.name).catch((error) => {
      console.error('轮询验证失败:', error)
      stopCountdown()
      qrcodeExpired.value = true
      ElMessage.error('验证登录状态失败')
    })
  } catch (error: any) {
    console.error('获取二维码失败:', error)
    ElMessage.error(error.message || '获取二维码失败')
  } finally {
    qrcodeLoading.value = false
  }
}

const handleCancelLogin = () => {
  stopCountdown()
  loginStore.stopVerifyPolling()
  loginStore.qrcode = null
  // 直接重置为未登录状态
  loginStore.loginStatus = { status: 'not_logged_in', message: '未登录' }
  ElMessage.info('已取消登录')
}

const handleClearSession = async () => {
  if (!currentLogin.value) return

  try {
    await ElMessageBox.confirm('确定要清除登录状态吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    stopCountdown()
    const success = await loginStore.clearSession(currentLogin.value.name)
    if (success) {
      ElMessage.success('登录状态已清除')
      // 直接设置为未登录状态
      const notLoggedInStatus: LoginStatus = { status: 'not_logged_in', message: '未登录' }
      statusCache.value[currentLogin.value.name] = notLoggedInStatus
      loginStore.loginStatus = notLoggedInStatus
      loginStore.qrcode = null
    } else {
      ElMessage.error('清除失败')
    }
  } catch {
    // 用户取消
  }
}

const getLoginStatusType = (loginName: string) => {
  const status = statusCache.value[loginName]?.status || loginStatus.value?.status
  if (status === 'success') return 'success'
  return 'info'
}

const getLoginStatusText = (loginName: string) => {
  const status = statusCache.value[loginName]?.status || loginStatus.value?.status
  if (status === 'success') return '已登录'
  return '未登录'
}

const getAlertType = (status?: string) => {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'error'
  return 'info'
}

onMounted(() => {
  fetchLogins()
})

onUnmounted(() => {
  stopCountdown()
  loginStore.stopVerifyPolling()
})
</script>

<style scoped lang="scss">
.login-manage-page {
  .loading-alert {
    margin-bottom: 20px;

    .loading-info {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 500;

    span {
      font-size: 16px;
    }
  }

  .info-section {
    margin-bottom: 24px;
  }

  .action-section {
    min-height: 300px;

    .logged-in-state {
      padding: 20px 0;
    }

    .login-options {
      .qr-type-selector {
        margin-bottom: 24px;

        .selector-label {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 12px;
          font-size: 15px;
          font-weight: 500;
          color: #303133;

          .el-icon {
            color: #409eff;
          }
        }

        :deep(.el-radio-group) {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
        }
      }

      .start-login-btn {
        display: flex;
        justify-content: center;
        margin-bottom: 24px;

        .el-button {
          min-width: 160px;
          font-size: 16px;
        }
      }

      .qrcode-display {
        max-width: 400px;
        margin: 0 auto;

        .el-divider {
          margin: 24px 0 32px;

          .divider-text {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 14px;
            color: #606266;
          }
        }

        .qrcode-wrapper {
          position: relative;
          display: inline-block;

          .qrcode-image {
            width: 220px;
            height: 220px;
            border: 2px solid #e4e7ed;
            border-radius: 8px;
            box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);

            :deep(.el-image__inner) {
              width: 100%;
              height: 100%;
            }

            .image-error,
            .image-loading {
              display: flex;
              flex-direction: column;
              align-items: center;
              justify-content: center;
              height: 100%;
              gap: 12px;
              color: #909399;

              .el-icon {
                font-size: 48px;
              }
            }
          }

          .refresh-qr-btn {
            position: absolute;
            top: 8px;
            right: 8px;
            opacity: 0;
            transition: opacity 0.3s;
          }

          &:hover .refresh-qr-btn {
            opacity: 1;
          }
        }

        .countdown-section {
          margin-top: 20px;
          padding: 16px;
          background: #f5f7fa;
          border-radius: 8px;

          .countdown-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;

            .countdown-text {
              font-size: 13px;
              color: #606266;
            }

            .countdown-time {
              font-size: 18px;
              font-weight: 600;
              color: #409eff;
            }
          }

          .countdown-progress {
            :deep(.el-progress-bar__outer) {
              height: 8px !important;
            }
          }
        }

        .qrcode-expired {
          margin-top: 16px;

          :deep(.el-alert) {
            .el-alert__content {
              display: flex;
              align-items: center;
              gap: 12px;
            }
          }
        }

        .polling-status {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          margin-top: 16px;
          padding: 12px;
          color: #409eff;
          font-size: 14px;

          .el-icon {
            font-size: 18px;
          }
        }

        .cancel-btn {
          display: flex;
          justify-content: center;
          margin-top: 16px;
        }
      }
    }
  }
}
</style>
