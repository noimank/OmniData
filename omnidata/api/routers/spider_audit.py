"""
爬虫审计路由
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Body, Query
from sqlalchemy import and_, case, delete as sql_delete, func, select

from omnidata.api.responses import (
    error_response,
    paginated_success_response,
    success_response,
)
from omnidata.database import get_db_session
from omnidata.database.models import SpiderAudit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/spider-audit", tags=["spider-audit"])


@router.get("/stats")
async def get_audit_stats():
    """
    获取审计统计信息

    Returns:
        今日调用统计、平台分布、成功率、小时趋势、热门爬虫排行、最近失败记录
    """
    try:
        async with get_db_session() as session:
            now = datetime.now()
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday = today - timedelta(days=1)

            # ========== 基础统计 ==========

            # 今日统计
            today_result = await session.execute(
                select(
                    func.count(SpiderAudit.id).label("total"),
                    func.sum(case((SpiderAudit.success == True, 1), else_=0)).label(
                        "success_count"
                    ),
                ).where(SpiderAudit.started_at >= today)
            )
            today_row = today_result.one()
            today_count = today_row.total or 0
            today_success_count = today_row.success_count or 0
            today_failure_count = today_count - today_success_count

            # 总统计
            total_result = await session.execute(select(func.count(SpiderAudit.id)))
            total_count = total_result.scalar() or 0

            # 平台统计（今日）
            platform_result = await session.execute(
                select(
                    SpiderAudit.platform,
                    func.count(SpiderAudit.id).label("count"),
                    func.sum(case((SpiderAudit.success == True, 1), else_=0)).label(
                        "success_count"
                    ),
                )
                .where(SpiderAudit.started_at >= today)
                .group_by(SpiderAudit.platform)
                .order_by(func.count(SpiderAudit.id).desc())
            )
            platform_stats = []
            for row in platform_result:
                platform_stats.append(
                    {
                        "platform": row.platform,
                        "count": row.count,
                        "success_count": row.success_count or 0,
                        "failure_count": row.count - (row.success_count or 0),
                    }
                )

            # 最近7天成功率
            week_ago = now - timedelta(days=7)
            week_result = await session.execute(
                select(
                    func.count(SpiderAudit.id).label("total"),
                    func.sum(case((SpiderAudit.success == True, 1), else_=0)).label(
                        "success_count"
                    ),
                ).where(SpiderAudit.started_at >= week_ago)
            )
            week_row = week_result.one()
            week_total = week_row.total or 0
            week_success = week_row.success_count or 0
            recent_success_rate = (week_success / week_total * 100) if week_total > 0 else 0.0

            # ========== 扩展统计 ==========

            # 按小时统计趋势（最近24小时）：单次查询取出 24 小时窗口内的记录，
            # 在内存中按小时分桶，替代原先的 24 次逐小时查询（N+1）。
            # 分桶用 timedelta 整除，与原先逐小时 WHERE 的左闭右开边界完全一致。
            window_start = now - timedelta(hours=24)
            hourly_result = await session.execute(
                select(SpiderAudit.started_at, SpiderAudit.success).where(
                    and_(
                        SpiderAudit.started_at >= window_start,
                        SpiderAudit.started_at < now,
                    )
                )
            )
            hour_delta = timedelta(hours=1)
            hourly_counts = [0] * 24
            hourly_success = [0] * 24
            for started_at, success in hourly_result:
                slot = (started_at - window_start) // hour_delta
                hourly_counts[slot] += 1
                if success:
                    hourly_success[slot] += 1
            hourly_stats = []
            for slot in range(24):
                count = hourly_counts[slot]
                success_count = hourly_success[slot]
                hour_start = window_start + timedelta(hours=slot)
                hourly_stats.append(
                    {
                        "hour": hour_start.strftime("%H:00"),
                        "count": count,
                        "success_count": success_count,
                        "failure_count": count - success_count,
                    }
                )

            # 热门爬虫排行（今日 Top 10）
            spider_result = await session.execute(
                select(
                    SpiderAudit.spider_name,
                    func.count(SpiderAudit.id).label("count"),
                    func.sum(case((SpiderAudit.success == True, 1), else_=0)).label(
                        "success_count"
                    ),
                )
                .where(SpiderAudit.started_at >= today)
                .group_by(SpiderAudit.spider_name)
                .order_by(func.count(SpiderAudit.id).desc())
                .limit(10)
            )
            spider_ranking = []
            for row in spider_result:
                spider_ranking.append(
                    {
                        "spider_name": row.spider_name,
                        "count": row.count,
                        "success_count": row.success_count or 0,
                        "failure_count": row.count - (row.success_count or 0),
                    }
                )

            # 最近失败记录（最近10条）
            recent_failures_result = await session.execute(
                select(SpiderAudit)
                .where(SpiderAudit.success == False)
                .order_by(SpiderAudit.started_at.desc())
                .limit(10)
            )
            recent_failures = []
            for record in recent_failures_result.scalars().all():
                recent_failures.append(
                    {
                        "id": record.id,
                        "spider_name": record.spider_name,
                        "platform": record.platform,
                        "error_message": record.error_message,
                        "started_at": record.started_at.isoformat(),
                        "duration_seconds": record.duration_seconds,
                    }
                )

            return success_response(
                {
                    "today_count": today_count,
                    "today_success_count": today_success_count,
                    "today_failure_count": today_failure_count,
                    "total_count": total_count,
                    "platform_stats": platform_stats,
                    "recent_success_rate": round(recent_success_rate, 2),
                    "hourly_stats": hourly_stats,
                    "spider_ranking": spider_ranking,
                    "recent_failures": recent_failures,
                },
                "获取审计统计成功",
            )

    except Exception as e:
        logger.error(f"Error getting audit stats: {e}")
        return error_response(f"获取审计统计失败: {str(e)}")


@router.get("/records")
async def get_audit_records(
    spider_name: str | None = Query(None, description="爬虫名称"),
    platform: str | None = Query(None, description="平台名称"),
    success: bool | None = Query(None, description="执行状态"),
    start_date: str | None = Query(None, description="开始日期"),
    end_date: str | None = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """
    获取审计记录列表（分页）

    支持按爬虫名称、平台、状态、时间范围筛选
    """
    try:
        async with get_db_session() as session:
            # 构建查询条件
            conditions = []

            if spider_name:
                conditions.append(SpiderAudit.spider_name == spider_name)

            if platform:
                conditions.append(SpiderAudit.platform == platform)

            if success is not None:
                conditions.append(SpiderAudit.success == success)

            if start_date:
                try:
                    start_dt = datetime.fromisoformat(f"{start_date}T00:00:00")
                    conditions.append(SpiderAudit.started_at >= start_dt)
                except ValueError:
                    return error_response("开始日期格式错误")

            if end_date:
                try:
                    end_dt = datetime.fromisoformat(f"{end_date}T23:59:59")
                    conditions.append(SpiderAudit.started_at <= end_dt)
                except ValueError:
                    return error_response("结束日期格式错误")

            # 查询总数量
            count_query = select(func.count(SpiderAudit.id))
            if conditions:
                count_query = count_query.where(and_(*conditions))

            count_result = await session.execute(count_query)
            total_count = count_result.scalar() or 0

            # 查询记录（分页）
            query = select(SpiderAudit)
            if conditions:
                query = query.where(and_(*conditions))

            query = query.order_by(SpiderAudit.started_at.desc())
            query = query.offset((page - 1) * page_size).limit(page_size)

            result = await session.execute(query)
            records = result.scalars().all()

            # 转换为响应格式
            items = []
            for record in records:
                items.append(
                    {
                        "id": record.id,
                        "spider_name": record.spider_name,
                        "platform": record.platform,
                        "spider_version": record.spider_version,
                        "success": record.success,
                        "error_message": record.error_message,
                        "started_at": record.started_at.isoformat(),
                        "completed_at": (
                            record.completed_at.isoformat() if record.completed_at else None
                        ),
                        "duration_seconds": record.duration_seconds,
                        "params": record.params,
                        "metadata": record.result_metadata,
                        "created_at": record.created_at.isoformat(),
                    }
                )

            return paginated_success_response(items, total_count, "获取审计记录成功")

    except Exception as e:
        logger.error(f"Error getting audit records: {e}")
        return error_response(f"获取审计记录失败: {str(e)}")


@router.get("/platforms")
async def get_audit_platforms():
    """
    获取所有有审计记录的平台列表

    Returns:
        平台名称列表
    """
    try:
        async with get_db_session() as session:
            result = await session.execute(
                select(SpiderAudit.platform).distinct().order_by(SpiderAudit.platform)
            )
            platforms = [row[0] for row in result.all()]

            return success_response(platforms, "获取平台列表成功")

    except Exception as e:
        logger.error(f"Error getting platforms: {e}")
        return error_response(f"获取平台列表失败: {str(e)}")


@router.get("/spiders")
async def get_audit_spiders(platform: str | None = Query(None, description="平台名称")):
    """
    获取所有有审计记录的爬虫列表

    Args:
        platform: 可选，筛选指定平台的爬虫

    Returns:
        爬虫名称列表
    """
    try:
        async with get_db_session() as session:
            query = select(SpiderAudit.spider_name).distinct()

            if platform:
                query = query.where(SpiderAudit.platform == platform)

            query = query.order_by(SpiderAudit.spider_name)

            result = await session.execute(query)
            spiders = [row[0] for row in result.all()]

            return success_response(spiders, "获取爬虫列表成功")

    except Exception as e:
        logger.error(f"Error getting spiders: {e}")
        return error_response(f"获取爬虫列表失败: {str(e)}")


@router.delete("/cleanup")
async def cleanup_audit_records(
    days: int = Query(30, ge=1, le=365, description="保留最近多少天的记录")
):
    """
    清理指定天数之前的审计记录

    Args:
        days: 保留最近多少天的记录，默认30天

    Returns:
        删除的记录数量
    """
    try:
        async with get_db_session() as session:
            # 计算删除的截止时间
            cutoff_time = datetime.now() - timedelta(days=days)

            # 查询要删除的记录数量
            count_result = await session.execute(
                select(func.count(SpiderAudit.id)).where(SpiderAudit.created_at < cutoff_time)
            )
            count = count_result.scalar() or 0

            if count == 0:
                return success_response({"count": 0}, "没有需要清理的记录")

            # 执行删除
            await session.execute(
                sql_delete(SpiderAudit).where(SpiderAudit.created_at < cutoff_time)
            )

            return success_response({"count": count}, f"已清理 {count} 条记录")

    except Exception as e:
        logger.error(f"Error cleaning up audit records: {e}")
        return error_response(f"清理记录失败: {str(e)}")


@router.delete("/records/batch")
async def delete_audit_records_batch(ids: list[int] = Body(..., embed=True)):
    """
    批量删除审计记录

    Args:
        ids: 要删除的记录ID列表

    Returns:
        删除的记录数量
    """
    if not ids:
        return error_response("记录ID列表不能为空")

    try:
        async with get_db_session() as session:
            # 查询存在的记录数量
            count_result = await session.execute(
                select(func.count(SpiderAudit.id)).where(SpiderAudit.id.in_(ids))
            )
            count = count_result.scalar() or 0

            if count == 0:
                return success_response({"count": 0}, "没有需要删除的记录")

            # 执行批量删除
            await session.execute(sql_delete(SpiderAudit).where(SpiderAudit.id.in_(ids)))

            return success_response({"count": count}, f"已删除 {count} 条记录")

    except Exception as e:
        logger.error(f"Error batch deleting audit records: {e}")
        return error_response(f"批量删除记录失败: {str(e)}")


@router.delete("/records/{record_id}")
async def delete_audit_record(record_id: int):
    """
    删除单条审计记录

    Args:
        record_id: 记录ID

    Returns:
        删除结果
    """
    try:
        async with get_db_session() as session:
            # 查询记录
            record = await session.execute(select(SpiderAudit).where(SpiderAudit.id == record_id))
            record_obj = record.scalar_one_or_none()

            if not record_obj:
                return error_response(f"记录不存在: {record_id}")

            # 删除记录
            await session.delete(record_obj)

            return success_response({"id": record_id}, "删除成功")

    except Exception as e:
        logger.error(f"Error deleting audit record: {e}")
        return error_response(f"删除记录失败: {str(e)}")
