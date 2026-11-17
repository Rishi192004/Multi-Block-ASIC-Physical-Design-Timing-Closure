"""RTL-level static feature extractor for Verilog and SystemVerilog sources."""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class RTLFeatures(BaseModel):
    """Structured container for RTL-level features."""
    rtl_num_modules: int = 0
    rtl_num_ports: int = 0
    rtl_num_inputs: int = 0
    rtl_num_outputs: int = 0
    rtl_num_inouts: int = 0
    rtl_num_registers: int = 0
    rtl_num_wires: int = 0
    rtl_num_always_blocks: int = 0
    rtl_num_comb_assignments: int = 0
    rtl_source_bytes: int = 0
    rtl_source_lines: int = 0
    rtl_comment_lines: int = 0
    rtl_blank_lines: int = 0
    rtl_code_lines: int = 0
    rtl_has_parameters: bool = False
    rtl_num_parameters: int = 0


class RTLExtractor:
    """Parses Verilog / SystemVerilog source files and extracts syntax & structural metrics."""

    def __init__(self):
        # Module declaration: module <name> ... ( <ports> );
        self.re_module_header = re.compile(r"\bmodule\s+([a-zA-Z0-9_$]+)\s*(?:#\s*\([\s\S]*?\))?\s*(?:\(([\s\S]*?)\))?\s*;", re.MULTILINE)
        
        # Declarations inside module body (delimited by semicolon)
        self.re_body_reg = re.compile(r"\b(?:reg|logic)\b\s*(?:\[[^\]]+\])?\s*([^;]+);", re.MULTILINE)
        self.re_body_wire = re.compile(r"\bwire\b\s*(?:\[[^\]]+\])?\s*([^;]+);", re.MULTILINE)
        self.re_body_input = re.compile(r"\binput\b\s*(?:wire|reg|logic)?\s*(?:\[[^\]]+\])?\s*([^;]+);", re.MULTILINE)
        self.re_body_output = re.compile(r"\boutput\b\s*(?:wire|reg|logic)?\s*(?:\[[^\]]+\])?\s*([^;]+);", re.MULTILINE)
        self.re_body_inout = re.compile(r"\binout\b\s*(?:wire|reg|logic)?\s*(?:\[[^\]]+\])?\s*([^;]+);", re.MULTILINE)
        
        # Behavioral blocks
        self.re_always = re.compile(r"\balways(?:_comb|_ff|_latch)?\b", re.MULTILINE)
        self.re_assign = re.compile(r"\bassign\b\s+[^=]+=", re.MULTILINE)
        self.re_param = re.compile(r"\bparameter\b\s*(?:\[[^\]]+\])?\s*([^;=,]+)", re.MULTILINE)

    def _count_identifiers(self, matched_group: str) -> int:
        """Count individual signal names in comma-separated declarations (e.g. 'a, b, c')."""
        clean = re.sub(r"\[[^\]]*\]", "", matched_group)
        parts = [p.strip() for p in clean.split(",") if p.strip()]
        return len(parts)

    def extract_from_file(self, file_path: Path) -> RTLFeatures:
        """Extract RTL features from a single source file."""
        if not file_path.exists():
            return RTLFeatures()

        content = file_path.read_text(encoding="utf-8", errors="replace")
        return self.extract_from_text(content, source_bytes=file_path.stat().st_size)

    def extract_from_files(self, file_paths: List[Path]) -> RTLFeatures:
        """Extract aggregated RTL features across multiple source files."""
        total = RTLFeatures()
        for fp in file_paths:
            feats = self.extract_from_file(fp)
            total.rtl_num_modules += feats.rtl_num_modules
            total.rtl_num_ports += feats.rtl_num_ports
            total.rtl_num_inputs += feats.rtl_num_inputs
            total.rtl_num_outputs += feats.rtl_num_outputs
            total.rtl_num_inouts += feats.rtl_num_inouts
            total.rtl_num_registers += feats.rtl_num_registers
            total.rtl_num_wires += feats.rtl_num_wires
            total.rtl_num_always_blocks += feats.rtl_num_always_blocks
            total.rtl_num_comb_assignments += feats.rtl_num_comb_assignments
            total.rtl_source_bytes += feats.rtl_source_bytes
            total.rtl_source_lines += feats.rtl_source_lines
            total.rtl_comment_lines += feats.rtl_comment_lines
            total.rtl_blank_lines += feats.rtl_blank_lines
            total.rtl_code_lines += feats.rtl_code_lines
            total.rtl_num_parameters += feats.rtl_num_parameters
            total.rtl_has_parameters = total.rtl_has_parameters or feats.rtl_has_parameters

        return total

    def extract_from_text(self, text: str, source_bytes: Optional[int] = None) -> RTLFeatures:
        """Extract RTL features from raw Verilog/SystemVerilog text."""
        lines = text.splitlines()
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = 0
        in_block_comment = False

        for line in lines:
            sline = line.strip()
            if in_block_comment:
                comment_lines += 1
                if "*/" in sline:
                    in_block_comment = False
            elif sline.startswith("//"):
                comment_lines += 1
            elif sline.startswith("/*"):
                comment_lines += 1
                if "*/" not in sline:
                    in_block_comment = True

        code_lines = max(0, total_lines - blank_lines - comment_lines)
        num_bytes = source_bytes if source_bytes is not None else len(text.encode("utf-8"))

        # Strip comments
        clean_code = re.sub(r"//.*", "", text)
        clean_code = re.sub(r"/\*.*?\*/", "", clean_code, flags=re.DOTALL)

        module_matches = self.re_module_header.findall(clean_code)
        num_modules = len(module_matches)

        inputs_count = 0
        outputs_count = 0
        inouts_count = 0
        reg_count = 0
        wire_count = 0

        # Parse port lists from ANSI-style headers: module foo (input a, output reg b);
        for mod_name, port_list_str in module_matches:
            if not port_list_str:
                continue
            # Split port items by comma
            raw_ports = [p.strip() for p in port_list_str.split(",") if p.strip()]
            for p in raw_ports:
                if re.search(r"\binput\b", p):
                    inputs_count += 1
                elif re.search(r"\boutput\b", p):
                    outputs_count += 1
                elif re.search(r"\binout\b", p):
                    inouts_count += 1

                if re.search(r"\b(?:reg|logic)\b", p):
                    reg_count += 1
                elif re.search(r"\bwire\b", p):
                    wire_count += 1

        # Now remove module headers to isolate module body
        body_code = self.re_module_header.sub("", clean_code)

        # Parse non-ANSI port declarations in module body if any
        inputs_count += sum(self._count_identifiers(m) for m in self.re_body_input.findall(body_code))
        outputs_count += sum(self._count_identifiers(m) for m in self.re_body_output.findall(body_code))
        inouts_count += sum(self._count_identifiers(m) for m in self.re_body_inout.findall(body_code))

        # Parse internal signals in body
        reg_count += sum(self._count_identifiers(m) for m in self.re_body_reg.findall(body_code))
        wire_count += sum(self._count_identifiers(m) for m in self.re_body_wire.findall(body_code))

        total_ports = inputs_count + outputs_count + inouts_count

        # Behavioral & Structural blocks
        always_blocks = len(self.re_always.findall(clean_code))
        comb_assigns = len(self.re_assign.findall(clean_code))

        # Parameters
        param_matches = self.re_param.findall(clean_code)
        num_params = sum(self._count_identifiers(m) for m in param_matches)

        return RTLFeatures(
            rtl_num_modules=num_modules,
            rtl_num_ports=total_ports,
            rtl_num_inputs=inputs_count,
            rtl_num_outputs=outputs_count,
            rtl_num_inouts=inouts_count,
            rtl_num_registers=reg_count,
            rtl_num_wires=wire_count,
            rtl_num_always_blocks=always_blocks,
            rtl_num_comb_assignments=comb_assigns,
            rtl_source_bytes=num_bytes,
            rtl_source_lines=total_lines,
            rtl_comment_lines=comment_lines,
            rtl_blank_lines=blank_lines,
            rtl_code_lines=code_lines,
            rtl_has_parameters=(num_params > 0),
            rtl_num_parameters=num_params
        )
