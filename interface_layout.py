#v5
import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import serial.tools.list_ports


class Layout():
    def __init__(self, app, config):
        super().__init__()
        self.config = config
        self.app = app

    def create_app_windows(self):
        ##############################################################################
        ########################## TAB CREATION ######################################
        ##############################################################################
        notebook = ttk.Notebook()
        self.notebook = notebook
        notebook.pack(fill='both', expand=True)

        Tab_Process_overview    = ttk.Frame(notebook)
        Tab_Additionnal_buttons = ttk.Frame(notebook)
        self.Tab_Process_overview    = Tab_Process_overview
        self.Tab_Additionnal_buttons = Tab_Additionnal_buttons

        notebook.add(Tab_Process_overview,    text=self.config.default_windows.onglet_1_titre)
        notebook.add(Tab_Additionnal_buttons, text=self.config.default_windows.onglet_2_titre)

        _lf_kwargs   = dict(padx=6, pady=4, bd=3, font='Helvetica 10 bold')
        _pack_kwargs = dict(side=tk.TOP, anchor=tk.N, fill=tk.X, padx=6, pady=(4, 2))

        ##############################################################################
        ############ Tab: Direct Controls ############################################
        ##############################################################################

        canvas_dc    = tk.Canvas(Tab_Additionnal_buttons)
        scrollbar_dc = tk.Scrollbar(Tab_Additionnal_buttons, orient="vertical",
                                    command=canvas_dc.yview)
        Frame_DC_inner = tk.Frame(canvas_dc)

        Frame_DC_inner.bind(
            "<Configure>",
            lambda e: canvas_dc.configure(scrollregion=canvas_dc.bbox("all")))

        canvas_dc.create_window((0, 0), window=Frame_DC_inner, anchor="nw")
        canvas_dc.configure(yscrollcommand=scrollbar_dc.set)
        scrollbar_dc.pack(side=tk.RIGHT, fill=tk.Y)
        canvas_dc.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # -----------------------------------------------------------------------
        #   PANEL 1 : Serial Connection  (single board)
        # -----------------------------------------------------------------------
        BAUDRATES      = ['1000000']
        available_ports = [p.device for p in serial.tools.list_ports.comports()]

        Frame_Serial_Connection = tk.LabelFrame(
            Frame_DC_inner, text=" Serial Connection ", **_lf_kwargs)
        Frame_Serial_Connection.pack(**_pack_kwargs)

        # Keep index-1 lists so main.py can reference [1] without change
        self.Combobox_port_board     = [None, None]
        self.Combobox_baudrate_board = [None, None]

        row = tk.Frame(Frame_Serial_Connection)
        row.pack(side=tk.TOP, anchor=tk.W, fill=tk.X, pady=2)

        tk.Label(row, text="  Board : COM Port :",
                 width=22, anchor='e').pack(side=tk.LEFT)

        self.Combobox_port_board[1] = ttk.Combobox(row, values=available_ports, width=10)
        self.Combobox_port_board[1].pack(side=tk.LEFT, padx=5)

        cfg_port = getattr(self.config.arduino[1], 'port', '')
        if cfg_port in available_ports:
            self.Combobox_port_board[1].set(cfg_port)
        elif available_ports:
            self.Combobox_port_board[1].current(0)

        tk.Label(row, text="  Baudrate :", anchor='e').pack(side=tk.LEFT)
        self.Combobox_baudrate_board[1] = ttk.Combobox(
            row, values=BAUDRATES, width=9, state='readonly')
        self.Combobox_baudrate_board[1].pack(side=tk.LEFT, padx=5)
        self.Combobox_baudrate_board[1].set('1000000')

        self.But_refresh_ports = tk.Button(
            row, text="Refresh ports", bd=3, width=13)
        self.But_refresh_ports.pack(side=tk.LEFT, padx=(2, 4))

        self.But_connect_serial = tk.Button(
            row, text="Connect",
            bd=4, width=10, bg='light green', font='Helvetica 10 bold')
        self.But_connect_serial.pack(side=tk.LEFT, padx=4)

        self.Label_serial_status = tk.Label(
            row, text="Disconnected", fg='red',
            font='Helvetica 10 bold', width=16, anchor='w')
        self.Label_serial_status.pack(side=tk.LEFT, padx=6)

        # -----------------------------------------------------------------------
        #   PANEL 2 : Pressure
        # -----------------------------------------------------------------------
        Frame_Pressure = tk.LabelFrame(
            Frame_DC_inner, text=" Pressure ", **_lf_kwargs)
        Frame_Pressure.pack(**_pack_kwargs)

        self.But_pressure_offset = tk.Button(
            Frame_Pressure, padx=0, pady=0, width=50,
            text='Define pressure offset (mean over last 5 seconds)', bd=4)
        self.But_pressure_offset.pack(side=tk.TOP, anchor=tk.N, pady=2)

        # -----------------------------------------------------------------------
        #   PANEL 3 : Debug  (Synchronize button kept but disabled)
        # -----------------------------------------------------------------------
        Frame_Sync_Debug = tk.LabelFrame(
            Frame_DC_inner, text=" Debug ", **_lf_kwargs)
        Frame_Sync_Debug.pack(**_pack_kwargs)

        row_sync = tk.Frame(Frame_Sync_Debug)
        row_sync.pack(side=tk.TOP, anchor=tk.N, pady=2)

        self.But_synchronize = tk.Button(
            row_sync, padx=0, pady=0, width=24,
            text='Synchronize (N/A)', bd=4, state='disabled')
        self.But_synchronize.pack(side=tk.LEFT, padx=(2, 4))

        self.But_print_data = tk.Button(
            row_sync, padx=0, pady=0, width=24,
            text='Print data in console  on/off', bd=4)
        self.But_print_data.pack(side=tk.LEFT, padx=2)

        # -----------------------------------------------------------------------
        #   PANEL 4 : Recording
        # -----------------------------------------------------------------------
        Frame_Record = tk.LabelFrame(
            Frame_DC_inner, text="Rec ON", **_lf_kwargs)
        Frame_Record.pack(**_pack_kwargs)

        row_rec = tk.Frame(Frame_Record)
        row_rec.pack(side=tk.TOP, anchor=tk.N, pady=2)

        self.But_start_record = tk.Button(
            row_rec, padx=0, pady=0, width=22,
            text='Start recording to file', bd=4)
        self.But_start_record.pack(side=tk.LEFT, padx=(2, 4))

        self.But_stop_record = tk.Button(
            row_rec, padx=0, pady=0, width=16,
            text='Stop recording', bd=4)
        self.But_stop_record.pack(side=tk.LEFT, padx=2)

        # -----------------------------------------------------------------------
        #   PANEL 5 : Continuous Rotation
        # -----------------------------------------------------------------------
        Frame_Rotation = tk.LabelFrame(
            Frame_DC_inner, text=" Continuous Rotation ", **_lf_kwargs)
        Frame_Rotation.pack(**_pack_kwargs)

        row_speed_override = tk.Frame(Frame_Rotation)
        row_speed_override.pack(side=tk.TOP, anchor=tk.N, pady=(4, 2))

        tk.Label(row_speed_override, text="Speed override (%):",
                 anchor='e').pack(side=tk.LEFT, padx=(4, 2))

        self.Entry_manual_rotation_speed = tk.Entry(
            row_speed_override, width=6, justify='center')
        self.Entry_manual_rotation_speed.pack(side=tk.LEFT, padx=2)
        self.Entry_manual_rotation_speed.insert(0, "100")
        
        self.var_override_speed = tk.BooleanVar(value=False)
        self.Checkbutton_override_speed = tk.Checkbutton(
            row_speed_override, text="Enable", variable=self.var_override_speed)
        self.Checkbutton_override_speed.pack(side=tk.LEFT, padx=(2, 6))
        
        self.But_continous_servo_limited = tk.Button(
            Frame_Rotation, padx=0, pady=0, width=30,
            text='Rotate 100%', bd=4)
        self.But_continous_servo_limited.pack(side=tk.TOP, anchor=tk.N, pady=2)
        
        self.But_start_continous_servo = tk.Button(
            Frame_Rotation, padx=0, pady=0, width=30,
            text='Start cycling', bd=4)
        self.But_start_continous_servo.pack(side=tk.TOP, anchor=tk.N, pady=2)

        self.But_start_continous_servo_rev = tk.Button(
            Frame_Rotation, padx=0, pady=0, width=30,
            text='Start cycling (reverse)', bd=4)
        self.But_start_continous_servo_rev.pack(side=tk.TOP, anchor=tk.N, pady=2)

        self.But_stop_continous_servo = tk.Button(
            Frame_Rotation, padx=0, pady=0, width=30,
            text='Stop cycling', bd=4)
        self.But_stop_continous_servo.pack(side=tk.TOP, anchor=tk.N, pady=2)

        self.But_homing_continous_servo = tk.Button(
            Frame_Rotation, padx=0, pady=0, width=30,
            text='Homing', bd=4)
        self.But_homing_continous_servo.pack(side=tk.TOP, anchor=tk.N, pady=2)



        # -----------------------------------------------------------------------
        #   PANEL 6 : Valves
        # -----------------------------------------------------------------------
        Frame_Valves = tk.LabelFrame(
            Frame_DC_inner, text=" Valves ", **_lf_kwargs)
        Frame_Valves.pack(**_pack_kwargs)

        Frame_Valves_both = tk.Frame(Frame_Valves)
        Frame_Valves_both.pack(side=tk.TOP, anchor=tk.N, fill=tk.X, pady=(4, 2))
        tk.Label(Frame_Valves_both, text="Both circuits:", width=22,
                 anchor='e').pack(side=tk.LEFT)
        self.But_open_both_valve = tk.Button(
            Frame_Valves_both, padx=0, pady=0, width=20,
            text='Open both valves', bd=4)
        self.But_open_both_valve.pack(side=tk.LEFT, padx=4)
        self.But_close_both_valve = tk.Button(
            Frame_Valves_both, padx=0, pady=0, width=20,
            text='Close both valves', bd=4)
        self.But_close_both_valve.pack(side=tk.LEFT, padx=4)

        Frame_Valves_tissue = tk.Frame(Frame_Valves)
        Frame_Valves_tissue.pack(side=tk.TOP, anchor=tk.N, fill=tk.X, pady=2)
        tk.Label(Frame_Valves_tissue, text="Tissue circuit:", width=22,
                 anchor='e').pack(side=tk.LEFT)
        self.But_open_tissue_valve = tk.Button(
            Frame_Valves_tissue, padx=0, pady=0, width=20,
            text='Open tissue valve', bd=4)
        self.But_open_tissue_valve.pack(side=tk.LEFT, padx=4)
        self.But_close_tissue_valve = tk.Button(
            Frame_Valves_tissue, padx=0, pady=0, width=20,
            text='Close tissue valve', bd=4)
        self.But_close_tissue_valve.pack(side=tk.LEFT, padx=4)

        Frame_Valves_ref = tk.Frame(Frame_Valves)
        Frame_Valves_ref.pack(side=tk.TOP, anchor=tk.N, fill=tk.X, pady=2)
        tk.Label(Frame_Valves_ref, text="Reference circuit:", width=22,
                 anchor='e').pack(side=tk.LEFT)
        self.But_open_ref_valve = tk.Button(
            Frame_Valves_ref, padx=0, pady=0, width=20,
            text='Open reference valve', bd=4)
        self.But_open_ref_valve.pack(side=tk.LEFT, padx=4)
        self.But_close_ref_valve = tk.Button(
            Frame_Valves_ref, padx=0, pady=0, width=20,
            text='Close reference valve', bd=4)
        self.But_close_ref_valve.pack(side=tk.LEFT, padx=4)

        # -----------------------------------------------------------------------
        #   Back navigation button
        # -----------------------------------------------------------------------
        previous_tab_button = tk.Button(
            Frame_DC_inner, padx=0, pady=4, width=20,
            text='<< Back to Measure',
            command=lambda: notebook.select(Tab_Process_overview), bd=4)
        previous_tab_button.pack(side=tk.TOP, anchor=tk.NW, padx=8, pady=(8, 4))

        ##############################################################################
        ############ Tab: Process Overview ###########################################
        ##############################################################################

        Frame_top_band = tk.Frame(Tab_Process_overview)
        Frame_top_band.pack(side=tk.TOP, fill=tk.X, padx=0, pady=0)

        Frame_bottom = tk.Frame(Tab_Process_overview)
        Frame_bottom.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        Frame_PO_left_container = tk.Frame(Frame_bottom)
        Frame_PO_left_container.pack(side=tk.LEFT, fill=tk.Y)

        canvas_po    = tk.Canvas(Frame_PO_left_container, width=340)
        scrollbar_po = tk.Scrollbar(Frame_PO_left_container, orient="vertical",
                                    command=canvas_po.yview)
        Frame_PO_inner = tk.Frame(canvas_po)

        Frame_PO_inner.bind(
            "<Configure>",
            lambda e: canvas_po.configure(scrollregion=canvas_po.bbox("all")))

        canvas_po.create_window((0, 0), window=Frame_PO_inner, anchor="nw")
        canvas_po.configure(yscrollcommand=scrollbar_po.set)
        scrollbar_po.pack(side=tk.RIGHT, fill=tk.Y)
        canvas_po.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        Frame_graphic = tk.Frame(
            Frame_bottom, padx=2, pady=2, borderwidth=2,
            highlightbackground="blue", highlightthickness=2)
        Frame_graphic.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        ##############################################################################
        #### TOP BAND : System Status
        ##############################################################################

        Frame_System_Status = tk.LabelFrame(
            Frame_top_band, text="", padx=2, pady=0, bd=0, font='Helvetica 10 bold')
        Frame_System_Status.pack(side=tk.LEFT, anchor=tk.W, padx=2, pady=0)

        Frame_SS_row = tk.Frame(Frame_System_Status)
        Frame_SS_row.pack(side=tk.TOP, fill=tk.X, pady=0)

        _ind_w, _ind_h = 78, 28
        _ind_lbl_kw    = dict(font='Helvetica 8 bold')

        self.Frame_rotation_servo = tk.Frame(
            Frame_SS_row, highlightbackground='black', highlightthickness=2,
            width=_ind_w, height=_ind_h)
        self.Frame_rotation_servo.pack_propagate(0)
        self.Frame_rotation_servo.pack(side=tk.LEFT, padx=1)
        self.Label_rotation_servo = tk.Label(
            self.Frame_rotation_servo, text='Cyclic OFF',
            width=10, bg='Green', **_ind_lbl_kw)
        self.Label_rotation_servo.pack(expand=True)
        self.Frame_rotation_servo.config(bg='Green')

        self.Frame_tissue_valve = tk.Frame(
            Frame_SS_row, highlightbackground='black', highlightthickness=2,
            width=_ind_w, height=_ind_h)
        self.Frame_tissue_valve.pack_propagate(0)
        self.Frame_tissue_valve.pack(side=tk.LEFT, padx=1)
        self.Label_tissue_valve = tk.Label(
            self.Frame_tissue_valve, text='T Valve O',
            width=10, bg='Green', **_ind_lbl_kw)
        self.Label_tissue_valve.pack(expand=True)
        self.Frame_tissue_valve.config(bg='Green')

        self.Frame_secondary_valve = tk.Frame(
            Frame_SS_row, highlightbackground='black', highlightthickness=2,
            width=_ind_w, height=_ind_h)
        self.Frame_secondary_valve.pack_propagate(0)
        self.Frame_secondary_valve.pack(side=tk.LEFT, padx=1)
        self.Label_secondary_valve = tk.Label(
            self.Frame_secondary_valve, text='R Valve O',
            width=10, bg='Green', **_ind_lbl_kw)
        self.Label_secondary_valve.pack(expand=True)
        self.Frame_secondary_valve.config(bg='Green')

        self.Frame_continuous_servo_direction = tk.Frame(
            Frame_SS_row, highlightbackground='black', highlightthickness=2,
            width=26, height=_ind_h)
        self.Frame_continuous_servo_direction.pack_propagate(0)
        self.Frame_continuous_servo_direction.pack(side=tk.LEFT, padx=1)
        self.Label_continuous_servo_direction = tk.Label(
            self.Frame_continuous_servo_direction, text='F',
            width=2, bg='Cyan', font='Helvetica 9 bold')
        self.Label_continuous_servo_direction.pack(expand=True)
        self.Frame_continuous_servo_direction.config(bg='Cyan')

        tk.Frame(Frame_SS_row, width=8, height=_ind_h).pack(side=tk.LEFT)

        self.But_change_test_mode = tk.Button(
            Frame_SS_row, width=12, height=1, padx=3, pady=2, bd=4)
        self.But_change_test_mode.pack(side=tk.LEFT, padx=(0, 1))

        self.Frame_test_type = tk.Frame(
            Frame_SS_row, highlightbackground='black', highlightthickness=2,
            width=_ind_w, height=_ind_h)
        self.Frame_test_type.pack_propagate(0)
        self.Frame_test_type.pack(side=tk.LEFT, padx=1)
        self.Label_test_type = tk.Label(
            self.Frame_test_type, width=10, font='Helvetica 8 bold')
        self.Label_test_type.pack(expand=True)
        if not self.config.starting_param.perform_calib:
            self.Label_test_type.config(text='Test', bg='Light Blue')
            self.Frame_test_type.config(bg='Light Blue')
            self.But_change_test_mode.config(text='->Calib mode')
        else:
            self.Label_test_type.config(text='Calib', bg='Purple')
            self.Frame_test_type.config(bg='Purple')
            self.But_change_test_mode.config(text='->Test mode')

        self.Frame_recording_status = tk.Frame(
            Frame_SS_row, highlightbackground='black', highlightthickness=2,
            width=_ind_w, height=_ind_h)
        self.Frame_recording_status.pack_propagate(0)
        self.Frame_recording_status.pack(side=tk.LEFT, padx=1)
        self.Label_recording_status = tk.Label(
            self.Frame_recording_status, text='Rec OFF',
            width=10, bg='Red', font='Helvetica 8 bold')
        self.Label_recording_status.pack(expand=True)
        self.Frame_recording_status.config(bg='Red')

        self.Frame_homesensor_status = tk.Frame(
            Frame_SS_row, highlightbackground='black', highlightthickness=2,
            width=26, height=_ind_h)
        self.Frame_homesensor_status.pack_propagate(0)
        self.Frame_homesensor_status.pack(side=tk.LEFT, padx=1)
        self.Frame_homesensor_status.config(bg='Green')
        self.Label_countsensor = tk.Label(
            self.Frame_homesensor_status, text=' ',
            width=2, bg='Green', font='Helvetica 9 bold')
        self.Label_countsensor.pack(expand=True)

        # Measurements merged into the same row
        tk.Frame(Frame_SS_row, width=10, height=_ind_h).pack(side=tk.LEFT)

        tk.Label(Frame_SS_row, text='Tissue pressure :', width=16,
                 anchor='e').pack(side=tk.LEFT)
        self.Label_manometer_value = tk.Label(
            Frame_SS_row, text='00', justify='center', width=5,
            font='Helvetica 12 bold')
        self.Label_manometer_value.pack(side=tk.LEFT)
        tk.Label(Frame_SS_row, text=' mbar').pack(side=tk.LEFT)

        tk.Label(Frame_SS_row, text='    Tissue shape :', width=16,
                 anchor='e').pack(side=tk.LEFT)
        self.Label_shape_value = tk.Label(
            Frame_SS_row, text='00', justify='center', width=5,
            font='Helvetica 12 bold')
        self.Label_shape_value.pack(side=tk.LEFT)

        ##############################################################################
        #### LEFT SCROLLABLE COLUMN
        ##############################################################################

        # --- Test Parameters ---
        Frame_Test_Params = tk.LabelFrame(
            Frame_PO_inner, text=" Test Parameters ", **_lf_kwargs)
        Frame_Test_Params.pack(**_pack_kwargs)

        row_tc = tk.Frame(Frame_Test_Params)
        row_tc.pack(side=tk.TOP, anchor=tk.W, fill=tk.X, pady=1)
        tk.Label(row_tc, text='Current test N :', width=18, anchor='e').pack(side=tk.LEFT)
        self.Label_compte_test = tk.Label(row_tc, width=3)
        self.Label_compte_test.pack(side=tk.LEFT)
        tk.Label(row_tc, text=' / ').pack(side=tk.LEFT)
        self.Entry_compte_test = tk.Entry(row_tc, width=3)
        self.Entry_compte_test.pack(side=tk.LEFT)
        tk.Label(row_tc, text=' tests').pack(side=tk.LEFT)

        row_cc = tk.Frame(Frame_Test_Params)
        row_cc.pack(side=tk.TOP, anchor=tk.W, fill=tk.X, pady=1)
        tk.Label(row_cc, text='Current cycle N :', width=18, anchor='e').pack(side=tk.LEFT)
        self.Label_compte_tour = tk.Label(row_cc, width=3)
        self.Label_compte_tour.pack(side=tk.LEFT)
        tk.Label(row_cc, text=' / ').pack(side=tk.LEFT)
        self.Entry_compte_tour = tk.Entry(row_cc, width=3)
        self.Entry_compte_tour.pack(side=tk.LEFT)
        tk.Label(row_cc, text=' cycles').pack(side=tk.LEFT)

        row_d = tk.Frame(Frame_Test_Params)
        row_d.pack(side=tk.TOP, anchor=tk.W, fill=tk.X, pady=1)
        tk.Label(row_d, text='Aperture diameter :', width=18, anchor='e').pack(side=tk.LEFT)
        self.Combobox_diameter_aperture = ttk.Combobox(
            row_d, values=self.config.default_system.diameter_aperture_list,
            width=5, justify='right')
        self.Combobox_diameter_aperture.pack(side=tk.LEFT)
        tk.Label(row_d, text=' mm').pack(side=tk.LEFT)

        row_p = tk.Frame(Frame_Test_Params)
        row_p.pack(side=tk.TOP, anchor=tk.W, fill=tk.X, pady=1)
        tk.Label(row_p, text='Max pressure limit :', width=18, anchor='e').pack(side=tk.LEFT)
        self.Entry_max_pressure = tk.Entry(row_p, width=5)
        self.Entry_max_pressure.pack(side=tk.LEFT)
        tk.Label(row_p, text=' mbar').pack(side=tk.LEFT)

        row_lm = tk.Frame(Frame_Test_Params)
        row_lm.pack(side=tk.TOP, anchor=tk.W, fill=tk.X, pady=1)
        tk.Label(row_lm, text='Loading mode :', width=18, anchor='e').pack(side=tk.LEFT)
        self.Combobox_loading_mode = ttk.Combobox(
            row_lm, values=self.config.default_system.loading_mode[1:],
            width=18, justify='left')
        self.Combobox_loading_mode.pack(side=tk.LEFT)
        self.Combobox_loading_mode.current(0)

        # --- File Management ---
        Frame_File_Mgmt = tk.LabelFrame(
            Frame_PO_inner, text=" File Management ", **_lf_kwargs)
        Frame_File_Mgmt.pack(**_pack_kwargs)

        row_f1 = tk.Frame(Frame_File_Mgmt)
        row_f1.pack(side=tk.TOP, anchor=tk.W, fill=tk.X, pady=1)
        tk.Label(row_f1, text='Saving folder :', width=13, anchor='e').pack(side=tk.LEFT)
        self.labelfile_path_name = tk.Label(
            row_f1, text="C:/current_saving_folder",
            anchor='w', justify='left', wraplength=190)
        self.labelfile_path_name.pack(side=tk.LEFT, fill=tk.X, expand=True)

        row_f2 = tk.Frame(Frame_File_Mgmt)
        row_f2.pack(side=tk.TOP, anchor=tk.W, fill=tk.X, pady=1)
        self.But_change_saving_folder = tk.Button(
            row_f2, text='Change folder', border=2, bd=4, width=14)
        self.But_change_saving_folder.pack(side=tk.LEFT, padx=(0, 3))
        self.But_open_folder_for_manual_delete = tk.Button(
            row_f2, text='Open in explorer', border=2, bd=4, width=14)
        self.But_open_folder_for_manual_delete.pack(side=tk.LEFT)

        row_n1 = tk.Frame(Frame_File_Mgmt)
        row_n1.pack(side=tk.TOP, anchor=tk.W, fill=tk.X, pady=(3, 0))
        tk.Label(row_n1, text='Name base :', width=13, anchor='e').pack(side=tk.LEFT)
        self.Entry_root_name_saving = tk.Entry(
            row_n1, textvariable=self.config.starting_param.default_name_base, width=20)
        self.Entry_root_name_saving.pack(side=tk.LEFT)

        row_n2 = tk.Frame(Frame_File_Mgmt)
        row_n2.pack(side=tk.TOP, anchor=tk.W, fill=tk.X, pady=(0, 1))
        tk.Label(row_n2, text='Save as :', width=13, anchor='e').pack(side=tk.LEFT)
        self.Label_full_name_saving = tk.Label(
            row_n2, text='Final_full_name_saving', anchor='w')
        self.Label_full_name_saving.pack(side=tk.LEFT)

        # --- Test Control ---
        Frame_Test_Control = tk.LabelFrame(
            Frame_PO_inner, text=" Test Control ", **_lf_kwargs)
        Frame_Test_Control.pack(**_pack_kwargs)

        Frame_TC_setup = tk.LabelFrame(
            Frame_Test_Control, text=" Setup ",
            padx=4, pady=3, bd=2, font='Helvetica 9 bold')
        Frame_TC_setup.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(3, 1))

        self.But_update_file_number = tk.Button(
            Frame_TC_setup, text='Update file number',
            padx=0, pady=0, width=28, bd=4, relief="ridge")
        self.But_update_file_number.pack(side=tk.TOP, anchor=tk.N, pady=1)

        self.But_pressure_offset_main = tk.Button(
            Frame_TC_setup, text='Set pressure offset',
            padx=0, pady=0, width=28, bd=4)
        self.But_pressure_offset_main.pack(side=tk.TOP, anchor=tk.N, pady=1)

        self.But_test_air_tighness = tk.Button(
            Frame_TC_setup, text='Test air tightness (2 cycles)',
            padx=0, pady=0, width=28, bd=4)
        self.But_test_air_tighness.pack(side=tk.TOP, anchor=tk.N, pady=1)

        Frame_TC_run = tk.LabelFrame(
            Frame_Test_Control, text=" Run ",
            padx=4, pady=3, bd=2, font='Helvetica 9 bold')
        Frame_TC_run.pack(side=tk.TOP, fill=tk.X, padx=4, pady=1)

        self.But_start_DMA = tk.Button(
            Frame_TC_run, text='Start test queue',
            padx=0, pady=0, width=28, bd=4,
            bg='light green', font='Helvetica 9 bold')
        self.But_start_DMA.pack(side=tk.TOP, anchor=tk.N, pady=1)

        self.But_pause_DMA_test_end = tk.Button(
            Frame_TC_run, text='Pause at end of current test',
            padx=0, pady=0, width=28, bd=4, bg='light gray')
        self.But_pause_DMA_test_end.pack(side=tk.TOP, anchor=tk.N, pady=1)

        row_skip = tk.Frame(Frame_TC_run)
        row_skip.pack(side=tk.TOP, anchor=tk.CENTER, pady=1)
        self.But_next_test_DMA = tk.Button(
            row_skip, text='Skip test', padx=0, pady=0, width=12, bd=4)
        self.But_next_test_DMA.pack(side=tk.LEFT, padx=(0, 2))
        self.But_next_test_DMA_nodelete = tk.Button(
            row_skip, text='Skip (keep file)', padx=0, pady=0, width=14, bd=4)
        self.But_next_test_DMA_nodelete.pack(side=tk.LEFT)

        row_stop = tk.Frame(Frame_TC_run)
        row_stop.pack(side=tk.TOP, anchor=tk.CENTER, pady=1)
        self.But_stop_DMA = tk.Button(
            row_stop, text='Stop queue', padx=0, pady=0, width=12, bd=4,
            bg='light coral', font='Helvetica 9 bold')
        self.But_stop_DMA.pack(side=tk.LEFT, padx=(0, 2))
        self.But_stop_DMA_nodelete = tk.Button(
            row_stop, text='Stop (keep file)', padx=0, pady=0, width=14, bd=4,
            bg='light coral')
        self.But_stop_DMA_nodelete.pack(side=tk.LEFT)

        Frame_TC_plot = tk.LabelFrame(
            Frame_Test_Control, text=" Plot ",
            padx=4, pady=3, bd=2, font='Helvetica 9 bold')
        Frame_TC_plot.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(1, 3))

        row_plot = tk.Frame(Frame_TC_plot)
        row_plot.pack(side=tk.TOP, fill=tk.X, pady=1)
        self.But_change_plot_style = tk.Button(
            row_plot, text='Switch plot type', padx=0, pady=0, width=13, bd=4)
        self.But_change_plot_style.pack(side=tk.LEFT, padx=(0, 2))
        self.But_switch_x_span = tk.Button(
            row_plot, text='Plot over 5 s', padx=0, pady=0, width=13, bd=4)
        self.But_switch_x_span.pack(side=tk.LEFT)

        next_tab_button = tk.Button(
            Frame_PO_inner, padx=0, pady=3, width=20,
            command=lambda: notebook.select(Tab_Additionnal_buttons),
            text='Direct controls >>', bd=4)
        next_tab_button.pack(side=tk.TOP, anchor=tk.NE, padx=6, pady=(3, 6))

        ##############################################################################
        #### Matplotlib graph  (single board: 4 lines + 1 dummy at index 0)
        ##############################################################################
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.fig.ax = self.fig.add_subplot(111)

        self.fig.list_lines = [0] * 5
        lines, = self.fig.ax.plot([0, 1], [0, 1], color='blue')
        self.fig.list_lines[1] = lines
        lines, = self.fig.ax.plot([0, 1], [0, 1], color='orange')
        self.fig.list_lines[2] = lines
        lines, = self.fig.ax.plot([0, 1], [0, 1], color='red')
        self.fig.list_lines[3] = lines
        lines, = self.fig.ax.plot([0, 1], [0, 1], color='orange')
        self.fig.list_lines[4] = lines

        self.fig.canvas = FigureCanvasTkAgg(self.fig, master=Frame_graphic)
        self.fig.canvas.get_tk_widget().pack(expand=tk.TRUE, fill=tk.BOTH)
        self.fig.canvas.draw()

        ##############################################################################
        #### Default tab: Direct Controls (serial connection)
        ##############################################################################
        notebook.select(Tab_Additionnal_buttons)