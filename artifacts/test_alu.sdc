create_clock -name virt_clock -period 5.0
set_input_delay  -clock virt_clock 1.000 [all_inputs]
set_output_delay -clock virt_clock 1.000 [all_outputs]
