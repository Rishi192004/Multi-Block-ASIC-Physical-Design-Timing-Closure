"""Netlist-level structural feature extractor from synthesized gate-level Verilog."""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
import numpy as np
from pydantic import BaseModel, Field


class NetlistFeatures(BaseModel):
    """Structured container for Netlist-level features."""
    netlist_total_cells: int = 0
    netlist_sequential_cells: int = 0
    netlist_combinational_cells: int = 0
    netlist_ff_count: int = 0
    netlist_latch_count: int = 0
    netlist_buffer_count: int = 0
    netlist_inverter_count: int = 0
    
    # Gate distribution counts
    gate_count_nand: int = 0
    gate_count_nor: int = 0
    gate_count_and: int = 0
    gate_count_or: int = 0
    gate_count_xor: int = 0
    gate_count_xnor: int = 0
    gate_count_mux: int = 0
    gate_count_aoi: int = 0
    gate_count_oai: int = 0
    gate_count_complex: int = 0

    # Net fanout statistics
    net_fanout_mean: float = 0.0
    net_fanout_max: int = 0
    net_fanout_std: float = 0.0
    net_fanout_median: float = 0.0
    total_nets: int = 0

    # Logic depth
    netlist_estimated_logic_depth: int = 0


class NetlistExtractor:
    """Extracts gate counts, cell categorizations, fanout distribution, and logic depth."""

    def __init__(self):
        # Cell instance: <cell_type> <instance_name> ( .PIN(NET), ... );
        self.re_cell = re.compile(
            r"([a-zA-Z0-9_\$]+)\s+([a-zA-Z0-9_\$]+)\s*\(([\s\S]*?)\);",
            re.MULTILINE
        )
        self.re_pin = re.compile(r"\.([a-zA-Z0-9_\$]+)\s*\(\s*([a-zA-Z0-9_\[\]\$]+)\s*\)")
        
        # Output pin heuristics across generic and PDK cells
        self.output_pins = {"y", "x", "q", "qn", "cout", "s", "z", "out"}

    def _is_sequential(self, cell_type: str) -> Tuple[bool, bool, bool]:
        """Classify cell type as (is_seq, is_ff, is_latch)."""
        c = cell_type.lower()
        if "dff" in c or "dfxtp" in c or "__df" in c:
            return True, True, False
        if "latch" in c or "__dl" in c:
            return True, False, True
        return False, False, False

    def _classify_gate(self, cell_type: str) -> str:
        """Classify standard combinational gate family."""
        c = cell_type.lower()
        if "nand" in c:
            return "nand"
        if "nor" in c:
            return "nor"
        if "xnor" in c:
            return "xnor"
        if "xor" in c:
            return "xor"
        if "and" in c:
            return "and"
        if "or" in c and "nor" not in c and "xor" not in c and "xnor" not in c:
            return "or"
        if "mux" in c:
            return "mux"
        if "aoi" in c or "a21oi" in c or "a31oi" in c or "a22oi" in c or "a41oi" in c:
            return "aoi"
        if "oai" in c or "o21ai" in c or "o31ai" in c or "o22ai" in c or "o32ai" in c:
            return "oai"
        if "inv" in c or "not" in c:
            return "inv"
        if "buf" in c:
            return "buf"
        return "complex"

    def extract_from_file(self, netlist_path: Path) -> NetlistFeatures:
        """Parse synthesized Verilog netlist file and extract structural features."""
        if not netlist_path.exists():
            return NetlistFeatures()

        content = netlist_path.read_text(encoding="utf-8", errors="replace")
        return self.extract_from_text(content)

    def extract_from_text(self, text: str) -> NetlistFeatures:
        """Parse gate-level netlist string and compute connectivity graph & metrics."""
        clean = re.sub(r"//.*", "", text)
        clean = re.sub(r"/\*.*?\*/", "", clean, flags=re.DOTALL)

        cell_matches = self.re_cell.findall(clean)
        if not cell_matches:
            return NetlistFeatures()

        total_cells = 0
        seq_cells = 0
        ff_count = 0
        latch_count = 0
        buf_count = 0
        inv_count = 0

        gate_dist = {
            "nand": 0, "nor": 0, "and": 0, "or": 0,
            "xor": 0, "xnor": 0, "mux": 0, "aoi": 0, "oai": 0, "complex": 0
        }

        # Net connectivity: net -> list of (cell_id, is_input)
        net_loads: Dict[str, int] = {}
        # DAG adjacency for combinational depth: cell_idx -> list of successor cell_idxs
        comb_cell_outputs: Dict[str, int] = {}  # net_name -> driving combinational cell_idx
        comb_cell_inputs: Dict[int, List[str]] = {}

        comb_idx = 0

        for cell_type, inst_name, ports_str in cell_matches:
            # Skip module header or declarations that match regex
            if cell_type in ("module", "wire", "input", "output", "inout", "reg", "assign"):
                continue

            total_cells += 1
            is_seq, is_ff, is_latch = self._is_sequential(cell_type)
            if is_seq:
                seq_cells += 1
                if is_ff:
                    ff_count += 1
                if is_latch:
                    latch_count += 1
            else:
                gate_family = self._classify_gate(cell_type)
                if gate_family == "inv":
                    inv_count += 1
                elif gate_family == "buf":
                    buf_count += 1
                elif gate_family in gate_dist:
                    gate_dist[gate_family] += 1
                else:
                    gate_dist["complex"] += 1

            # Parse pin connections
            pins = self.re_pin.findall(ports_str)
            curr_comb_id = None
            if not is_seq:
                curr_comb_id = comb_idx
                comb_cell_inputs[curr_comb_id] = []
                comb_idx += 1

            for pin_name, net_name in pins:
                pin_lower = pin_name.lower()
                is_output = pin_lower in self.output_pins

                if is_output:
                    if curr_comb_id is not None:
                        comb_cell_outputs[net_name] = curr_comb_id
                else:
                    # Input load
                    net_loads[net_name] = net_loads.get(net_name, 0) + 1
                    if curr_comb_id is not None:
                        comb_cell_inputs[curr_comb_id].append(net_name)

        comb_cells = max(0, total_cells - seq_cells)

        # Net fanout statistics
        fanouts = list(net_loads.values()) if net_loads else [0]
        fanout_mean = float(np.mean(fanouts)) if fanouts else 0.0
        fanout_max = int(np.max(fanouts)) if fanouts else 0
        fanout_std = float(np.std(fanouts)) if fanouts else 0.0
        fanout_median = float(np.median(fanouts)) if fanouts else 0.0

        # Estimated Logic Depth via DAG longest path
        # Build adjacency: cell_A -> cell_B if cell_A drives an input of cell_B
        adj: Dict[int, List[int]] = {i: [] for i in range(comb_idx)}
        in_degree: Dict[int, int] = {i: 0 for i in range(comb_idx)}

        for c_id, in_nets in comb_cell_inputs.items():
            for n in in_nets:
                if n in comb_cell_outputs:
                    pred_id = comb_cell_outputs[n]
                    if pred_id != c_id:
                        adj[pred_id].append(c_id)
                        in_degree[c_id] = in_degree.get(c_id, 0) + 1

        # Longest path in DAG using Kahn's topological sort
        queue = [i for i in range(comb_idx) if in_degree[i] == 0]
        depths = {i: 1 for i in range(comb_idx)}
        visited_count = 0

        while queue:
            curr = queue.pop(0)
            visited_count += 1
            curr_depth = depths[curr]
            for succ in adj[curr]:
                if curr_depth + 1 > depths[succ]:
                    depths[succ] = curr_depth + 1
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)

        estimated_logic_depth = max(depths.values()) if depths else 0

        return NetlistFeatures(
            netlist_total_cells=total_cells,
            netlist_sequential_cells=seq_cells,
            netlist_combinational_cells=comb_cells,
            netlist_ff_count=ff_count,
            netlist_latch_count=latch_count,
            netlist_buffer_count=buf_count,
            netlist_inverter_count=inv_count,
            gate_count_nand=gate_dist["nand"],
            gate_count_nor=gate_dist["nor"],
            gate_count_and=gate_dist["and"],
            gate_count_or=gate_dist["or"],
            gate_count_xor=gate_dist["xor"],
            gate_count_xnor=gate_dist["xnor"],
            gate_count_mux=gate_dist["mux"],
            gate_count_aoi=gate_dist["aoi"],
            gate_count_oai=gate_dist["oai"],
            gate_count_complex=gate_dist["complex"],
            net_fanout_mean=round(fanout_mean, 3),
            net_fanout_max=fanout_max,
            net_fanout_std=round(fanout_std, 3),
            net_fanout_median=round(fanout_median, 3),
            total_nets=len(net_loads),
            netlist_estimated_logic_depth=estimated_logic_depth
        )
