<template>
  <div class="login-manage-page">
    <el-row :gutter="20">
      <!-- 左侧：登录器列表 -->
      <el-col :span="8">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>登录器列表</span>
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
                <el-tag :type="getLoginStatusDataType(row.name)" size="small">
                  {{ getLoginStatusDataText(row.name) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="70" align="center">
              <template #default="{ row }">
                <el-button
                  :icon="Refresh"
                  circle
                  size="small"
                  :loading="refreshingLogin === row.name"
                  @click="handleRefreshLogin(row)"
                />
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
                    :value="type"
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
import type { LoginInfo, LoginStatusData } from '@/api/types'

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
const refreshingLogin = ref<string | null>(null)

const selectedQrType = ref('')
const statusCache = ref<Record<string, LoginStatusData>>({})
const countdown = ref(0)
const qrcodeExpired = ref(false)
let countdownTimer: number | null = null

// 是否可以开始登录（只有未登录状态才可以，或二维码已过期）
const canStartLogin = computed(() => {
  if (!loginStatus.value) return true
  // waiting 状态说明正在等待扫码，不允许重新开始
  if (loginStatus.value.status === 'waiting') return false
  // success 状态已登录，不允许
  if (loginStatus.value.status === 'success') return false
  // 其他状态（not_logged_in、failed）都可以触发登录
  return true
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

  countdownTimer = window.setInterval(async () => {
    countdown.value--
    if (countdown.value <= 0) {
      stopCountdown()
      qrcodeExpired.value = true
      loginStore.stopVerifyPolling()

      // 调用后端 API 清理二维码资源
      if (currentLogin.value) {
        try {
          await loginStore.cleanupQrcodeResources(currentLogin.value.name)
        } catch (error) {
          console.error('清理二维码资源失败:', error)
        }
      }

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
    // 如果不是成功状态，自动重置为未登录状态，允许重新登录
    if (loginStatus.value && loginStatus.value.status !== 'success') {
      const notLoggedInStatus: LoginStatusData = { status: 'not_logged_in', message: '未登录' }
      statusCache.value[currentLogin.value?.name || ''] = notLoggedInStatus
      loginStore.loginStatus = notLoggedInStatus
      qrcodeExpired.value = false
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
  // 如果当前没有选中登录器但有登录状态，尝试从缓存同步
  if (!currentLogin.value && loginStatus.value) {
    // 这种情况不应该发生，但确保状态一致
  }
}

const handleSelectLogin = async (login: LoginInfo | null) => {
  // 在更新状态之前，先保存旧的登录器信息
  const oldLoginName = currentLogin.value?.name
  const wasPolling = polling.value

  loginStore.setCurrentLogin(login)
  loginStore.stopVerifyPolling()
  stopCountdown()

  // 切换登录器时清理之前的二维码资源
  if (oldLoginName && wasPolling) {
    try {
      await loginStore.cleanupQrcodeResources(oldLoginName)
    } catch (error) {
      console.error('清理二维码资源失败:', error)
    }
  }

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
  if (!currentLogin.value) {
    return
  }

  // 实时检查登录状态，而不是使用缓存
  try {
    const realTimeStatus = await loginStore.checkStatus(currentLogin.value.name)

    if (!realTimeStatus) {
      ElMessage.error('无法获取登录状态，请重试')
      return
    }

    // 更新状态缓存
    statusCache.value[currentLogin.value.name] = realTimeStatus
    loginStore.loginStatus = realTimeStatus

    // 如果已登录，不允许再次登录
    if (realTimeStatus.status === 'success') {
      ElMessage.warning('当前已登录，请先清除登录状态')
      return
    }

    // 只有未登录状态才能获取二维码
    if (realTimeStatus.status !== 'not_logged_in' && realTimeStatus.status !== 'failed') {
      ElMessage.warning(realTimeStatus.message || '当前状态不允许登录')
      return
    }

    // 确认未登录后，获取二维码
    await handleGetQrcode()
  } catch (error: any) {
    console.error('检查登录状态失败:', error)
    ElMessage.error(error.message || '检查登录状态失败')
  }
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

    // 开始轮询验证
    loginStore.startVerifyPolling(currentLogin.value.name).then((status) => {
      // 轮询成功完成后，更新状态缓存
      if (status && currentLogin.value) {
        statusCache.value[currentLogin.value.name] = status
        // 如果登录成功，显示成功提示
        if (status.status === 'success') {
          ElMessage.success('登录成功')
        }
      }
    }).catch((error) => {
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

const handleCancelLogin = async () => {
  stopCountdown()
  loginStore.stopVerifyPolling()

  // 调用后端 API 清理二维码资源
  if (currentLogin.value) {
    try {
      await loginStore.cleanupQrcodeResources(currentLogin.value.name)
    } catch (error) {
      console.error('清理二维码资源失败:', error)
    }

    // 重新获取登录状态，确保与后端同步
    const detail = await loginStore.fetchLoginDetail(currentLogin.value.name)
    if (detail?.login_status) {
      loginStore.loginStatus = detail.login_status
      statusCache.value[currentLogin.value.name] = detail.login_status
    } else {
      // 如果后端返回 null，设置默认未登录状态
      const notLoggedInStatus: LoginStatusData = { status: 'not_logged_in', message: '未登录' }
      statusCache.value[currentLogin.value.name] = notLoggedInStatus
      loginStore.loginStatus = notLoggedInStatus
    }
  } else {
    // 如果没有选中登录器，也重置本地状态
    const notLoggedInStatus: LoginStatusData = { status: 'not_logged_in', message: '未登录' }
    loginStore.loginStatus = notLoggedInStatus
  }

  qrcodeExpired.value = false
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
      // 重置所有状态，允许重新登录
      loginStore.qrcode = null
      const notLoggedInStatus: LoginStatusData = { status: 'not_logged_in', message: '未登录' }
      statusCache.value[currentLogin.value.name] = notLoggedInStatus
      loginStore.loginStatus = notLoggedInStatus
      qrcodeExpired.value = false
    } else {
      ElMessage.error('清除失败')
    }
  } catch {
    // 用户取消
  }
}

const getLoginStatusDataType = (loginName: string) => {
  const status = statusCache.value[loginName]?.status || loginStatus.value?.status
  if (status === 'success') return 'success'
  return 'info'
}

const getLoginStatusDataText = (loginName: string) => {
  const status = statusCache.value[loginName]?.status || loginStatus.value?.status
  if (status === 'success') return '已登录'
  return '未登录'
}

// 刷新单个登录器的状态
const handleRefreshLogin = async (login: LoginInfo) => {
  refreshingLogin.value = login.name
  try {
    const status = await loginStore.checkStatus(login.name)
    if (status) {
      statusCache.value[login.name] = status
      // 如果是当前选中的登录器，同时更新 store 中的状态
      if (currentLogin.value?.name === login.name) {
        loginStore.loginStatus = status
      }
      ElMessage.success(`${login.platform} 状态已刷新`)
    }
  } catch (error) {
    console.error('刷新登录状态失败:', error)
    ElMessage.error('刷新失败')
  } finally {
    refreshingLogin.value = null
  }
}

const getAlertType = (status?: string) => {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'error'
  return 'info'
}

// 组件挂载时
onMounted(async () => {
  await fetchLogins()
})

// 组件卸载时
onUnmounted(() => {
  stopCountdown()
  loginStore.stopVerifyPolling()

  // 清理二维码资源
  if (currentLogin.value && qrcode.value) {
    loginStore.cleanupQrcodeResources(currentLogin.value.name).catch(() => {})
  }

  // 重置状态
  loginStore.qrcode = null
  loginStore.loginStatus = null
})
</script>

<style scoped lang="scss">
.login-manage-page {
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
