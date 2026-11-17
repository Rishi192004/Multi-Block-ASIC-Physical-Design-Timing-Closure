# OpenROAD PD Script for alu - sky130hd - EDA-Genius
read_lef "/opt/eda_env/share/pdk/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef"
read_lef "/opt/eda_env/share/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef"
read_liberty "/opt/eda_env/share/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
read_verilog "/opt/cad_ai/artifacts/runs/run_alu_2ae9d4bf/alu_synth.v"
link_design alu
read_sdc "/opt/cad_ai/artifacts/runs/run_alu_2ae9d4bf/alu.sdc"

# Floorplan
initialize_floorplan -site unithd -utilization 40 -aspect_ratio 1.0 -core_space 10.0
make_tracks li1  -x_offset 0.23 -x_pitch 0.46 -y_offset 0.17 -y_pitch 0.34
make_tracks met1 -x_offset 0.17 -x_pitch 0.34 -y_offset 0.17 -y_pitch 0.34
make_tracks met2 -x_offset 0.23 -x_pitch 0.46 -y_offset 0.23 -y_pitch 0.46
make_tracks met3 -x_offset 0.34 -x_pitch 0.68 -y_offset 0.34 -y_pitch 0.68
make_tracks met4 -x_offset 0.46 -x_pitch 0.92 -y_offset 0.46 -y_pitch 0.92
make_tracks met5 -x_offset 1.70 -x_pitch 3.40 -y_offset 1.70 -y_pitch 3.40
place_pins -hor_layers met3 -ver_layers met2

# Global + Detailed Placement
global_placement -density 0.6
detailed_placement

# Signoff Reports - written via Tcl file I/O
set _fd [open "/opt/cad_ai/artifacts/runs/run_alu_2ae9d4bf/timing_signoff.rpt" w]
puts $_fd [report_design_area]
puts $_fd [report_checks -path_delay min_max -digits 4]
puts $_fd [report_worst_slack -max]
puts $_fd [report_tns]
close $_fd

set _pfd [open "/opt/cad_ai/artifacts/runs/run_alu_2ae9d4bf/power_signoff.rpt" w]
puts $_pfd [report_power]
close $_pfd

write_def "/opt/cad_ai/artifacts/runs/run_alu_2ae9d4bf/alu_placed.def"
exit
