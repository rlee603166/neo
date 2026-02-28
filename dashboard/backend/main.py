import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATE_DIR = Path(__file__).parent / "state"


# ── Response models ────────────────────────────────────────────────────────────

class NodeSummary(BaseModel):
    node_id: str
    node_type: str
    state: str
    parent_id: str | None
    children_ids: list[str]
    working_directory: str


class TreeSummary(BaseModel):
    tree_id: str
    root_id: str
    nodes: dict[str, NodeSummary]


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_tree(tree_id: str) -> dict:
    path = STATE_DIR / f"{tree_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Tree '{tree_id}' not found")
    with open(path) as f:
        return json.load(f)


def summarize_node(node: dict) -> NodeSummary:
    return NodeSummary(
        node_id=node["node_id"],
        node_type=node["node_type"],
        state=node["state"],
        parent_id=node.get("parent_id"),
        children_ids=node.get("children_ids", []),
        working_directory=node.get("working_directory", "."),
    )


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/tree")
def list_trees() -> list[str]:
    return [p.stem for p in STATE_DIR.glob("*.json")]


@app.get("/tree/{tree_id}", response_model=TreeSummary)
def get_tree(tree_id: str):
    data = load_tree(tree_id)
    root = data["root"]
    all_nodes = {root["node_id"]: root, **data.get("nodes", {})}
    return TreeSummary(
        tree_id=tree_id,
        root_id=root["node_id"],
        nodes={node_id: summarize_node(node) for node_id, node in all_nodes.items()},
    )


@app.get("/tree/{tree_id}/{node_id}")
def get_node(tree_id: str, node_id: str):
    data = load_tree(tree_id)
    root = data["root"]
    all_nodes = {root["node_id"]: root, **data.get("nodes", {})}
    if node_id not in all_nodes:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found in tree '{tree_id}'")
    return all_nodes[node_id]


SPECIFIC_DIR = STATE_DIR / "specific"
SPECIFIC_DIR.mkdir(parents=True, exist_ok=True)


@app.post("/tree/{tree_id}/{node_id}/save")
def save_node(tree_id: str, node_id: str):
    data = load_tree(tree_id)
    root = data["root"]
    all_nodes = {root["node_id"]: root, **data.get("nodes", {})}
    if node_id not in all_nodes:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found in tree '{tree_id}'")
    out_path = SPECIFIC_DIR / f"{node_id}.json"
    with open(out_path, "w") as f:
        json.dump(all_nodes[node_id], f, indent=2)
    return {"saved": str(out_path)}
