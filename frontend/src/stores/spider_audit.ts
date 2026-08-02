import { defineStore } from "pinia";
import { ref } from "vue";
import * as api from "@/api/spider_audit";
import type {
  SpiderAuditRecord,
  SpiderAuditStats,
  SpiderAuditQuery,
} from "@/api/types";

export const useSpiderAuditStore = defineStore("spiderAudit", () => {
  // 状态
  const stats = ref<SpiderAuditStats | null>(null);
  const records = ref<SpiderAuditRecord[]>([]);
  const totalRecords = ref(0);
  const platforms = ref<string[]>([]);
  const spiders = ref<string[]>([]);
  const loading = ref<boolean>(false);

  // 查询参数
  const queryParams = ref<SpiderAuditQuery>({
    page: 1,
    page_size: 20,
  });

  // ========== 统计信息 ==========

  const fetchStats = async () => {
    try {
      loading.value = true;
      const response = await api.getAuditStats();
      stats.value = response.data;
      return stats.value;
    } catch (err: any) {
      console.error("Failed to fetch audit stats:", err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  // ========== 审计记录 ==========

  const fetchRecords = async () => {
    try {
      loading.value = true;
      const response = await api.getAuditRecords(queryParams.value);
      if (response.data) {
        records.value = response.data.items || [];
        totalRecords.value = response.data.count;
      }
      return response.data;
    } catch (err: any) {
      console.error("Failed to fetch audit records:", err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const setQueryParams = (params: Partial<SpiderAuditQuery>) => {
    queryParams.value = { ...queryParams.value, ...params };
    // 如果修改了筛选条件，重置到第一页
    if (
      params.spider_name !== undefined ||
      params.platform !== undefined ||
      params.success !== undefined ||
      params.start_date !== undefined ||
      params.end_date !== undefined
    ) {
      queryParams.value.page = 1;
    }
  };

  const resetQueryParams = () => {
    queryParams.value = {
      page: 1,
      page_size: 20,
    };
  };

  // ========== 平台和爬虫列表 ==========

  const fetchPlatforms = async () => {
    try {
      const response = await api.getAuditPlatforms();
      platforms.value = response.data || [];
      return platforms.value;
    } catch (err: any) {
      console.error("Failed to fetch platforms:", err);
      return [];
    }
  };

  const fetchSpiders = async (platform?: string) => {
    try {
      const response = await api.getAuditSpiders(platform);
      spiders.value = response.data || [];
      return spiders.value;
    } catch (err: any) {
      console.error("Failed to fetch spiders:", err);
      return [];
    }
  };

  // ========== 删除和清理 ==========

  // 删除后重新加载：删除当前页全部记录后页码可能越界（最后一页变空），
  // 需先回退到有效页码，再从服务端刷新统计与列表，确保表格始终填满有效数据
  const reloadAfterDelete = async () => {
    const pageSize = queryParams.value.page_size ?? 20;
    const maxPage = Math.max(1, Math.ceil(totalRecords.value / pageSize));
    if ((queryParams.value.page ?? 1) > maxPage) {
      queryParams.value.page = maxPage;
    }
    await Promise.all([fetchStats(), fetchRecords()]);
  };

  const deleteRecord = async (recordId: number) => {
    try {
      loading.value = true;
      await api.deleteAuditRecord(recordId);
      totalRecords.value = Math.max(0, totalRecords.value - 1);
      await reloadAfterDelete();
      return true;
    } catch (err: any) {
      console.error("Failed to delete audit record:", err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const deleteRecordsBatch = async (recordIds: number[]) => {
    try {
      loading.value = true;
      const response = await api.deleteAuditRecordsBatch(recordIds);
      const deletedCount = response.data?.count || 0;
      totalRecords.value = Math.max(0, totalRecords.value - deletedCount);
      await reloadAfterDelete();
      return deletedCount;
    } catch (err: any) {
      console.error("Failed to batch delete audit records:", err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const cleanupOldRecords = async (days: number = 30) => {
    try {
      loading.value = true;
      const response = await api.cleanupAuditRecords(days);
      // 刷新数据
      await Promise.all([fetchStats(), fetchRecords()]);
      return response.data?.count || 0;
    } catch (err: any) {
      console.error("Failed to cleanup audit records:", err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const refresh = async () => {
    await Promise.all([fetchStats(), fetchRecords()]);
  };

  return {
    // 状态
    stats,
    records,
    totalRecords,
    platforms,
    spiders,
    loading,
    queryParams,

    // 方法
    fetchStats,
    fetchRecords,
    setQueryParams,
    resetQueryParams,
    fetchPlatforms,
    fetchSpiders,
    refresh,
    deleteRecord,
    deleteRecordsBatch,
    cleanupOldRecords,
  };
});
