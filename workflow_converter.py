"""Converts a ComfyUI *UI-format* workflow (the .json you save from the graph editor)
into the *API-format* prompt that ComfyUI's ``POST /prompt`` endpoint accepts.

Handles what the frontend normally does for us:
  * subgraphs (nested "group nodes") are flattened, ids become ``outer:inner``
  * bypassed nodes (mode 4) are replaced by a pass-through of the matching input type
  * muted nodes (mode 2) and frontend-only nodes (notes, ...) are dropped
  * widget values are read from ``widgets_values_named`` (written by the Plenio templates)
  * only nodes that are reachable from the requested output nodes are emitted
"""

from __future__ import annotations

import copy
import json
from typing import Any

FRONTEND_ONLY = {"MarkdownNote", "Note"}
CONTROL_VALUES = {"fixed", "randomize", "increment", "decrement"}
MODE_BYPASS = 4
MODE_MUTE = 2


class ConversionError(Exception):
    pass


def _norm_link(link: Any) -> dict:
    if isinstance(link, dict):
        return link
    # [id, origin_id, origin_slot, target_id, target_slot, type]
    return {
        "id": link[0],
        "origin_id": link[1],
        "origin_slot": link[2],
        "target_id": link[3],
        "target_slot": link[4],
        "type": link[5] if len(link) > 5 else None,
    }


class _Scope:
    def __init__(self, nodes, links, prefix="", subgraph=None, outer_node=None, outer_scope=None):
        self.nodes = {n["id"]: n for n in nodes}
        self.links = {}
        for raw in links:
            link = _norm_link(raw)
            self.links[link["id"]] = link
        self.prefix = prefix
        self.subgraph = subgraph
        self.outer_node = outer_node
        self.outer_scope = outer_scope


class WorkflowConverter:
    def __init__(self, workflow: dict):
        self.wf = copy.deepcopy(workflow)
        self.subgraphs = {s["id"]: s for s in self.wf.get("definitions", {}).get("subgraphs", [])}
        self.top = _Scope(self.wf["nodes"], self.wf.get("links", []))
        # per-conversion state
        self.api: dict[str, dict] = {}
        self.overrides: dict[str, dict] = {}
        self.modes: dict[int, int] = {}
        self.unlinks: dict[str, list[str]] = {}

    # ------------------------------------------------------------------ public

    def top_node(self, node_id: int) -> dict:
        return self.top.nodes[node_id]

    def widget_defaults(self, node_id: int) -> dict:
        node = self.top.nodes[node_id]
        return dict(node.get("widgets_values_named") or {})

    def convert(
        self,
        outputs: list[int],
        overrides: dict[int | str, dict] | None = None,
        modes: dict[int, int] | None = None,
        unlinks: dict[int | str, list[str]] | None = None,
        extra_sources: dict[str, tuple[int, int]] | None = None,
    ) -> dict:
        """Return an API prompt for the given top-level output node ids.

        ``extra_sources`` adds ``PreviewAny`` nodes: ``{api_id: (top_node_id, output_slot)}``.
        """
        self.api = {}
        self.overrides = {str(k): v for k, v in (overrides or {}).items()}
        self.modes = dict(modes or {})
        self.unlinks = {str(k): v for k, v in (unlinks or {}).items()}
        for node_id in outputs:
            if self._mode(self.top, self.top.nodes[node_id]) != 0:
                continue
            self._emit(self.top, self.top.nodes[node_id])
        for api_id, (node_id, slot) in (extra_sources or {}).items():
            src = self._resolve_output(self.top, node_id, slot)
            if src and src[0] == "link":
                self.api[api_id] = {"class_type": "PreviewAny", "inputs": {"source": [src[1], src[2]]}}
            elif src and src[0] == "value":
                raise ConversionError(f"output {node_id}:{slot} is a constant")
            else:
                raise ConversionError(f"output {node_id}:{slot} cannot be resolved")
        self._prune(
            [str(n) for n in outputs if str(n) in self.api] + list((extra_sources or {}).keys())
        )
        return self.api

    def _prune(self, roots: list[str]) -> None:
        """Drop nodes no output depends on (links may have been cut after emission)."""
        keep: set[str] = set()
        stack = list(roots)
        while stack:
            key = stack.pop()
            if key in keep or key not in self.api:
                continue
            keep.add(key)
            for value in self.api[key]["inputs"].values():
                if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
                    stack.append(value[0])
        self.api = {k: v for k, v in self.api.items() if k in keep}

    # ----------------------------------------------------------------- helpers

    def _mode(self, scope: _Scope, node: dict) -> int:
        if scope is self.top and node["id"] in self.modes:
            return self.modes[node["id"]]
        return node.get("mode", 0) or 0

    def _key(self, scope: _Scope, node: dict) -> str:
        return f"{scope.prefix}{node['id']}"

    def _input_source(self, scope: _Scope, node: dict, inp: dict):
        """Resolve one input of ``node``: ('link', api_id, slot) | ('value', v) | None."""
        link_id = inp.get("link")
        if link_id is not None:
            link = scope.links.get(link_id)
            if link is None:
                return None
            return self._resolve_output(scope, link["origin_id"], link["origin_slot"])
        if "widget" in inp:
            named = node.get("widgets_values_named") or {}
            value = named.get(inp["name"])
            if value is not None:
                return ("value", value)
        return None

    def _resolve_subgraph_input(self, scope: _Scope, slot: int):
        sg_inputs = scope.subgraph["inputs"]
        if slot >= len(sg_inputs):
            return None
        name = sg_inputs[slot]["name"]
        outer = scope.outer_node
        if scope.outer_scope is self.top:
            forced = self.overrides.get(str(outer["id"]), {})
            if name in forced:
                return ("value", forced[name])
        for inp in outer.get("inputs", []):
            if inp.get("name") == name:
                src = self._input_source(scope.outer_scope, outer, inp)
                if src is not None:
                    return src
                break
        named = outer.get("widgets_values_named") or {}
        if named.get(name) is not None:
            return ("value", named[name])
        return None

    def _resolve_output(self, scope: _Scope, node_id: int, slot: int):
        if node_id == -10:  # subgraph input pseudo-node
            return self._resolve_subgraph_input(scope, slot)
        node = scope.nodes.get(node_id)
        if node is None:
            return None
        mode = self._mode(scope, node)
        if mode == MODE_MUTE:
            return None
        if mode == MODE_BYPASS:
            return self._bypass(scope, node, slot)
        ntype = node["type"]
        if ntype in FRONTEND_ONLY:
            return None
        if ntype == "Reroute":
            inputs = node.get("inputs", [])
            return self._input_source(scope, node, inputs[0]) if inputs else None
        if ntype == "PrimitiveNode":
            vals = node.get("widgets_values") or []
            return ("value", vals[0]) if vals else None
        if ntype in self.subgraphs:
            sg = self.subgraphs[ntype]
            inner = _Scope(
                sg["nodes"], sg["links"], prefix=f"{scope.prefix}{node['id']}:",
                subgraph=sg, outer_node=node, outer_scope=scope,
            )
            for link in inner.links.values():
                if link["target_id"] == -20 and link["target_slot"] == slot:
                    return self._resolve_output(inner, link["origin_id"], link["origin_slot"])
            return None
        self._emit(scope, node)
        return ("link", self._key(scope, node), slot)

    def _bypass(self, scope: _Scope, node: dict, slot: int):
        outputs = node.get("outputs", [])
        if slot >= len(outputs):
            return None
        want = outputs[slot].get("type")
        for inp in node.get("inputs", []):
            if inp.get("type") == want and inp.get("link") is not None:
                return self._input_source(scope, node, inp)
        return None

    def _emit(self, scope: _Scope, node: dict) -> None:
        key = self._key(scope, node)
        if key in self.api:
            return
        entry: dict[str, Any] = {"class_type": node["type"], "inputs": {}}
        self.api[key] = entry  # placeholder against cycles
        inputs = entry["inputs"]
        seen = set()
        for inp in node.get("inputs", []):
            name = inp["name"]
            seen.add(name)
            src = self._input_source(scope, node, inp)
            if src is None:
                continue
            inputs[name] = [src[1], src[2]] if src[0] == "link" else src[1]
        named = node.get("widgets_values_named") or {}
        for name, value in named.items():
            if name in seen or value is None:
                continue
            if name == "control_after_generate" or (isinstance(value, str) and value in CONTROL_VALUES):
                continue
            inputs[name] = value
        for name, value in self.overrides.get(key, {}).items():
            inputs[name] = value
        for name in self.unlinks.get(key, []):
            inputs.pop(name, None)
        if scope is self.top:
            for name, value in self.overrides.get(str(node["id"]), {}).items():
                inputs[name] = value
            for name in self.unlinks.get(str(node["id"]), []):
                inputs.pop(name, None)
        # ComfyUI rejects the API prompt when a value is a non-link list; keep JSON-serialisable.
        json.dumps(inputs)


def load_workflow(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)
