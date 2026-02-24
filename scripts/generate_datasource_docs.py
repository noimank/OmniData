"""
自动扫描 data_sources/ 目录，生成数据源接口文档

使用方法：
    uv run python scripts/generate_datasource_docs.py
"""

import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_platform_display_name(platform_dir: str) -> str:
    """获取平台中文名称"""
    platform_names = {
        "21jingji": "21财经",
        "bilibili": "Bilibili",
        "cls": "财联社",
        "eastmoney": "东方财富",
        "futunn": "富途牛牛",
        "hexun": "和讯网",
        "jrj": "金融界",
        "sina": "新浪财经",
        "ths_10jqka": "同花顺",
        "ths_iwencai": "同花顺问财",
        "wallstreetcn": "华尔街见闻",
        "yicai": "第一财经",
    }
    return platform_names.get(platform_dir, platform_dir)


class SpiderInfoExtractor(ast.NodeVisitor):
    """从 Python 代码中提取爬虫信息"""

    def __init__(self):
        self.class_name: Optional[str] = None
        self.bases: List[str] = []
        self.class_attributes: Dict[str, Any] = {}
        self.params_model: Optional[str] = None
        self.imports: Dict[str, str] = {}  # name -> module

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports[alias.asname or alias.name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            for alias in node.names:
                self.imports[alias.asname or alias.name] = f"{node.module}.{alias.name}"
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # 只处理直接继承 BaseWebSpider 的类
        has_base_web_spider = any(
            (isinstance(base, ast.Name) and base.id == "BaseWebSpider") or
            (isinstance(base, ast.Attribute) and base.attr == "BaseWebSpider")
            for base in node.bases
        )

        if has_base_web_spider:
            self.class_name = node.name

            # 提取类属性
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            attr_name = target.id
                            if isinstance(item.value, ast.Constant):
                                self.class_attributes[attr_name] = item.value.value
                            elif isinstance(item.value, ast.Str):  # Python < 3.8
                                self.class_attributes[attr_name] = item.value.s
                            elif isinstance(item.value, ast.Name):
                                self.params_model = item.value.id

        self.generic_visit(node)


def extract_spider_info(file_path: Path) -> Optional[Dict[str, Any]]:
    """从爬虫文件中提取元数据"""
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)

        extractor = SpiderInfoExtractor()
        extractor.visit(tree)

        if not extractor.class_name:
            return None

        # 查找 params_model 类定义以提取参数信息
        params_info = []
        if extractor.params_model:
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == extractor.params_model:
                    params_info = extract_params_from_class(node)
                    break

        return {
            "class_name": extractor.class_name,
            "name": extractor.class_attributes.get("name", ""),
            "description": extractor.class_attributes.get("description", ""),
            "author": extractor.class_attributes.get("author", ""),
            "version": extractor.class_attributes.get("version", ""),
            "platform": extractor.class_attributes.get("platform", ""),
            "params_model": extractor.params_model,
            "params": params_info,
        }
    except Exception as e:
        print(f"解析文件 {file_path} 失败: {e}")
        return None


def extract_params_from_class(node: ast.ClassDef) -> List[Dict[str, Any]]:
    """从 Pydantic 模型类中提取参数信息"""
    params = []

    # 查找基类 BaseModel
    bases = [base.id if isinstance(base, ast.Name) else ""
             for base in node.bases if isinstance(base, ast.Name)]

    if "BaseModel" not in bases:
        return params

    # 提取类属性作为参数
    for item in node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            param_name = item.target.id

            # 尝试获取 Field 信息
            default_value = None
            description = ""
            required = True

            if isinstance(item.value, ast.Call):
                # 处理 Field(...) 调用
                for keyword in item.value.keywords:
                    if keyword.arg == "description" and isinstance(keyword.value, ast.Constant):
                        description = keyword.value.value
                    elif keyword.arg == "default" and isinstance(keyword.value, ast.Constant):
                        default_value = keyword.value.value
                        required = False

            params.append({
                "name": param_name,
                "description": description,
                "default": default_value,
                "required": required,
            })

    return params


def render_spider_doc(spider_info: Dict[str, Any], platform_name: str) -> str:
    """渲染单个爬虫文档"""

    # 生成标题（从 snake_case 转换为可读标题）
    name = spider_info["name"]
    title = name.replace("_", " ").title()

    # 生成参数表格
    params_table = ""
    if spider_info["params"]:
        params_rows = []
        for param in spider_info["params"]:
            req_mark = "✓" if param["required"] else "✗"
            default = f", 默认: `{param['default']}`" if param["default"] is not None else ""
            params_rows.append(
                f"| `{param['name']}` | string | {req_mark} | {param['description']}{default} |"
            )
        params_table = "\n".join(["| 参数 | 类型 | 必填 | 说明 |", "| :--- | :--- | :---: | :--- |", *params_rows])
    else:
        params_table = "该接口无需参数。"

    return f"""# {title}

!!! abstract "接口信息"
    - **爬虫名称**：`{spider_info['name']}`
    - **平台**：{platform_name}
    - **作者**：{spider_info['author']}
    - **版本**：{spider_info['version']}

## 功能说明

{spider_info['description']}

## 请求参数

{params_table}

## 返回结果

```json
{{
  "success": true,
  "data": {{ ... }}
}}
```

## 使用示例

```bash
curl -X POST http://localhost:8380/spiders/run \\
  -H "Content-Type: application/json" \\
  -d '{{
    "spider_name": "{spider_info['name']}"{',\n    "params": {{ ... }}' if spider_info['params'] else ''}
  }}'
```

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/spiders/run",
        json={{
            "spider_name": "{spider_info['name']}"{',\n            "params": {{ ... }}' if spider_info['params'] else ''}
        }}
    )
    result = resp.json()
```

## 注意事项

!!! tip "使用提示"
    具体使用方法请参考代码实现。

!!! warning "限制"
    请合理使用接口，避免频繁请求。
"""


def generate_all_datasource_docs():
    """生成所有数据源文档"""
    project_root = Path(__file__).parent.parent
    datasources_dir = project_root / "omnidata" / "data_sources"
    docs_dir = project_root / "docs" / "datasources"

    total_generated = 0

    for platform_dir in sorted(datasources_dir.iterdir()):
        if not platform_dir.is_dir() or platform_dir.name.startswith("_"):
            continue

        platform_name = get_platform_display_name(platform_dir.name)
        platform_docs_dir = docs_dir / platform_dir.name
        platform_docs_dir.mkdir(parents=True, exist_ok=True)

        spiders = []

        # 扫描平台目录下的所有 Python 文件
        for py_file in sorted(platform_dir.glob("*.py")):
            if py_file.name.startswith("_") or py_file.name == "login.py":
                continue

            spider_info = extract_spider_info(py_file)
            if spider_info and spider_info["name"]:
                spiders.append(spider_info)

                # 生成单个爬虫文档
                doc_filename = f"{spider_info['name']}.md"
                doc_path = platform_docs_dir / doc_filename

                content = render_spider_doc(spider_info, platform_name)
                doc_path.write_text(content, encoding="utf-8")
                total_generated += 1
                print(f"[OK] Generated: {doc_path}")

        # 更新平台索引文档（如果已存在则跳过，避免覆盖手动内容）
        index_path = platform_docs_dir / "index.md"
        if not index_path.exists():
            index_content = f"""# {platform_name}

{platform_name}数据接口。

!!! note "接口数量"
    当前共有 **{len(spiders)}** 个接口。

## 接口列表

"""
            for spider in spiders:
                doc_name = spider["name"]
                index_content += f"- [{spider['description']}]({doc_name}.md)\n"

            index_content += "\n---\n\n## 特点\n\n- ✅ 数据实时更新\n\n## 使用示例\n\n```bash\ncurl -X POST http://localhost:8380/spiders/run \\\n  -H \"Content-Type: application/json\" \\\n  -d '{{\n    \"spider_name\": \"{spiders[0]['name'] if spiders else ''}\",\n    \"params\": {{}}\n  }}'\n```"
            index_path.write_text(index_content, encoding="utf-8")
            print(f"[OK] Generated: {index_path}")

    print(f"\n[OK] Generated {total_generated} spider docs in total")


if __name__ == "__main__":
    generate_all_datasource_docs()
