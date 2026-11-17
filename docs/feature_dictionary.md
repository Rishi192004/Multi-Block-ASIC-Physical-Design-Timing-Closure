# EDA-Genius Feature Dictionary

Documented definitions, calculation sources, and physical meaning for all engineered features.

## 1. Feature Taxonomy Overview

| Category | Prefix / Scope | Count | Description |
|---|---|---|---|
| **A. RTL Features** | `rtl_*` | 11 | Synthesizable source code structural metrics |
| **B. Netlist Features** | `netlist_*`, `gate_count_*`, `net_fanout_*` | 19 | Gate-level cell distribution, fanouts & logic depth |
| **C. Physical Design Config** | `pd_*` | 8 | Placement constraints, utilization & PDK settings |
| **D. Domain Interactions** | `feat_*`, `log_*` | 22 | Ratios, densities, and log-transformed metrics |
| **E. Targets / EDA Outcomes** | `target_*` | 9 | Runtime, area, timing slack, power, DRC violations |

## 2. Detailed Feature Catalog

| Feature Name | Category | Dtype | Extraction Source | Calculation / Description |
|---|---|---|---|---|
| `rtl_num_modules` | RTL | `int` | RTL Source (`.v`/`.sv`) | Count of module declarations (`module ... endmodule`) |
| `rtl_num_ports` | RTL | `int` | RTL Source | Sum of all input, output, and inout port pins |
| `rtl_num_inputs` | RTL | `int` | RTL Source | Total primary input port pins |
| `rtl_num_outputs` | RTL | `int` | RTL Source | Total primary output port pins |
| `rtl_num_registers` | RTL | `int` | RTL Source | Total `reg` and `logic` declarations |
| `rtl_num_wires` | RTL | `int` | RTL Source | Total internal `wire` declarations |
| `rtl_num_always_blocks` | RTL | `int` | RTL Source | Count of `always`, `always_ff`, and `always_comb` procedural blocks |
| `rtl_num_comb_assignments` | RTL | `int` | RTL Source | Count of continuous `assign` statements |
| `rtl_source_bytes` | RTL | `int` | Filesystem | RTL source file size in bytes |
| `rtl_source_lines` | RTL | `int` | RTL Source | Total raw lines of code in RTL files |
| `rtl_code_lines` | RTL | `int` | RTL Source | Non-comment, non-blank lines of Verilog code |
| `netlist_total_cells` | Netlist | `int` | Gate Netlist (`*_synth.v`) | Total standard cell instances in synthesized netlist |
| `netlist_sequential_cells` | Netlist | `int` | Gate Netlist | Count of state elements (DFFs, latches) |
| `netlist_combinational_cells` | Netlist | `int` | Gate Netlist | Total combinational logic gates |
| `netlist_ff_count` | Netlist | `int` | Gate Netlist | Dedicated flip-flop count (e.g. `sky130_fd_sc_hd__df*`) |
| `netlist_buffer_count` | Netlist | `int` | Gate Netlist | Buffer count (`sky130_fd_sc_hd__buf_*`) |
| `netlist_inverter_count` | Netlist | `int` | Gate Netlist | Inverter count (`sky130_fd_sc_hd__inv_*`) |
| `gate_count_nand` | Netlist | `int` | Gate Netlist | NAND gate instances (`nand2`, `nand3`, etc.) |
| `gate_count_nor` | Netlist | `int` | Gate Netlist | NOR gate instances (`nor2`, `nor3`, etc.) |
| `gate_count_and` | Netlist | `int` | Gate Netlist | AND gate instances |
| `gate_count_or` | Netlist | `int` | Gate Netlist | OR gate instances |
| `gate_count_xor` | Netlist | `int` | Gate Netlist | XOR gate instances |
| `gate_count_xnor` | Netlist | `int` | Gate Netlist | XNOR gate instances |
| `gate_count_mux` | Netlist | `int` | Gate Netlist | Multiplexer instances (`mux2`, `mux4`) |
| `gate_count_aoi` | Netlist | `int` | Gate Netlist | AND-OR-Invert compound cells (`a21oi`, `a31oi`) |
| `gate_count_oai` | Netlist | `int` | Gate Netlist | OR-AND-Invert compound cells (`o21ai`, `o31ai`) |
| `netlist_estimated_logic_depth` | Netlist | `int` | Netlist DAG | Longest topological path through combinational gates |
| `net_fanout_mean` | Netlist | `float` | Netlist Graph | Mean number of pin loads driven per net |
| `net_fanout_max` | Netlist | `int` | Netlist Graph | Maximum fanout load of any individual net |
| `net_fanout_std` | Netlist | `float` | Netlist Graph | Standard deviation of fanout distribution |
| `pd_target_utilization` | Config | `float` | Floorplan TCL | Target core cell placement density (0.05 to 0.95) |
| `pd_core_aspect_ratio` | Config | `float` | Floorplan TCL | Floorplan aspect ratio (height / width) |
| `pd_core_space_um` | Config | `float` | Floorplan TCL | Margin distance from die boundary to core in µm |
| `pd_clock_period_ns` | Config | `float` | SDC Constraints | Target clock period constraint in nanoseconds |
| `pd_clock_uncertainty_ns` | Config | `float` | SDC Constraints | Clock jitter & uncertainty budget in nanoseconds |
| `pd_clock_transition_ns` | Config | `float` | SDC Constraints | Maximum clock transition time in nanoseconds |
| `pd_num_routing_layers` | Config | `int` | Technology LEF | Available metal routing layer count (e.g. 6 for SKY130) |
| `pd_is_sky130` | Config | `int` | PDK Registry | Binary indicator (1 = SkyWater SKY130A, 0 = Generic) |
| `feat_seq_ratio` | Domain | `float` | Calculated | Ratio of sequential cells: `netlist_seq / total_cells` |
| `feat_comb_ratio` | Domain | `float` | Calculated | Ratio of combinational cells: `netlist_comb / total_cells` |
| `feat_clock_freq_mhz` | Domain | `float` | Calculated | Operating frequency: `1000.0 / clock_period_ns` |
| `feat_fanout_intensity` | Domain | `float` | Calculated | Fanout complexity: `fanout_mean * log1p(fanout_max)` |
| `feat_density_proxy` | Domain | `float` | Calculated | Cell density proxy: `total_cells / target_utilization` |
| `target_synthesis_runtime_s` | Target | `float` | Yosys Execution | Wall-clock duration of RTL synthesis in seconds |
| `target_placement_runtime_s` | Target | `float` | OpenROAD Execution | Wall-clock duration of placement & PD in seconds |
| `target_total_runtime_s` | Target | `float` | Flow Orchestrator | End-to-end flow execution time in seconds |
| `target_cell_area_um2` | Target | `float` | OpenROAD / STA | Total standard cell silicon area in µm² |
| `target_wns_ns` | Target | `float` | OpenSTA Timing | Worst Negative Slack in nanoseconds (>=0 is MET) |
| `target_tns_ns` | Target | `float` | OpenSTA Timing | Total Negative Slack accumulated across timing endpoints |
| `target_total_power_w` | Target | `float` | OpenROAD Power | Total dynamic and leakage power dissipation in Watts |
