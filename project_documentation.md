project/
├── main.py                   ← shell Application (init, bindings, utilitaires)  
├── interface_layout.py       
├── bin/
│   └── data/
│       └── config.py         
└── mixins/
    ├── __init__.py            
    ├── serial_mixin.py        ← threads, lecture série, queue
    ├── plot_mixin.py          ← affichage graphique
    ├── file_mixin.py          ← gestion fichiers/dossiers
    ├── hardware_mixin.py      ← servo, vannes, offset pression
    └── dma_mixin.py           ← machine d'états DMA
	
	
	# Project Documentation : DMA Test Application
> **Purpose of this document**: Provide a complete structural map of the codebase so that an AI can understand every function's role, its inputs/outputs, and its relationships, then substitute hardware-specific implementations for a new target hardware.

---

## 1. Architecture Overview

```
project/
         main.py                    -> Application shell (init, bindings, utilities)
         interface_layout.py        -> Tkinter widget layout (not documented here : no source provided)
         bin/
               data/
                   config.py          -> Config loader (not documented here : no source provided)
        mixins/
             __init__.py
             serial_mixin.py        -> Serial threads, packet reading, data queue
             plot_mixin.py          -> Matplotlib display, value refresh
             file_mixin.py          -> File/folder management, recording
             hardware_mixin.py      -> Servo, valves, pressure offset, board sync
            dma_mixin.py           -> DMA state machine
```

`Application(tk.Tk, SerialMixin, PlotMixin, FileMixin, HardwareMixin, DMAMixin)` is the single runtime class. All mixins share `self` state.

---

## 2. Key Shared State (self.*)

| Attribute | Type | Description |
|---|---|---|
| `self.system_color` | `str` | Hardware variant: `'blue'`, `'black'`, or `'red'` |
| `self.config` | `Config` | Full INI-based configuration object |
| `self.interface` | `Layout` | All Tkinter widgets |
| `self.link[bi]` | `txfer.SerialTransfer` | Serial connection per board (index 1-based) |
| `self.link[bi].data_summary` | `np.ndarray` | Rolling data buffer per board |
| `self.link[bi].last_saved_index` | `int` | Current write pointer in data_summary |
| `self.link[bi].saving_data_lock` | `Lock` | Protects data_summary access |
| `self.link[bi].arduino_board_last_status` | `list[str]` | Last decoded status byte as list of '0'/'1' chars |
| `self.link[bi].pressure_offset` | `float` | Pressure zero offset for board bi, sensor 1 |
| `self.link[bi].pressure_offset2` | `float` | Pressure zero offset for board bi, sensor 2 (black/red only) |
| `self.stitched_data` | `np.ndarray` | Merged data from both boards (blue only) |
| `self.last_stitched_index_global` | `int` | Write pointer in stitched_data (blue only) |
| `self.DMA_step_index` | `int` | Current step in the DMA state machine |
| `self.ongoing_DMA` | `bool` | True while a DMA sequence is running |
| `self.currently_saving_data` | `bool` | True while file recording is active |
| `self.after_call_alive` | `bool` | Gate for all Tkinter `after()` callbacks |
| `self.continous_dir` | `int` | Current rotation direction: -1, 0, or 1 |
| `self.continous_rotation_speed` | `int` | Percentage speed for continuous rotation |
| `self.pause_at_step_end` | `bool` | If True, pause dialog shown between DMA tests |
| `self.abort_current_saving` | `bool` | If True, file is deleted on stop_record() |
| `self.change_step_index_lock` | `Lock` | Protects DMA_step_index writes |
| `self.queue_serial_data` | `queue.Queue` | Raw packets from ticking thread to consumer thread |
| `self.queue_stitching_locker` | `queue.Queue` | Triggers stitching thread (blue only) |
| `self.invert_lately_max/min/middle/start` | `bool` | Hysteresis flags for DMA loading modes |
| `self.pressure_max_dma_loc` | `float` | Local (per-test) DMA pressure upper bound |
| `self.pressure_min_dma_loc` | `float` | Local (per-test) DMA pressure lower bound |
| `self.count_homing_sensor_up/down` | `int` | Debounce counters for homing sensor |

---

## 3. Config Object : Key Fields Referenced

| Path | Description |
|---|---|
| `config.arduino_general.nb_board` | Number of Arduino boards (typically 1 or 2) |
| `config.arduino_general.board_ref` | Board index for reference circuit |
| `config.arduino_general.board_tissu` | Board index for tissue circuit |
| `config.arduino_general.count_sensor_number` | Current angular position (0:60 counts) |
| `config.arduino[bi].port` | COM port string for board bi |
| `config.arduino[bi].pmin/pmax` | Sensor pressure range |
| `config.arduino[bi].pressure_index_at_pmin` | Raw ADC value at pmin |
| `config.arduino[bi].pressure_index_range` | ADC range |
| `config.arduino[bi].factor` | Computed mbar/ADC-count |
| `config.starting_param.sampling_rate_micro` | Sampling period in microseconds |
| `config.starting_param.nb_tours_per_test` | Number of rotation cycles per test |
| `config.starting_param.nb_tests_per_position` | Number of tests per position |
| `config.default_system.nb_lignes_data` | Chunk size for data array growth |
| `config.default_system.pressure_max_cycle` | Pressure inversion threshold (cycle modes) |
| `config.default_system.pressure_max_dma` | DMA pressure upper bound |
| `config.default_system.pressure_min_dma` | DMA pressure lower bound |
| `config.convention.ref_test_step_*` | Integer step IDs for the DMA state machine |
| `config.convention.line_status_*` | Bit-index into the status byte string |

---

## 4. `mixins/__init__.py`

Simple re-export module. No classes or logic.

```python
from .serial_mixin import SerialMixin
from .plot_mixin import PlotMixin
from .file_mixin import FileMixin
from .hardware_mixin import HardwareMixin
from .dma_mixin import DMAMixin
```

---

## 5. `main.py` : class `Application`

**Inherits**: `tk.Tk, SerialMixin, PlotMixin, FileMixin, HardwareMixin, DMAMixin`

### `__init__(self, master=None)`
- **Description**: Entry point. Sets `system_color`, then calls the four private init helpers.
- **Inputs**: none (beyond optional tk master)
- **Side effects**: Full application initialization
- **Calls**: `_load_config`, `_init_window`, `_init_state_variables`, `_init_tk_variables`, `_bind_buttons`
- **Called by**: `main()`

---

### `_load_config(self)`
- **Description**: Selects the INI file based on `system_color`, instantiates `Config`, calls `test_config_values`.
- **Inputs**: `self.system_color`
- **Side effects**: Sets `self.config`, `self.folder_ini`, `self.time_program_start`
- **Calls**: `Config(...)`, `self.test_config_values()`
- **Called by**: `__init__`

---

### `_init_window(self)`
- **Description**: Configures Tk window geometry, title, creates the `Layout` object.
- **Inputs**: `self.config.default_windows.*`
- **Side effects**: Sets `self.interface`, configures window, binds close to `exit_programm`
- **Calls**: `Layout(self, self.config)`, `self.interface.create_app_windows()`
- **Called by**: `__init__`

---

### `_init_state_variables(self)`
- **Description**: Initializes every runtime attribute to its default value. Groups: serial state, display loops, locks, DMA state, servo/sensors, recording, stitched data (blue), queues.
- **Inputs**: `self.system_color`, `self.config.*`
- **Side effects**: Creates all `Lock` objects, `queue.Queue` objects, sets all boolean/integer flags
- **Calls**: `Lock()`, `queue.Queue()`
- **Called by**: `__init__`

---

### `_init_tk_variables(self)`
- **Description**: Creates all Tkinter `*Var` objects, links them to widgets, attaches trace callbacks to propagate changes to `self.config`.
- **Inputs**: `self.config.starting_param.*`, `self.interface.*`
- **Side effects**: Sets `self.tkvar_*`, `self.mastervar_*`, configures widget `textvariable`
- **Calls**: `_bind_entry_var`, `_compute_aperture_values`, `implement_folder_structure`, `define_name_txt_saved`
- **Called by**: `__init__`

---

### `_bind_entry_var(self, tracker_attr, entry, var_attr, var_type, initial_value, config_key)`
- **Description**: Helper. Binds one Entry widget to a config key via a master variable and a dirty-flag tracker.
- **Inputs**: `tracker_attr` (str name of bool flag on self), `entry` (tk.Entry), `var_attr` (str name of var on self), `var_type` (IntVar/StringVarâ€¦), `initial_value`, `config_key` (dot-path string)
- **Side effects**: Creates the variable on self, attaches trace, binds `<Key>` event
- **Calls**: `make_on_entry_modified_by_user`, `fun_modify_initial_value`
- **Called by**: `_init_tk_variables`

---

### `_compute_aperture_values(self)`
- **Description**: Recomputes `syringe_section_ratio`, `cup_mat_circuit_volumes_ini`, `V_ref_aperture`, and `continous_rotation_speed` based on the selected aperture diameter.
- **Inputs**: `self.mastervar_diameter_aperture`, `self.config.default_system.*`, `self.config.starting_param.*`
- **Side effects**: Updates `self.syringe_section_ratio`, `self.cup_mat_circuit_volumes_ini`, `self.V_ref_aperture`, `self.continous_rotation_speed`
- **Calls**: none
- **Called by**: `_init_tk_variables`, `fun_modify_initial_value` (when diameter changes)

---

### `_bind_buttons(self)`
- **Description**: Assigns `command=` to every button in the interface.
- **Inputs**: `self.interface.*` (all buttons), `self.config.convention.ref_test_step_valve_open0_request`
- **Side effects**: Configures button commands and initial states
- **Calls**: References to all public action methods (see each mixin)
- **Called by**: `__init__`

---

### `toggle_serial_connection(self)`
- **Description**: Dispatcher : calls `connect_serial()` or `disconnect_serial()` based on `self._serial_connected`.
- **Calls**: `connect_serial`, `disconnect_serial`
- **Called by**: `But_connect_serial` command

---

### `connect_serial(self)`
- **Description**: Reads ports from UI, disables connection widgets, spawns `_connect_serial_thread`.
- **Inputs**: `self.interface.Combobox_port_board[bi]`, `self.interface.Combobox_baudrate_board[bi]`
- **Side effects**: Populates `self.config.arduino[bi].port`, `self._serial_baud[bi]`, disables UI
- **Calls**: `threading.Thread(target=_connect_serial_thread)`
- **Called by**: `toggle_serial_connection`

---

### `_connect_serial_thread(self)`
- **Description**: Worker thread. Calls `_init_serial()` and schedules the success or error callback on the Tk main thread.
- **Calls**: `_init_serial`, `self.after(0, _on_serial_connected)` or `self.after(0, _on_serial_error)`
- **Called by**: `connect_serial` (in a daemon thread)

---

### `_on_serial_connected(self)`
- **Description**: Called in main thread on successful connection. Updates UI, navigates to measurement tab, starts display loops.
- **Side effects**: Sets `self._serial_connected = True`, re-enables/re-labels button, selects notebook tab
- **Calls**: `_start_display_loops`
- **Called by**: `_connect_serial_thread` via `after(0, ...)`

---

### `_on_serial_error(self, error_msg)`
- **Description**: Called in main thread on connection failure. Restores UI, shows error dialog.
- **Inputs**: `error_msg` (str)
- **Side effects**: Sets `self._serial_connected = False`, re-enables form widgets, calls `messagebox.showerror`
- **Called by**: `_connect_serial_thread` via `after(0, ...)`

---

### `disconnect_serial(self)`
- **Description**: Stops all display loops and serial threads, closes all ports, resets `self.link`, updates UI.
- **Side effects**: Stops threads, closes serial ports, sets `self._serial_connected = False`
- **Calls**: `stop_threads` (SerialMixin), `self.link[bi].close()`
- **Called by**: `toggle_serial_connection`

---

### `refresh_serial_ports(self)`
- **Description**: Lists available COM ports and repopulates the combobox values.
- **Inputs**: `serial.tools.list_ports.comports()`
- **Side effects**: Updates `self.interface.Combobox_port_board[bi]['values']`
- **Called by**: `But_refresh_ports` command

---

### `_init_serial(self)`
- **Description**: Opens serial ports via `pySerialTransfer`, attaches packet callbacks, initializes per-board data structures, waits until all boards respond. Raises `ConnectionError` on failure.
- **Inputs**: `self.config.arduino[bi].port`, `self._serial_baud[bi]`, `self.system_color`
- **Side effects**: Populates `self.link[bi]` with fully configured SerialTransfer objects
- **Calls**: `txfer.SerialTransfer(port, baud)`, `Modify_pressure_sampling_rate`, `_read_a_packet_to_queue` (registered as callback)
- **Called by**: `_connect_serial_thread`
- **Hardware coupling**: Direct. Replace `txfer.SerialTransfer` calls and the `lnk.available()` wait loop.

---

### `_start_display_loops(self)`
- **Description**: Synchronizes boards and starts the two periodic Tkinter `after()` loops (data display and plot update).
- **Side effects**: Sets `self.print_output_values`, `self.after_call_alive`; schedules `print_data` and `plot_data`
- **Calls**: `Board_synchronize`, `set_plot_mode`, `self.after(â€¦, print_data)`, `self.after(â€¦, plot_data)`
- **Called by**: `_on_serial_connected`

---

### `test_config_values(self)`
- **Description**: Clamps `sampling_rate_micro` to â‰¤ 9999 and computes derived config fields.
- **Side effects**: Modifies `self.config.starting_param.sampling_rate_micro`, sets `self.plot_delta_nb_pts`
- **Called by**: `_load_config`

---

### `make_on_entry_modified_by_user(self, tracking_var) â†’ callable`
- **Description**: Returns a `<Key>` callback that sets `self.<tracking_var> = True`.
- **Inputs**: `tracking_var` (str)
- **Returns**: Event handler function
- **Called by**: `_bind_entry_var`

---

### `fun_modify_initial_value(self, name, index, mode, adress_in_self_config, master_variable, entry_possible_origine, entry_object)`
- **Description**: Generic trace callback. Reads the new value from entry or variable and writes it into `self.config` via dot-path string. Also triggers `_compute_aperture_values` when the diameter changes.
- **Inputs**: `adress_in_self_config` (dot-path string, e.g. `"config.default_system.pressure_max_cycle"`), `master_variable` (tk.*Var), dirty-flag and entry widget (optional)
- **Side effects**: Sets attribute on config, optionally calls `_compute_aperture_values`
- **Called by**: All tk.*Var `.trace_add('write', ...)` callbacks

---

### `change_calibration_or_test(self)`
- **Description**: Toggles `mastervar_perform_calib` and updates the UI frame color and button label accordingly. Refreshes folder structure and file name.
- **Calls**: `implement_folder_structure`, `define_name_txt_saved`
- **Called by**: `But_change_test_mode` command

---

### `change_print_data_mode(self)`
- **Description**: Toggles `self.print_output_values` on/off.
- **Called by**: `But_print_data` command

---

### `exit_programm(self)`
- **Description**: Clean shutdown. If connected: stops DMA, opens valves, stops servo, waits for last packets, closes recording file, stops threads, closes serial ports. Always saves config and destroys window.
- **Calls**: `stop_DMA`, `Modify_both_valves`, `Set_continous_rotation`, `Modify_pressure_sampling_rate`, `stop_threads`, `self.config.save()`
- **Called by**: `WM_DELETE_WINDOW` protocol

---

### `next_expected_index(self, last_index) â†’ int`
- **Description**: Returns next Arduino index in 0:255 cycle.
- **Inputs**: `last_index` (int 0:255)
- **Returns**: `last_index + 1`, or `0` if `last_index == 255`
- **Called by**: (utility, not observed in current code)

---

### `developp_status(self, board_index)`
- **Description**: Debug print. Decodes the status byte of a board into human-readable labels.
- **Inputs**: `self.link[board_index].arduino_board_last_status`, `self.config.convention.*`
- **Called by**: (manual debug use)

---

## 6. `mixins/serial_mixin.py` : class `SerialMixin`

All methods run in background threads except `stop_threads` and `correction_index`.

### `_th_extract_data_from_serials(self)`
- **Description**: Thread target. Continuously calls `link[bi].tick()` for every board in a loop. The tick triggers the registered callback `_read_a_packet_to_queue` when a full packet is received.
- **Inputs**: `self.config.arduino_general.nb_board`, `self.link[bi]`
- **Side effects**: Fills `self.queue_serial_data` indirectly via callbacks; clears buffers on stop
- **Hardware coupling**: Direct. Replace `link[bi].tick()` with new hardware read.
- **Calls**: `self.link[bi].tick()`
- **Called by**: `Board_synchronize` (started as `ticking_serials_thread`)

---

### `th_consume_queue(self)`
- **Description**: Thread target. Dequeues raw packets from `queue_serial_data`, decodes pressure values and status byte, detects missing indices, stores data in `link[bi].data_summary`, triggers stitching (blue) or writes to file directly (black/red).
- **Inputs**: `queue_serial_data` items: `[board_index, time_index, status_byte, adc_hi, adc_lo, (adc2_hi, adc2_lo for black/red)]`
- **Side effects**: Updates `link[bi].data_summary`, `link[bi].arduino_board_last_status`, triggers `queue_stitching_locker` (blue)
- **Hardware coupling**: Medium. Pressure decoding formula (`pmin + (256*hi + lo - index_at_pmin) * factor`) is sensor-specific.
- **Calls**: `_grow_data_array_if_needed`, `_update_sensor_counters`, `_save_raw_to_file_if_recording`
- **Called by**: `Board_synchronize` (started as `consume_queue_thread`)

---

### `_grow_data_array_if_needed(self, board_index)`
- **Description**: Called under `saving_data_lock`. If `data_summary` is full, concatenates a new zero-block.
- **Inputs**: `self.link[board_index].last_saved_index`, `.data_summary.shape[0]`
- **Side effects**: Extends `data_summary` in place
- **Calls**: `np.concatenate`
- **Called by**: `th_consume_queue`

---

### `_update_sensor_counters(self, status)`
- **Description**: Updates `config.arduino_general.count_sensor_number` (+1/-1 per count sensor edge) and resets to 60 on homing sensor rising edge. Manages debounce flags `monitor_continous_recent_homing` and `monitor_continous_recent_count`.
- **Inputs**: `status` (8-char bit string), `config.convention.line_status_rotation_direction/opto_homing/opto_count`
- **Side effects**: Mutates `self.config.arduino_general.count_sensor_number`, debounce flags
- **Hardware coupling**: Direct. Logic is specific to this encoder/homing sensor pair.
- **Called by**: `th_consume_queue` (black/red only)

---

### `_save_raw_to_file_if_recording(self, brd_time_ind, p1, p2, status)`
- **Description**: If `currently_saving_data`, writes one CSV line to the open file under `file_data_save_lock`.
- **Format (black/red)**: `time_index;-p1;0;-p2;homing;count;direction\n`
- **Inputs**: `brd_time_ind` (int), `p1/p2` (float mbar), `status` (bit string)
- **Calls**: `self.file_data_save_id.write(...)`
- **Called by**: `th_consume_queue` (black/red only)

---

### `th_stitching_values_for_thread(self)`
- **Description**: Thread target (blue only). Triggered by `queue_stitching_locker`. Takes the last 100-point batch from both boards and temporally aligns them into `stitched_data` using three strategies in priority order: (1) direct index match, (2) indirect index alignment, (3) resynchronization on homing sensor edge.
- **Inputs**: `link[1].data_summary`, `link[2].data_summary`
- **Output columns of stitched_data**: `[t_mat, idx_mat, p_mat, idx_ref_corrected, p_ref, sensor_mat, sensor_ref]`
- **Side effects**: Extends and writes `self.stitched_data`, increments `last_stitched_index_global`, calls `_save_stitched_to_file`
- **Calls**: `correction_index`, `_save_stitched_to_file`
- **Called by**: `Board_synchronize` (started as `stitching_thread`)

---

### `_save_stitched_to_file(self, stitched_local_data)`
- **Description**: Writes stitched rows to the text file. Handles the `save_data_up_to_nb` limit for precise stop-on-index.
- **Format (blue)**: `idx_mat;-p_mat;idx_ref;-p_ref;sensor_mat;sensor_ref\n`
- **Calls**: `self.file_data_save_id.write(...)`
- **Called by**: `th_stitching_values_for_thread`

---

### `_read_a_packet_to_queue(self, board_ind)`
- **Description**: Callback registered with `txfer`. Called by `link[bi].tick()` when a packet is complete. Validates status, reads raw bytes, pushes list to `queue_serial_data`.
- **Packet format (blue)**: 5 bytes â†’ `[board_ind, time_idx, status, adc1_hi, adc1_lo]`
- **Packet format (black/red)**: 6 bytes â†’ `[board_ind, time_idx, status, adc1_hi, adc1_lo, adc2_hi (merged)]`
- **Hardware coupling**: Direct. Byte count and layout match Arduino firmware.
- **Calls**: `queue_serial_data.put(...)`
- **Called by**: `_th_extract_data_from_serials` â†’ `link[bi].tick()` â†’ callback dispatch

---

### `stop_threads(self)`
- **Description**: Signals all three thread stop events, sends sentinel `None` into queues, joins threads.
- **Calls**: `_stop_event_ticking.set()`, `_stop_event_consuming.set()`, `_stop_event_stitching.set()`, `queue.put(None)`, `thread.join()`
- **Called by**: `Board_synchronize`, `disconnect_serial`, `exit_programm`

---

### `correction_index(self, table_index) â†’ int | np.ndarray`
- **Description**: Normalizes Arduino time index into [0, 255] by adding/subtracting 256. Works on scalar or array.
- **Inputs**: `table_index` (int or ndarray)
- **Returns**: Corrected value(s); ndarray reshaped to `(-1, 1)`
- **Called by**: `th_stitching_values_for_thread`

---

## 7. `mixins/plot_mixin.py` : class `PlotMixin`

### `update_values(self)`
- **Description**: Reads latest pressure values from `data_summary`, computes shape factor (V_syringe : V_gas) / V_ref, updates `tkvar_manometer_pressure` and `tkvar_Shape`. Updates homing sensor indicator color.
- **Inputs**: `self.link[*].data_summary`, `self.config.default_system.athmopheric_pressure`, `self.cup_mat_circuit_volumes_ini`, `self.syringe_section_ratio`, `self.V_ref_aperture`
- **Side effects**: Sets tkvar values, changes Frame/Label background colors
- **Called by**: `print_data`

---

### `print_data(self)`
- **Description**: Periodic callback (scheduled via `after`). Calls `update_values`, optionally prints raw data to console, reschedules itself.
- **Calls**: `update_values`, `self.after(print_last_data_every_ms, print_data)`
- **Called by**: `_start_display_loops` (initial schedule); self-rescheduling

---

### `set_plot_mode(self, plot_mode_choice)`
- **Description**: Sets `self.plot_output_values` and configures axis labels/line colors to match the chosen mode. Passing `None` cycles between `ref_plot_one_vs_another` and `ref_plot_vs_time`.
- **Inputs**: `plot_mode_choice` (int constant from `config.default_plot.ref_plot_*`, or None)
- **Side effects**: Updates `self.plot_output_values`, axis labels, line colors, clears lines 3/4 if entering one-vs-another
- **Called by**: `_bind_buttons`, `_start_display_loops`, `DMAMixin.master_DMA`

---

### `set_plot_length(self)`
- **Description**: Toggles `self.x_plot_length` between 0 (full history) and a 5-second window in points.
- **Side effects**: Updates `self.x_plot_length`, changes button label
- **Called by**: `But_switch_x_span` command

---

### `plot_data(self)`
- **Description**: Periodic callback. Dispatches to the correct `_plot_*` helper based on `self.plot_output_values`, then reschedules itself.
- **Calls**: `_plot_vs_index`, `_plot_vs_time`, `_plot_one_vs_another`, `_plot_temp`, `self.after(â€¦, plot_data)`
- **Called by**: `_start_display_loops`; self-rescheduling

---

### `_get_plot_indices(self, board_index) â†’ (i0, i_tip, i1)`
- **Description**: Returns slice indices for the plot window.
- **Inputs**: `link[board_index].last_saved_index`, `self.x_plot_length`, `self.plot_delta_nb_pts`, `config.default_plot.number_points_tip`
- **Returns**: `(i0, i_tip, i1)` where i0 = window start, i_tip = tip highlight start, i1 = current end
- **Called by**: all `_plot_*` helpers

---

### `_refresh_canvas(self)`
- **Description**: Calls `relim()`, `autoscale_view()`, `canvas.draw()` on the matplotlib figure.
- **Called by**: all `_plot_*` helpers

---

### `_plot_vs_index(self)`
- **Description**: Plots pressure vs Arduino index (0:255) for all boards.
- **Data source**: `link[bi].data_summary[:, 1]` (x), `[:, 2]` (y)
- **Calls**: `_get_plot_indices`, `_refresh_canvas`
- **Called by**: `plot_data`

---

### `_plot_vs_time(self)`
- **Description**: Plots pressure vs time in seconds.
- **Data source (blue)**: per-board `data_summary[:, 0]/1000` (x), `[:, 2]` (y)
- **Data source (black/red)**: board 1 columns 2 and 3 (two pressure signals)
- **Calls**: `_get_plot_indices`, `_refresh_canvas`
- **Called by**: `plot_data`

---

### `_plot_one_vs_another(self)`
- **Description**: Plots p_mat vs p_ref (Lissajous-style).
- **Data source (blue)**: `stitched_data[:, 4]` (x = p_ref), `[:, 2]` (y = p_mat)
- **Data source (black/red)**: `data_summary[:, 3]` (x), `[:, 2]` (y)
- **Calls**: `_get_plot_indices`, `_refresh_canvas`
- **Called by**: `plot_data`

---

### `_plot_temp(self, mode)`
- **Description**: Plots temperature (column 4, 6, or 7 of data_summary) alongside pressure. Mode determines which board and which column pair.
- **Data source**: `data_summary[:, 4/6/7]` depending on mode and system_color
- **Calls**: `_get_plot_indices`, `_refresh_canvas`
- **Called by**: `plot_data`

---

## 8. `mixins/file_mixin.py` : class `FileMixin`

### `implement_folder_structure(self)`
- **Description**: Creates the save folder if it does not exist.
- **Inputs**: `self.mastervar_default_folder.get()`
- **Calls**: `os.makedirs`
- **Called by**: `_init_tk_variables`, `change_calibration_or_test`, `browse_folder`

---

### `define_name_txt_saved(self)`
- **Description**: Scans the current folder to find the next available numeric file index, then builds `self.save_data_name` as `NNNbase_INDEX_raw.txt`. Also writes a color marker file and updates the UI label.
- **Inputs**: `self.mastervar_diameter_aperture`, `self.mastervar_perform_calib`, `self.mastervar_default_name_base`, `self.mastervar_default_folder`
- **Side effects**: Sets `self.save_data_name`, updates `Label_full_name_saving`
- **Calls**: `implement_folder_structure`, `os.listdir`, `np.max`
- **Called by**: `start_DMA`, `_init_tk_variables` (trace), `stop_record`

---

### `start_record(self)`
- **Description**: Opens the text file for writing, sets `currently_saving_data = True`, enables DMA control buttons, updates recording status label to green.
- **Inputs**: `self.save_data_name`, `self.mastervar_default_folder`
- **Side effects**: Creates/opens `self.file_data_save_id`, sets `self.currently_saving_data`, `self.save_data_up_to_nb = None`
- **Calls**: `open(path, 'w')`
- **Called by**: `DMAMixin.master_DMA` (on `ref_test_step_forward_request`)

---

### `stop_record(self)`
- **Description**: Stops recording. For blue: waits until the stitching thread finishes writing up to the current index (acquires `file_data_finish_saving_lock`). For black/red: sets flag immediately. Closes the file, optionally deletes it if `abort_current_saving`. Resets UI to red "Not Recording".
- **Side effects**: Closes `file_data_save_id`, may `os.remove` the file, calls `define_name_txt_saved`
- **Calls**: `file_data_finish_saving_lock.acquire()` (blue), `define_name_txt_saved`
- **Called by**: `DMAMixin.master_DMA` (on `ref_test_step_forward_finish`)

---

### `browse_for_manual_modifications(self)`
- **Description**: Opens the current save folder in the OS file explorer.
- **Calls**: `os.startfile`
- **Called by**: `But_open_folder_for_manual_delete` command

---

### `browse_folder(self)`
- **Description**: Opens a folder picker dialog and updates `mastervar_default_folder`.
- **Calls**: `askdirectory`, `implement_folder_structure`
- **Called by**: `But_change_saving_folder` command

---

## 9. `mixins/hardware_mixin.py` : class `HardwareMixin`

### `Modify_pressure_sampling_rate(self, sampling_rate_micro)`
- **Description**: Sends command `'P' + zfill(4)` to all boards. Recomputes `plot_delta_nb_pts` and `plot_subsampling` if `sampling_rate_micro != 0`.
- **Inputs**: `sampling_rate_micro` (int, microseconds; 0 = stop)
- **Side effects**: Sends serial command to all boards, updates `self.plot_delta_nb_pts`, `self.plot_subsampling`, `self.config.starting_param.sampling_rate_micro`
- **Hardware coupling**: Direct. Command format `'PNNNN'` is firmware-specific.
- **Calls**: `link[bi].send(link[bi].tx_obj(command))`
- **Called by**: `Board_synchronize`, `_init_serial`, `exit_programm`

---

### `Board_synchronize(self)`
- **Description**: Full re-synchronization sequence: pauses sampling, drains in-flight packets, stops all threads, resets all data arrays and pointers, restarts threads, resumes sampling.
- **Side effects**: Clears all `data_summary` arrays, resets `stitched_data` (blue), creates and starts three threads
- **Calls**: `Modify_pressure_sampling_rate(0)`, `stop_threads`, `threading.Thread(...)`, `Modify_pressure_sampling_rate(sampling_rate_micro)`
- **Called by**: `start_DMA`, `_start_display_loops`, `exit_programm` (indirectly), `But_synchronize` command

---

### `Set_continous_rotation(self, percentage, delay_ms)`
- **Description**: Sends command `'R' + zfill(4)` to all boards. Updates direction label/color and button states. If `delay_ms > 0`, schedules an auto-stop.
- **Inputs**: `percentage` (int, âˆ’100 to 100), `delay_ms` (int)
- **Side effects**: Sends serial command, updates `self.continous_dir`, UI labels, schedules `after(delay_ms, stop)`
- **Hardware coupling**: Direct. Command format is firmware-specific.
- **Calls**: `link[bi].send(...)`, `self.after_cancel(...)`, `self.after(delay_ms, ...)`
- **Called by**: `DMAMixin.master_DMA` and all loading helpers, `_bind_buttons` (manual buttons)

---

### `Homing_continous_rotation(self)`
- **Description**: Sends command `'H0000'` to all boards to trigger firmware-controlled homing.
- **Hardware coupling**: Direct. Firmware must implement homing on receiving `'H'`.
- **Calls**: `link[bi].send(...)`
- **Called by**: `DMAMixin.master_DMA` (on `ref_test_step_homing_request`), `But_homing_continous_servo` command

---

### `Modify_both_valves(self, mode)`
- **Description**: Opens or closes both valves simultaneously.
- **Inputs**: `mode` (`'Open'` or `'Close'`)
- **Calls**: `Modify_valve_position('Open'/'Close', 0, speed)`, `Modify_valve_position('Open'/'Close', 1, speed)` (speed 100 for open, 3000 for close)
- **Called by**: `DMAMixin.master_DMA`, `exit_programm`, button commands

---

### `Modify_valve_position(self, mode, valve, speed)`
- **Description**: Selects a valve with command `'SNNNN'`, then sends open `'ONNNN'` or close `'CNNNN'` command with speed. Updates corresponding UI labels and buttons.
- **Inputs**: `mode` (`'Open'`/`'Close'`), `valve` (0=tissue, 1=ref), `speed` (int)
- **Hardware coupling**: Direct. Two-command protocol (select then act) is firmware-specific.
- **Calls**: `link[bi].send(...)` twice
- **Called by**: `Modify_both_valves`, button commands

---

### `define_pressure_offset(self)`
- **Description**: Computes mean pressure over the last `offset_nb_pts` samples and adds it to `link[bi].pressure_offset` (and `pressure_offset2` for black/red board 1).
- **Inputs**: `self.config.default_system.offset_nb_pts`, `link[bi].data_summary[:, 2]` (and `[:, 3]` for black/red)
- **Side effects**: Increments `link[bi].pressure_offset` (and `pressure_offset2`)
- **Calls**: `np.mean`
- **Called by**: `But_pressure_offset` and `But_pressure_offset_main` commands

---

## 10. `mixins/dma_mixin.py` : class `DMAMixin`

The DMA state machine is an event-driven loop scheduled via Tkinter `after()`. Every call to `master_DMA(mode)` checks the current `DMA_step_index` against known step constants, executes the matching block, possibly advances the index, then reschedules itself after `delay_wait` ms.

### Step Sequence Summary

```
valve_open0_request â†’ valve_open0_process
  - pause0_request
  - prehoming_request - prehoming_process - prehoming_finish (black/red only)
  - not_home_request - not_home_process - not_home_finish
  - pause1_request
  - homing_request - homing_process - homing_finish
  - pause2_request
  - valve_close_request - valve_close_process - valve_close_process2_
  - pause3_request
  - backward_request - backward_process - backward_finish
  - pause4_request
  - forward_request - forward_process - [forward_prefinish] - forward_finish
  - released_homing_process
  - pause5_request
  - valve_open_request - valve_open_process - valve_open_process2_
  - pause6_request
  - backward_end_request - backward_end_process - backward_end_finish
  - next_step_request  - (loop to not_home_request | end)
```

---

### `start_DMA(self, mode, step_index)`
- **Description**: Entry point for a DMA sequence. Initializes state, disables start button, synchronizes boards, kicks off `master_DMA`.
- **Inputs**: `mode` (`'Real test'` or `'Air tightness test'`), `step_index` (initial step constant)
- **Side effects**: Sets `ongoing_DMA=True`, resets test/cycle counters, sets `DMA_step_index`
- **Calls**: `define_name_txt_saved`, `Board_synchronize`, `master_DMA`
- **Called by**: `But_start_DMA`, `But_test_air_tighness` commands

---

### `f_pause_at_step_end(self)`
- **Description**: Toggles `self.pause_at_step_end`. Updates button background color.
- **Called by**: `But_pause_DMA_test_end` command; `master_DMA` (auto-reset after pause shown)

---

### `next_test_DMA(self, mode)`
- **Description**: Skips to end of current test (sets step to `forward_finish`). Optionally marks `abort_current_saving`.
- **Inputs**: `mode` (`'Delete current saving'` or None)
- **Calls**: `Set_continous_rotation`, `_disable_dma_buttons`
- **Called by**: `But_next_test_DMA` / `But_next_test_DMA_nodelete` commands

---

### `stop_DMA(self, mode)`
- **Description**: Jumps to `forward_finish` and advances the test counter past the limit to force end of sequence. Optionally marks `abort_current_saving`.
- **Calls**: `Set_continous_rotation`, `_disable_dma_buttons`
- **Called by**: `But_stop_DMA` / `But_stop_DMA_nodelete` commands

---

### `master_DMA_debug(self, mode)`
- **Description**: Schedules one `master_DMA` tick with a 50 ms delay. Used for debugging.
- **Calls**: `self.after(50, master_DMA)`

---

### `master_DMA(self, mode)`
- **Description**: Main state machine dispatcher. A large if-chain (intentionally non-exclusive) checks and handles each step. At the end, reschedules itself via `after(delay_wait, master_DMA)`.
- **Inputs**: `mode` (`'Real test'` or other)
- **Key side effects per step group**:
  - **valve_open0**: Opens valves if needed; enables stop/next buttons
  - **pause0:6**: Shows optional `messagebox.showinfo` dialogs
  - **prehoming**: Starts backward rotation until homing sensor activates, then stops (black/red)
  - **not_home**: Ensures homing sensor is NOT active (rotates away if needed)
  - **homing**: Calls `Homing_continous_rotation`, waits for sensor activation
  - **valve_close**: Closes valves, waits for movement complete
  - **backward**: Starts backward rotation, waits for motion start then stop
  - **forward_request**: Calls `start_record`, starts forward rotation
  - **forward_process**: Dispatches to loading mode helpers
  - **forward_finish**: Calls `stop_record`, stops rotation
  - **valve_open**: Reopens valves
  - **backward_end**: Returns to pre-homing position
  - **next_step**: Loops to next test or calls `_end_dma_sequence`
- **Calls**: `Modify_both_valves`, `Set_continous_rotation`, `Homing_continous_rotation`, `start_record`, `stop_record`, `set_plot_mode`, `_handle_loading_*`, `_end_dma_sequence`, `_disable_dma_buttons`, `messagebox.showinfo`
- **Called by**: `start_DMA`, self-rescheduling via `after(delay_wait, ...)`

---

### `_end_dma_sequence(self)`
- **Description**: Resets `ongoing_DMA`, restores start/stop buttons to normal state.
- **Side effects**: `ongoing_DMA = False`, re-enables `But_start_DMA`, `But_test_air_tighness`, `But_start_continous_servo`
- **Calls**: `_disable_dma_buttons`
- **Called by**: `master_DMA` (at `next_step_request`)

---

### `_disable_dma_buttons(self)`
- **Description**: Sets `But_next_test_DMA`, `But_stop_DMA`, `But_next_test_DMA_nodelete`, `But_stop_DMA_nodelete` all to `state='disabled'`.
- **Called by**: `next_test_DMA`, `stop_DMA`, `_end_dma_sequence`

---

### `_reset_invert_flags(self)`
- **Description**: Resets all four hysteresis flags to False.
- **Called by**: `_increment_cycle_and_check_finish`

---

### `_toggle_direction(self)`
- **Description**: Reverses servo direction by calling `Set_continous_rotation` with the opposite sign of `continous_rotation_speed`.
- **Inputs**: `self.continous_dir`
- **Calls**: `Set_continous_rotation`
- **Called by**: All `_handle_loading_*` helpers

---

### `_count_homing_cycles(self, home) - bool`
- **Description**: Debounce accumulator for the homing sensor. Returns True when a full cycle is confirmed (up > 10 AND down > 100 counts).
- **Inputs**: `home` ('1' or '0'), mutates `count_homing_sensor_up/down`
- **Returns**: `True` if cycle complete (and resets counters)
- **Called by**: `_handle_loading_shape_max`, `_handle_loading_pressure_max`

---

### `_increment_cycle_and_check_finish(self, mode, use_prefinish=False) - bool`
- **Description**: Increments `tkvar_current_cycle`. If the cycle limit is reached (`nb_tours_per_test` for real test, 2 otherwise), sets `DMA_step_index` to finish step and resets flags.
- **Inputs**: `mode`, `use_prefinish` (if True, goes to `forward_prefinish` instead of `forward_finish`)
- **Returns**: True if sequence should stop
- **Calls**: `_reset_invert_flags`
- **Called by**: All `_handle_loading_*` helpers

---

### `_handle_loading_shape_max(self, mode, home, cur_mat_p, cur_ref_p)`
- **Description**: Loading mode `'Full cycle up to Shape max'`. Computes instantaneous shape factor. Inverts direction when shape > `shape_max_cycle` or pressure > `pressure_max_cycle`. Counts homing cycles to determine end of test.
- **Inputs**: `cur_mat_p`, `cur_ref_p` (pressures in mbar), `home` (homing sensor state)
- **Calls**: `_toggle_direction`, `_count_homing_cycles`, `_increment_cycle_and_check_finish`
- **Called by**: `master_DMA` (during `forward_process`)

---

### `_handle_loading_pressure_max(self, mode, home, cur_mat_p)`
- **Description**: Loading mode `'Full cycle up to Pressure max'` (also default for non-real-test mode). Inverts direction at pressure threshold with hysteresis. Counts homing cycles.
- **Calls**: `_toggle_direction`, `_count_homing_cycles`, `_increment_cycle_and_check_finish`
- **Called by**: `master_DMA`

---

### `_handle_loading_dma_pressure(self, cur_mat_p)`
- **Description**: Loading mode `'DMA pressure'`. Bounces between `pressure_max_dma` and `pressure_min_dma`. Each min-crossing increments cycle count.
- **Calls**: `_toggle_direction`, `_increment_cycle_and_check_finish`
- **Called by**: `master_DMA`

---

### `_handle_loading_dma_pressure_change(self, cur_mat_p)`
- **Description**: Loading mode `'DMA pressure change'`. Like `_handle_loading_dma_pressure` but upper and lower bounds increase by `pressure_change_max/min` after each inversion (ramp protocol).
- **Inputs**: `self.pressure_max_dma_loc`, `self.pressure_min_dma_loc`
- **Side effects**: Increments `pressure_max_dma_loc` and `pressure_min_dma_loc`
- **Calls**: `_toggle_direction`, `_increment_cycle_and_check_finish`
- **Called by**: `master_DMA`

---

### `_handle_loading_dma_counts(self)`
- **Description**: Loading mode `'DMA Counts'`. Uses `config.arduino_general.count_sensor_number` (angular position 1:60) instead of pressure. Bounces between `count_max_cycle` and `count_min_cycle`.
- **Inputs**: `config.arduino_general.count_sensor_number`, `config.default_system.count_min/max_cycle`
- **Calls**: `_toggle_direction`, `_increment_cycle_and_check_finish`
- **Called by**: `master_DMA`

---

## 11. Hardware Coupling Summary

The following functions contain **direct hardware dependencies** that must be replaced for a new hardware target:

| Function | File | What to replace |
|---|---|---|
| `_init_serial` | main.py | `txfer.SerialTransfer(port, baud)`, `lnk.available()`, board-wait loop |
| `_read_a_packet_to_queue` | serial_mixin.py | Byte layout `rx_buff[:5 or :6]`, packet format |
| `th_consume_queue` | serial_mixin.py | Pressure decoding formula, status byte bit layout |
| `_update_sensor_counters` | serial_mixin.py | Encoder/homing logic, count wrapping at 60 |
| `_save_raw_to_file_if_recording` | serial_mixin.py | CSV column order (firmware-specific channels) |
| `th_stitching_values_for_thread` | serial_mixin.py | Two-board index synchronization (blue only) |
| `_save_stitched_to_file` | serial_mixin.py | CSV column order (stitched data) |
| `Modify_pressure_sampling_rate` | hardware_mixin.py | Command string `'PNNNN'` |
| `Set_continous_rotation` | hardware_mixin.py | Command string `'RNNNN'` |
| `Homing_continous_rotation` | hardware_mixin.py | Command string `'H0000'` |
| `Modify_valve_position` | hardware_mixin.py | Two-step command protocol `'SNNNN'` then `'O/CNNNN'` |

Functions that are **hardware-agnostic** and can be reused as-is:
`_end_dma_sequence`, `_disable_dma_buttons`, `_reset_invert_flags`, `_toggle_direction`, `_count_homing_cycles`, `_increment_cycle_and_check_finish`, all `_handle_loading_*` helpers, all plot helpers, all file helpers, all Tkinter variable management.

---

*End of document.*
