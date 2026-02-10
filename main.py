"""
OmniData 主入口模块

运行方式:
    python main.py              # 启动 API 服务
    python main.py --list       # 列出所有爬虫
"""
import argparse
import asyncio
import logging
from dotenv import load_dotenv
load_dotenv()
# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


async def list_spiders():
    """列出所有爬虫"""
    from omnidata.core.spider_register import get_spider_register
    register =  get_spider_register()

    spiders = register.list_spider_info()

    print("\n=== Registered Spiders ===")
    print(f"Total: {len(spiders)} spiders\n")

    for spider in spiders:
        print(f"Name: {spider['name']}")
        print(f"  Description: {spider.get('description', 'N/A')}")
        print(f"  Version: {spider.get('version', 'N/A')}")
        print(f"  Author: {spider.get('author', 'N/A')}")
        print(f"  Enabled: {spider.get('enabled', True)}")
        print()

    await register.shutdown()


async def run_spider(name: str, params: dict | str):
    """运行指定爬虫"""
    import json
    from omnidata.core.spider_register import get_spider_register
    register = get_spider_register()

    # 如果参数是 JSON 字符串，解析为字典
    if isinstance(params, str):
        params = json.loads(params)

    logger.info(f"Running spider: {name}")
    result = await register.run_spider(name, params)

    print("\n=== Spider Result ===")
    print(f"Spider: {result.spider_name}")
    print(f"Success: {result.success}")
    print(f"Duration: {result.duration_seconds:.2f}s")

    if result.success:
        import json
        print(f"Data: {json.dumps(result.data, ensure_ascii=False, indent=2)}")
    else:
        print(f"Error: {result.message}")

    await register.shutdown()


async def main_async(args):
    """异步主函数"""
    from omnidata.core.browser_context_pool import get_browser_context_pool
    from omnidata.core.spider_register import get_spider_register, close_spider_register
    from omnidata.utils.redis_client import init_redis
    # 初始化 Redis 客户端
    await init_redis()

    # 使用 LRU 单例模式获取实例
    browser_pool = get_browser_context_pool()
    await browser_pool.initialize()

    register = get_spider_register()
    await register.initialize()

    if args.list:
        await list_spiders()
    elif args.run:
        params = args.params if args.params else {}
        await run_spider(args.run, params)

    # 清理
    await close_spider_register()
    await browser_pool.shutdown()


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(description="OmniData Web Scraping Framework")

    parser.add_argument("--host", help="API server host")
    parser.add_argument("--port", type=int, help="API server port")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--list", action="store_true", help="List all registered spiders")
    parser.add_argument("--run", metavar="NAME", help="Run a specific spider")
    parser.add_argument(
        "--params",
        help="Spider parameters as JSON string",
    )

    args = parser.parse_args()

    # 启动 API 服务时直接调用 uvicorn.run()，不使用 asyncio.run()
    if not args.list and not args.run:
        import uvicorn

        uvicorn.run(
            "omnidata.api.main:app",
            host=args.host or "0.0.0.0",
            port=args.port or 8380,
            reload=args.reload,
            log_level="info",
        )
        return

    # 其他模式使用 asyncio.run()
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
