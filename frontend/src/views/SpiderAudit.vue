<template>
  <div class="spider-audit-page">
    <!-- 统计卡片区域 -->
    <el-row :gutter="20">
      <!-- 今日调用统计 -->
      <el-col :span="6">
        <el-card v-loading="loading">
          <template #header>
            <div class="card-header">
              <span>今日调用</span>
              <el-icon color="#409eff"><DataLine /></el-icon>
            </div>
          </template>
          <div v-if="stats" class="stats-content">
            <div class="stat-item">
              <span class="label">总调用</span>
              <span class="value">{{ stats.today_count }}</span>
            </div>
            <div class="stat-item">
              <span class="label">成功</span>
              <span class="value success">{{ stats.today_success_count }}</span>
            </div>
            <div class="stat-item">
              <span class="label">失败</span>
              <span class="value warning">{{ stats.today_failure_count }}</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 历史总计 -->
      <el-col :span="6">
        <el-card v-loading="loading">
          <template #header>
            <div class="card-header">
              <span>历史总计</span>
              <el-icon color="#67c23a"><FolderOpened /></el-icon>
            </div>
          </template>
          <div v-if="stats" class="stats-content">
            <div class="stat-item">
              <span class="label">总记录数</span>
              <span class="value">{{ stats.total_count }}</span>
            </div>
            <div class="stat-item">
              <span class="label">7天成功率</span>
              <span class="value">{{ stats.recent_success_rate }}%</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 按小时趋势 -->
      <el-col :span="12">
        <el-card v-loading="loading">
          <template #header>
            <div class="card-header">
              <span>24小时趋势</span>
              <el-icon color="#e6a23c"><TrendCharts /></el-icon>
            </div>
          </template>
          <div
            v-if="stats && stats.hourly_stats.length > 0"
            class="hourly-chart"
          >
            <div
              v-for="(item, index) in stats.hourly_stats"
              :key="index"
              class="hourly-bar-container"
            >
              <div class="hourly-label">{{ item.hour }}</div>
              <div class="hourly-bar-wrapper">
                <div
                  class="hourly-bar success"
                  :style="{
                    width:
                      getHourlyBarWidth(item.count, stats.hourly_stats) + '%',
                  }"
                  :title="`成功: ${item.success_count}`"
                ></div>
                <div
                  class="hourly-bar failure"
                  :style="{
                    width:
                      getHourlyBarWidth(item.count, stats.hourly_stats) + '%',
                  }"
                  :title="`失败: ${item.failure_count}`"
                ></div>
              </div>
              <div class="hourly-count">{{ item.count }}</div>
            </div>
          </div>
          <div v-else class="no-data">暂无数据</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 平台分布 & 热门爬虫 & 最近失败 -->
    <el-row :gutter="20" class="mt-20">
      <!-- 平台分布 -->
      <el-col :span="8">
        <el-card v-loading="loading">
          <template #header>
            <div class="card-header">
              <span>平台分布（今日）</span>
              <el-icon color="#e6a23c"><PieChart /></el-icon>
            </div>
          </template>
          <div
            v-if="stats && stats.platform_stats.length > 0"
            class="platform-stats"
          >
            <div
              v-for="item in stats.platform_stats"
              :key="item.platform"
              class="platform-item"
            >
              <div class="platform-info">
                <span class="platform-name">{{ item.platform }}</span>
                <span class="platform-count">{{ item.count }}次</span>
              </div>
              <el-progress
                :percentage="getPlatformPercentage(item.count)"
                :show-text="false"
              />
            </div>
          </div>
          <div v-else class="no-data">暂无数据</div>
        </el-card>
      </el-col>

      <!-- 热门爬虫排行 -->
      <el-col :span="8">
        <el-card v-loading="loading">
          <template #header>
            <div class="card-header">
              <span>热门爬虫（今日）</span>
              <el-icon color="#409eff"><Trophy /></el-icon>
            </div>
          </template>
          <div
            v-if="stats && stats.spider_ranking.length > 0"
            class="spider-ranking"
          >
            <div
              v-for="(item, index) in stats.spider_ranking"
              :key="item.spider_name"
              class="spider-ranking-item"
            >
              <div class="ranking-number" :class="getRankingClass(index)">
                {{ index + 1 }}
              </div>
              <div class="ranking-info">
                <div class="spider-name">{{ item.spider_name }}</div>
                <div class="spider-count">{{ item.count }}次调用</div>
              </div>
            </div>
          </div>
          <div v-else class="no-data">暂无数据</div>
        </el-card>
      </el-col>

      <!-- 最近失败记录 -->
      <el-col :span="8">
        <el-card v-loading="loading">
          <template #header>
            <div class="card-header">
              <span>最近失败</span>
              <el-icon color="#f56c6c"><Warning /></el-icon>
            </div>
          </template>
          <div
            v-if="stats && stats.recent_failures.length > 0"
            class="recent-failures"
          >
            <div
              v-for="item in stats.recent_failures"
              :key="item.id"
              class="failure-item"
            >
              <div class="failure-spider">{{ item.spider_name }}</div>
              <div class="failure-error">{{ item.error_message }}</div>
              <div class="failure-time">
                {{ formatDateTime(item.started_at) }}
              </div>
            </div>
          </div>
          <div v-else class="no-data">暂无失败记录</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 审计记录列表 -->
    <el-card class="mt-20" v-loading="loading">
      <template #header>
        <div class="table-header">
          <span>调用记录</span>
          <div class="header-actions">
            <el-button
              v-if="selectedRecords.length > 0"
              type="danger"
              size="small"
              @click="handleBatchDelete"
            >
              <el-icon><Delete /></el-icon>
              批量删除 ({{ selectedRecords.length }})
            </el-button>
            <el-button
              v-if="selectedRecords.length > 0"
              size="small"
              @click="handleClearSelection"
            >
              取消选择
            </el-button>
            <el-button type="danger" plain size="small" @click="handleCleanup">
              <el-icon><Delete /></el-icon>
              清理
            </el-button>
            <el-button type="primary" size="small" @click="handleRefresh">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <!-- 筛选条件 -->
      <div class="filter-section">
        <el-form :inline="true" :model="queryParams">
          <el-form-item label="平台">
            <el-select
              v-model="queryParams.platform"
              placeholder="全部平台"
              clearable
              @change="handlePlatformChange"
              style="width: 150px"
            >
              <el-option
                v-for="platform in platforms"
                :key="platform"
                :label="platform"
                :value="platform"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="爬虫">
            <el-select
              v-model="queryParams.spider_name"
              placeholder="输入或选择爬虫"
              clearable
              filterable
              :filter-method="filterSpiders"
              @change="auditStore.fetchRecords()"
              style="width: 200px"
            >
              <el-option
                v-for="spider in filteredSpiderOptions"
                :key="spider"
                :label="spider"
                :value="spider"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="状态">
            <el-select
              v-model="queryParams.success"
              placeholder="全部状态"
              clearable
              @change="auditStore.fetchRecords()"
              style="width: 120px"
            >
              <el-option label="成功" :value="true" />
              <el-option label="失败" :value="false" />
            </el-select>
          </el-form-item>

          <el-form-item label="日期范围">
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              @change="handleDateRangeChange"
              style="width: 240px"
            />
          </el-form-item>

          <el-form-item>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 数据表格 -->
      <el-table
        ref="tableRef"
        :data="records"
        row-key="id"
        stripe
        @selection-change="handleSelectionChange"
      >
        <el-table-column
          type="selection"
          width="50"
          :reserve-selection="true"
        />
        <el-table-column prop="spider_name" label="爬虫名称" width="200" />
        <el-table-column prop="platform" label="平台" width="120" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.success ? 'success' : 'danger'" size="small">
              {{ row.success ? "成功" : "失败" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration_seconds" label="耗时" width="100">
          <template #default="{ row }">
            {{ row.duration_seconds.toFixed(2) }}s
          </template>
        </el-table-column>
        <el-table-column prop="started_at" label="开始时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.started_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误信息" min-width="200">
          <template #default="{ row }">
            <span v-if="!row.success" class="error-message">{{
              row.error_message
            }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              link
              size="small"
              @click="handleViewDetail(row)"
            >
              详情
            </el-button>
            <el-divider direction="vertical" />
            <el-button
              type="danger"
              link
              size="small"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.page_size"
          :page-sizes="[10, 20, 50, 100]"
          :total="totalRecords"
          layout="total, sizes, prev, pager, next, jumper"
          @update:page-size="handleSizeChange"
          @update:current-page="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="调用详情" width="700px">
      <div v-if="currentRecord" class="detail-content">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="爬虫名称">
            {{ currentRecord.spider_name }}
          </el-descriptions-item>
          <el-descriptions-item label="平台">
            {{ currentRecord.platform }}
          </el-descriptions-item>
          <el-descriptions-item label="版本">
            {{ currentRecord.spider_version }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="currentRecord.success ? 'success' : 'danger'">
              {{ currentRecord.success ? "成功" : "失败" }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">
            {{ formatDateTime(currentRecord.started_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="完成时间">
            {{
              currentRecord.completed_at
                ? formatDateTime(currentRecord.completed_at)
                : "-"
            }}
          </el-descriptions-item>
          <el-descriptions-item label="执行时长">
            {{ currentRecord.duration_seconds.toFixed(2) }} 秒
          </el-descriptions-item>
          <el-descriptions-item label="错误信息" v-if="!currentRecord.success">
            {{ currentRecord.error_message }}
          </el-descriptions-item>
        </el-descriptions>

        <el-divider>参数</el-divider>
        <pre v-if="currentRecord.params" class="json-content">{{
          formatJson(currentRecord.params)
        }}</pre>
        <div v-else class="text-muted">无参数</div>

        <el-divider>元数据</el-divider>
        <pre v-if="currentRecord.metadata" class="json-content">{{
          formatJson(currentRecord.metadata)
        }}</pre>
        <div v-else class="text-muted">无元数据</div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { ElMessageBox, ElMessage } from "element-plus";
import { useSpiderAuditStore } from "@/stores/spider_audit";
import type { SpiderAuditRecord } from "@/api/types";
import {
  DataLine,
  FolderOpened,
  TrendCharts,
  PieChart,
  Trophy,
  Warning,
  Refresh,
  Delete,
} from "@element-plus/icons-vue";

const auditStore = useSpiderAuditStore();

const stats = computed(() => auditStore.stats);
const records = computed(() => auditStore.records);
const totalRecords = computed(() => auditStore.totalRecords);
const platforms = computed(() => auditStore.platforms);
const spiders = computed(() => auditStore.spiders);
const loading = computed(() => auditStore.loading);
const queryParams = ref(auditStore.queryParams);

const dateRange = ref<[string, string] | null>(null);
const detailDialogVisible = ref(false);
const currentRecord = ref<SpiderAuditRecord | null>(null);

// 表格多选状态
const tableRef = ref();
const selectedRecords = ref<SpiderAuditRecord[]>([]);

// 当记录列表变化时清空选择
watch(records, () => {
  selectedRecords.value = [];
  tableRef.value?.clearSelection();
});

// 爬虫筛选输入关键字
const spiderSearchKeyword = ref("");
const filteredSpiderOptions = computed(() => {
  const keyword = spiderSearchKeyword.value.trim().toLowerCase();
  if (!keyword) return spiders.value;
  return spiders.value.filter((s) => s.toLowerCase().includes(keyword));
});

let timer: number | null = null;

// 格式化日期时间
const formatDateTime = (isoString: string) => {
  const date = new Date(isoString);
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
};

// 格式化 JSON
const formatJson = (jsonString: string) => {
  try {
    return JSON.stringify(JSON.parse(jsonString), null, 2);
  } catch {
    return jsonString;
  }
};

// 获取平台百分比
const getPlatformPercentage = (count: number) => {
  if (!stats.value || stats.value.today_count === 0) return 0;
  return Math.round((count / stats.value.today_count) * 100);
};

// 获取小时柱状图宽度
const getHourlyBarWidth = (count: number, allStats: any[]) => {
  const maxCount = Math.max(...allStats.map((s) => s.count));
  if (maxCount === 0) return 0;
  return Math.max((count / maxCount) * 100, 5); // 最小5%宽度
};

// 获取排行样式
const getRankingClass = (index: number) => {
  if (index === 0) return "gold";
  if (index === 1) return "silver";
  if (index === 2) return "bronze";
  return "";
};

// 加载数据
const loadData = async () => {
  await auditStore.refresh();
};

// 加载筛选选项
const loadFilters = async () => {
  await Promise.all([
    auditStore.fetchPlatforms(),
    auditStore.fetchSpiders(queryParams.value.platform),
  ]);
};

// 平台变化
const handlePlatformChange = async () => {
  queryParams.value.spider_name = undefined;
  spiderSearchKeyword.value = "";
  await auditStore.fetchSpiders(queryParams.value.platform);
  await auditStore.fetchRecords();
};

// 日期范围变化
const handleDateRangeChange = async () => {
  if (dateRange.value) {
    queryParams.value.start_date = dateRange.value[0];
    queryParams.value.end_date = dateRange.value[1];
  } else {
    queryParams.value.start_date = undefined;
    queryParams.value.end_date = undefined;
  }
  await auditStore.fetchRecords();
};

// 重置
const handleReset = async () => {
  dateRange.value = null;
  spiderSearchKeyword.value = "";
  auditStore.resetQueryParams();
  await auditStore.fetchRecords();
};

// 刷新
const handleRefresh = async () => {
  await loadData();
};

// 分页变化 - v-model 已自动更新值
const handlePageChange = async () => {
  await auditStore.fetchRecords();
};

const handleSizeChange = async () => {
  // 改变每页数量时需要重置到第一页
  queryParams.value.page = 1;
  await auditStore.fetchRecords();
};

// 爬虫筛选输入过滤
const filterSpiders = (keyword: string) => {
  spiderSearchKeyword.value = keyword;
};

// 表格选择变化
const handleSelectionChange = (rows: SpiderAuditRecord[]) => {
  selectedRecords.value = rows;
};

// 取消选择
const handleClearSelection = () => {
  tableRef.value?.clearSelection();
  selectedRecords.value = [];
};

// 批量删除
const handleBatchDelete = async () => {
  const count = selectedRecords.value.length;
  if (count === 0) return;

  await ElMessageBox.confirm(
    `确定要删除选中的 ${count} 条审计记录吗？此操作不可恢复。`,
    "批量删除确认",
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    },
  );

  try {
    const ids = selectedRecords.value.map((r) => r.id);
    const deletedCount = await auditStore.deleteRecordsBatch(ids);
    ElMessage.success(`已删除 ${deletedCount} 条记录`);
    handleClearSelection();
  } catch (err: any) {
    if (err !== "cancel") {
      console.error("Batch delete error:", err);
    }
  }
};

// 查看详情
const handleViewDetail = (record: SpiderAuditRecord) => {
  currentRecord.value = record;
  detailDialogVisible.value = true;
};

// 删除记录
const handleDelete = async (record: SpiderAuditRecord) => {
  await ElMessageBox.confirm(`确定要删除这条审计记录吗？`, "删除确认", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  });

  try {
    await auditStore.deleteRecord(record.id);
    ElMessage.success("删除成功");
  } catch (err: any) {
    // 用户取消或删除失败，不显示错误（已通过拦截器处理）
    if (err !== "cancel") {
      console.error("Delete error:", err);
    }
  }
};

// 清理旧记录
const handleCleanup = async () => {
  const { value } = await ElMessageBox.prompt(
    "请输入要保留的天数（将删除此天数之前的记录）",
    "清理审计记录",
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      inputValue: "30",
      inputPattern: /^\d+$/,
      inputErrorMessage: "请输入有效的天数",
      inputPlaceholder: "30",
    },
  );

  const days = parseInt(value, 10);
  if (days < 1 || days > 365) {
    ElMessage.warning("天数必须在 1-365 之间");
    return;
  }

  await ElMessageBox.confirm(
    `确定要删除 ${days} 天之前的所有审计记录吗？此操作不可恢复。`,
    "清理确认",
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    },
  );

  try {
    const count = await auditStore.cleanupOldRecords(days);
    ElMessage.success(`已清理 ${count} 条记录`);
  } catch (err: any) {
    if (err !== "cancel") {
      console.error("Cleanup error:", err);
    }
  }
};

onMounted(async () => {
  await Promise.all([loadData(), loadFilters()]);
  // 定时刷新（每30秒）
  timer = window.setInterval(loadData, 30000);
});

onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>

<style scoped lang="scss">
.spider-audit-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 500;
  }

  .stats-content {
    .stat-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 0;
      border-bottom: 1px solid #f0f0f0;

      &:last-child {
        border-bottom: none;
      }

      .label {
        color: #909399;
        font-size: 14px;
      }

      .value {
        font-size: 18px;
        font-weight: 500;
        color: #303133;

        &.success {
          color: #67c23a;
        }

        &.warning {
          color: #f56c6c;
        }
      }
    }
  }

  // 小时趋势图
  .hourly-chart {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: 150px;
    overflow-y: auto;

    .hourly-bar-container {
      display: flex;
      align-items: center;
      gap: 8px;

      .hourly-label {
        width: 45px;
        font-size: 12px;
        color: #909399;
        text-align: right;
      }

      .hourly-bar-wrapper {
        flex: 1;
        height: 16px;
        background: #f5f7fa;
        border-radius: 4px;
        overflow: hidden;
        display: flex;
        position: relative;

        .hourly-bar {
          height: 100%;
          position: absolute;
          left: 0;

          &.success {
            background: linear-gradient(to right, #67c23a, #85ce61);
            z-index: 2;
            opacity: 0.8;
          }

          &.failure {
            background: linear-gradient(to right, #f56c6c, #f78989);
            z-index: 1;
          }
        }
      }

      .hourly-count {
        width: 30px;
        font-size: 12px;
        color: #303133;
        text-align: center;
      }
    }
  }

  // 平台统计
  .platform-stats {
    max-height: 380px;
    overflow-y: auto;
    padding-right: 4px;

    // 滚动条样式
    &::-webkit-scrollbar {
      width: 6px;
    }

    &::-webkit-scrollbar-thumb {
      background: #dcdfe6;
      border-radius: 3px;

      &:hover {
        background: #c0c4cc;
      }
    }

    .platform-item {
      margin-bottom: 16px;

      &:last-child {
        margin-bottom: 0;
      }

      .platform-info {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
        font-size: 14px;

        .platform-name {
          font-weight: 500;
        }

        .platform-count {
          color: #909399;
        }
      }
    }
  }

  // 爬虫排行
  .spider-ranking {
    max-height: 380px;
    overflow-y: auto;
    padding-right: 4px;

    // 滚动条样式
    &::-webkit-scrollbar {
      width: 6px;
    }

    &::-webkit-scrollbar-thumb {
      background: #dcdfe6;
      border-radius: 3px;

      &:hover {
        background: #c0c4cc;
      }
    }

    .spider-ranking-item {
      display: flex;
      align-items: center;
      padding: 10px 0;
      border-bottom: 1px solid #f0f0f0;

      &:last-child {
        border-bottom: none;
      }

      .ranking-number {
        width: 28px;
        height: 28px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 500;
        margin-right: 12px;
        background: #f5f7fa;
        color: #909399;

        &.gold {
          background: linear-gradient(135deg, #ffd666, #ffa940);
          color: #fff;
        }

        &.silver {
          background: linear-gradient(135deg, #d9d9d9, #bfbfbf);
          color: #fff;
        }

        &.bronze {
          background: linear-gradient(135deg, #ffa940, #d46b08);
          color: #fff;
        }
      }

      .ranking-info {
        flex: 1;

        .spider-name {
          font-weight: 500;
          font-size: 14px;
          margin-bottom: 4px;
        }

        .spider-count {
          font-size: 12px;
          color: #909399;
        }
      }
    }
  }

  // 最近失败
  .recent-failures {
    max-height: 380px;
    overflow-y: auto;
    padding-right: 4px;

    // 滚动条样式
    &::-webkit-scrollbar {
      width: 6px;
    }

    &::-webkit-scrollbar-thumb {
      background: #dcdfe6;
      border-radius: 3px;

      &:hover {
        background: #c0c4cc;
      }
    }

    .failure-item {
      padding: 10px;
      margin-bottom: 10px;
      background: #fef0f0;
      border-radius: 4px;
      border-left: 3px solid #f56c6c;

      &:last-child {
        margin-bottom: 0;
      }

      .failure-spider {
        font-weight: 500;
        font-size: 14px;
        color: #303133;
        margin-bottom: 4px;
      }

      .failure-error {
        font-size: 12px;
        color: #f56c6c;
        margin-bottom: 4px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .failure-time {
        font-size: 12px;
        color: #909399;
      }
    }
  }

  .no-data {
    text-align: center;
    color: #909399;
    padding: 20px;
  }

  .mt-20 {
    margin-top: 20px;
  }

  .table-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 500;

    .header-actions {
      display: flex;
      gap: 10px;
    }
  }

  .filter-section {
    margin-bottom: 20px;
  }

  .error-message {
    color: #f56c6c;
    font-size: 13px;
  }

  .text-muted {
    color: #909399;
  }

  .pagination-wrapper {
    display: flex;
    justify-content: flex-end;
    margin-top: 20px;
  }

  .detail-content {
    .json-content {
      background: #f5f7fa;
      padding: 12px;
      border-radius: 4px;
      font-size: 13px;
      line-height: 1.6;
      max-height: 300px;
      overflow: auto;
    }
  }
}
</style>
