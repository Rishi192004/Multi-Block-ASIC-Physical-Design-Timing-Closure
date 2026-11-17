"""Parser for Yosys synthesis logs and statistics."""

import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from src.common.types import ParsedMetric
from src.common.logger import logger


class YosysLogParser:
    """Extracts cell counts, logic statistics, and warnings with byte-offset provenance."""

    def __init__(self):
        # Patterns for Yosys statistics
        self.re_cell_stat = re.compile(r"^\s*([a-zA-Z0-9_\$]+)\s+(\d+)\s*$")
        self.re_wire_stat = re.compile(r"^\s*Number of wires:\s+(\d+)")
        self.re_wire_bits = re.compile(r"^\s*Number of wire bits:\s+(\d+)")
        self.re_public_wires = re.compile(r"^\s*Number of public wires:\s+(\d+)")
        self.re_memories = re.compile(r"^\s*Number of memories:\s+(\d+)")
        self.re_memory_bits = re.compile(r"^\s*Number of memory bits:\s+(\d+)")
        self.re_processes = re.compile(r"^\s*Number of processes:\s+(\d+)")
        self.re_cells_total = re.compile(r"^\s*Number of cells:\s+(\d+)")
        self.re_chip_area = re.compile(r"^\s*Chip area for top module [^:]*:\s+([0-9\.]+)")
        self.re_warning = re.compile(r"^Warning:\s*(.*)$")
        self.re_error = re.compile(r"^ERROR:\s*(.*)$")

    def parse_file(self, log_path: Path) -> List[ParsedMetric]:
        """Parse yosys log file and return list of atomic ParsedMetric objects."""
        if not log_path.exists():
            logger.warning(f"Log file not found: {log_path}")
            return []

        metrics: List[ParsedMetric] = []
        in_cell_stats_block = False

        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            byte_offset = 0
            for line_no, line in enumerate(f, start=1):
                raw_line = line.rstrip("\r\n")

                # Detect cell stats header
                if "=== " in raw_line and "design hierarchy ===" in raw_line:
                    in_cell_stats_block = False
                elif "=== " in raw_line and ("design hierarchy" not in raw_line):
                    in_cell_stats_block = True

                # Total cells
                m_cells = self.re_cells_total.search(raw_line)
                if m_cells:
                    val = float(m_cells.group(1))
                    metrics.append(ParsedMetric(
                        category="CELL_COUNT",
                        name="total_cells",
                        float_value=val,
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))
                    in_cell_stats_block = True

                # Wires
                m_wires = self.re_wire_stat.search(raw_line)
                if m_wires:
                    metrics.append(ParsedMetric(
                        category="NETLIST",
                        name="num_wires",
                        float_value=float(m_wires.group(1)),
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))

                # Wire bits
                m_wbits = self.re_wire_bits.search(raw_line)
                if m_wbits:
                    metrics.append(ParsedMetric(
                        category="NETLIST",
                        name="num_wire_bits",
                        float_value=float(m_wbits.group(1)),
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))

                # Memories
                m_mem = self.re_memories.search(raw_line)
                if m_mem:
                    metrics.append(ParsedMetric(
                        category="NETLIST",
                        name="num_memories",
                        float_value=float(m_mem.group(1)),
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))

                # Chip area
                m_area = self.re_chip_area.search(raw_line)
                if m_area:
                    metrics.append(ParsedMetric(
                        category="AREA",
                        name="chip_area_um2",
                        float_value=float(m_area.group(1)),
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))

                # Individual cell stats inside the block
                if in_cell_stats_block:
                    m_stat = self.re_cell_stat.match(raw_line)
                    if m_stat:
                        c_name = m_stat.group(1)
                        c_count = int(m_stat.group(2))
                        # Ignore top-level headers
                        if c_name not in ["Number", "Chip", "==="]:
                            metrics.append(ParsedMetric(
                                category="CELL_TYPE",
                                name=f"cell_{c_name}",
                                float_value=float(c_count),
                                line_number=line_no,
                                byte_offset=byte_offset,
                                raw_snippet=raw_line,
                                metadata={"cell_name": c_name}
                            ))

                # Warnings
                m_warn = self.re_warning.match(raw_line)
                if m_warn:
                    metrics.append(ParsedMetric(
                        category="LOG_EVENT",
                        name="warning",
                        string_value=m_warn.group(1).strip(),
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))

                # Errors
                m_err = self.re_error.match(raw_line)
                if m_err:
                    metrics.append(ParsedMetric(
                        category="LOG_EVENT",
                        name="error",
                        string_value=m_err.group(1).strip(),
                        line_number=line_no,
                        byte_offset=byte_offset,
                        raw_snippet=raw_line
                    ))

                byte_offset += len(line.encode("utf-8"))

        return metrics

    def extract_cell_histogram(self, metrics: List[ParsedMetric]) -> Dict[str, int]:
        """Extract dictionary mapping cell name to count."""
        hist = {}
        for m in metrics:
            if m.category == "CELL_TYPE" and m.metadata.get("cell_name"):
                hist[m.metadata["cell_name"]] = int(m.float_value or 0)
        return hist
