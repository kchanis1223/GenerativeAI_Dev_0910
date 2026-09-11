"""Compare the checked-in design contract and DOCX tables with the running interfaces."""

import ast
import json
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))

from badaro.runtime.contracts import AgentReply, DispatchMap, RequestDraft  # noqa: E402
from badaro.runtime.tools import TOOLS  # noqa: E402
from badaro.schemas import DispatchConstraints, DispatchRequest, DispatchResult  # noqa: E402


def contract():
    tree = ast.parse((ROOT / "agent/badaro/runtime/graph.py").read_text())
    middleware = next(
        [item.id for item in node.value.elts]
        for node in ast.walk(tree)
        if isinstance(node, ast.keyword) and node.arg == "middleware"
    )
    return {
        "tools": {t.name: list(t.tool_call_schema.model_json_schema()["properties"]) for t in TOOLS},
        "middleware": middleware,
        "models": {
            cls.__name__: list(cls.model_fields)
            for cls in (RequestDraft, DispatchRequest, DispatchConstraints, DispatchResult,
                        AgentReply, DispatchMap)
        },
    }


def doc_tables():
    with ZipFile(ROOT / "docs/6반_3조_설계서_v2.docx") as archive:
        xml = ET.fromstring(archive.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    return [
        [["".join(c.itertext()) for c in row.findall("w:tc", ns)]
         for row in table.findall("w:tr", ns)]
        for table in xml.findall("w:body/w:tbl", ns)
    ]


def main():
    current = contract()
    path = ROOT / "docs/runtime-contract.json"
    if "--write" in sys.argv:
        path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n")
        return
    assert json.loads(path.read_text()) == current, "runtime-contract.json is stale"
    tables = doc_tables()
    tools = next(t for t in tables if t[0][0] == "Tool")
    documented = {row[0]: [s.strip() for s in row[2].split(",")] for row in tools[1:]}
    assert documented == current["tools"], "DOCX Tool names or arguments differ"
    middleware = next(t for t in tables if t[0][0] == "Middleware")
    assert [r[0] for r in middleware[1:]] == current["middleware"], "DOCX middleware differs"
    fields = next(t for t in tables if t[0][:2] == ["모델", "필드"])
    documented_models = {}
    model = None
    for row in fields[1:]:
        model = row[0] or model
        documented_models.setdefault(model, []).append(row[1])
    for name in ("DispatchRequest", "DispatchResult"):
        assert documented_models[name] == current["models"][name], f"DOCX {name} differs"
    print("Design contract OK: 4 Tools, 6 middleware, request/result fields")


if __name__ == "__main__":
    main()
