"""
自动扫描 data_sources/ 目录，生成数据源接口文档
"""

import ast
from ruamel.yaml import YAML
from pathlib import Path
from typing import Any, Dict, List, Optional


class SpiderInfoExtractor(ast.NodeVisitor):
    def __init__(self):
        self.class_name: Optional[str] = None
        self.class_attributes: Dict[str, Any] = {}
        self.params_model: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        has_base = any((isinstance(b, ast.Name) and b.id == "BaseWebSpider") for b in node.bases)
        if has_base:
            self.class_name = node.name
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            if isinstance(item.value, ast.Constant):
                                self.class_attributes[target.id] = item.value.value
                            elif isinstance(item.value, ast.Name) and target.id == "params_model":
                                self.params_model = item.value.id
        self.generic_visit(node)


def extract_params(node: ast.ClassDef) -> List[Dict[str, Any]]:
    params = []
    for item in node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            ptype = "string"
            try:
                ptype = ast.unparse(item.annotation) if item.annotation else "string"
            except:
                pass
            desc, default, req = "", None, True
            if isinstance(item.value, ast.Call):
                for kw in item.value.keywords:
                    if kw.arg == "description" and isinstance(kw.value, ast.Constant):
                        desc = kw.value.value
                    elif kw.arg == "default" and isinstance(kw.value, ast.Constant):
                        default, req = kw.value.value, False
            elif item.value and isinstance(item.value, ast.Constant):
                default, req = item.value.value, False
            params.append(
                {
                    "name": item.target.id,
                    "type": ptype,
                    "description": desc,
                    "default": default,
                    "required": req,
                }
            )
    return params


def extract_spider_info(fp: Path) -> Optional[Dict[str, Any]]:
    try:
        tree = ast.parse(fp.read_text(encoding="utf-8"))
        ext = SpiderInfoExtractor()
        ext.visit(tree)
        if not ext.class_name:
            return None
        params = []
        if ext.params_model:
            for n in ast.walk(tree):
                if isinstance(n, ast.ClassDef) and n.name == ext.params_model:
                    params = extract_params(n)
                    break
        return {
            "name": ext.class_attributes.get("name", ""),
            "description": ext.class_attributes.get("description", ""),
            "author": ext.class_attributes.get("author", ""),
            "version": ext.class_attributes.get("version", ""),
            "platform": ext.class_attributes.get("platform", ""),
            "params": params,
        }
    except Exception as e:
        print(f"Error: {fp} - {e}")
        return None


def render_spider_doc(si: Dict, pn: str) -> str:
    pt = ""
    if si["params"]:
        rows = []
        for p in si["params"]:
            req = "✓" if p["required"] else "✗"
            default_val = f"`{p['default']}`" if p["default"] is not None else "-"
            rows.append(
                f"| `{p['name']}` | `{p['type']}` | {req} | {default_val} | {p['description']} |"
            )
        pt = "\n".join(
            [
                "| 参数名 | 类型 | 必填 | 默认值 | 说明 |",
                "| :--- | :--- | :---: | :--- | :--- |",
                *rows,
            ]
        )
    else:
        pt = "该接口无需参数。"
    ep_bash = ',\n    "params": { ... }' if si["params"] else ""
    ep_python = ',\n            "params": { ... }' if si["params"] else ""
    return f"""# {si['description']}

## 基本信息

| 项目 | 值 |
| :--- | :--- |
| **爬虫名称** | `{si['name']}` |
| **平台** | {pn} |
| **版本** | {si['version']} |
| **作者** | {si['author']} |

## 请求参数

{pt}

## 使用示例

### API 调用

```bash
curl -X POST http://localhost:8380/api/v1/spiders/run \
  -H "Content-Type: application/json" \
  -d '{{
    "spider_name": "{si['name']}"{ep_bash}
  }}'
```

### Python SDK

```python
import httpx

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8380/api/v1/spiders/run",
        json={{
            "spider_name": "{si['name']}"{ep_python}
        }}
    )
    result = resp.json()
```

## 返回格式

```json
{{
  "success": true,
  "message": "执行成功",
  "data": {{ ... }},
  "execution_time": 1.23
}}
```
"""


def gen_platform_index(pdn: str, pn: str, spiders: List) -> str:
    rows = [
        f"| [{s['description']}]({s['name']}.md) | `{s['name']}` | {s['version']} |"
        for s in spiders
    ]
    table = "\n".join(["| 接口说明 | 爬虫名称 | 版本 |", "| :--- | :--- | :---: |", *rows])
    return f"""# {pn}

## 概览

| 统计项 | 数值 |
| :--- | :--- |
| **平台标识** | `{pdn}` |
| **接口数量** | {len(spiders)} |

## 接口列表

{table}

## 使用说明

所有接口均通过统一的 API 端点调用：

```bash
POST http://localhost:8380/api/v1/spiders/run
```
"""


def gen_main_index(stats: Dict) -> str:
    total_p = len(stats)
    total_s = sum(s["spider_count"] for s in stats.values())
    rows = [
        f"| [{s['display_name']}]({pd}/index.md) | {s['spider_count']} | `{pd}` |"
        for pd, s in sorted(stats.items())
    ]
    table = "\n".join(["| 平台 | 接口数 | 标识 |", "| :--- | :---: | :--- |", *rows])
    return f"""# 数据源

## 统计概览

| 统计项 | 数值 |
| :--- | :--- |
| **支持平台数** | {total_p} |
| **总接口数** | {total_s} |

## 平台列表

{table}

## 使用方式

### 通过 API

```bash
curl http://localhost:8380/api/v1/spiders
curl -X POST http://localhost:8380/api/v1/spiders/run -H "Content-Type: application/json" -d '{{"spider_name": "xxx"}}'
```

### 通过 MCP

创建 MCP 服务后，所有爬虫自动暴露为 MCP 工具。
"""


def update_mkdocs_nav(platform_stats: Dict[str, Dict[str, Any]], root: Path):
    """更新 mkdocs.yml 中的数据源导航配置（保留注释和格式）"""
    mkdocs_path = root / "mkdocs.yml"

    if not mkdocs_path.exists():
        print("⚠ mkdocs.yml 不存在，跳过导航更新")
        return

    # 使用 ruamel.yaml 保留注释和格式
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    yaml.width = 4096  # 避免自动换行
    yaml.indent(mapping=2, sequence=4, offset=2)  # mapping=2, sequence=4 匹配原始格式

    try:
        with open(mkdocs_path, "r", encoding="utf-8") as f:
            config = yaml.load(f)
    except Exception as e:
        print(f"⚠ 解析 mkdocs.yml 失败: {e}")
        return

    if "nav" not in config:
        print("⚠ mkdocs.yml 中未找到 nav 配置")
        return

    # 查找数据源部分
    datasources_index = -1
    for i, item in enumerate(config["nav"]):
        if isinstance(item, dict) and "数据源" in item:
            datasources_index = i
            break

    if datasources_index == -1:
        print("⚠ 未找到数据源导航配置")
        return

    # 构建新的数据源导航列表
    new_datasources_nav = yaml.seq()
    new_datasources_nav.append("datasources/index.md")

    # 按平台名称排序添加
    for platform_dir, stats in sorted(platform_stats.items()):
        display_name = stats["display_name"]
        item = yaml.map()
        item[display_name] = f"datasources/{platform_dir}/index.md"
        new_datasources_nav.append(item)

    # 更新配置
    config["nav"][datasources_index]["数据源"] = new_datasources_nav

    # 写回文件，保持原有格式和注释
    try:
        with open(mkdocs_path, "w", encoding="utf-8", newline="\n") as f:
            yaml.dump(config, f)
        print(f"✓ {mkdocs_path.relative_to(root)} (已更新数据源导航)")
    except Exception as e:
        print(f"⚠ 写入 mkdocs.yml 失败: {e}")


def generate_all_datasource_docs():
    root = Path(__file__).parent.parent
    ds_dir = root / "omnidata" / "data_sources"
    docs_dir = root / "docs" / "datasources"
    stats, total = {}, 0

    for pd in sorted(ds_dir.iterdir()):
        if not pd.is_dir() or pd.name.startswith("_"):
            continue

        pname = pd.name
        pdocs = docs_dir / pname
        pdocs.mkdir(parents=True, exist_ok=True)
        spiders = []

        for pf in sorted(pd.glob("*.py")):
            if pf.name.startswith("_") or pf.name == "login.py":
                continue
            si = extract_spider_info(pf)
            if si and si["name"]:
                spiders.append(si)
                dp = pdocs / f"{si['name']}.md"
                dp.write_text(
                    render_spider_doc(si, si.get("platform", pname)), encoding="utf-8", newline="\n"
                )
                total += 1
                print(f"✓ {dp.relative_to(root)}")

        if spiders:
            dn = spiders[0].get("platform", pname)
            ip = pdocs / "index.md"
            ip.write_text(gen_platform_index(pname, dn, spiders), encoding="utf-8", newline="\n")
            print(f"✓ {ip.relative_to(root)}")
            stats[pname] = {"display_name": dn, "spider_count": len(spiders)}

    mi = docs_dir / "index.md"
    mi.write_text(gen_main_index(stats), encoding="utf-8", newline="\n")
    print(f"✓ {mi.relative_to(root)}")

    # 更新 mkdocs.yml 导航配置
    update_mkdocs_nav(stats, root)

    print(f"\n✓ 共生成 {total} 个爬虫文档，覆盖 {len(stats)} 个平台")


if __name__ == "__main__":
    generate_all_datasource_docs()
