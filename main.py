#v5
import os
import sys
import time
import tkinter as tk
import tkinter.messagebox as messagebox
import threading
from threading import Lock
import queue
import numpy as np
from pySerialTransfer import pySerialTransfer as txfer
from functools import partial
import serial.tools.list_ports

from bin.data.config import Config
from interface_layout import Layout

from mixins.serial_mixin import SerialMixin
from mixins.plot_mixin import PlotMixin
from mixins.file_mixin import FileMixin
from mixins.hardware_mixin import HardwareMixin
from mixins.dma_mixin import DMAMixin


class Application(tk.Tk, SerialMixin, PlotMixin, FileMixin, HardwareMixin, DMAMixin):

    def __init__(self, master=None):
        super().__init__()
        self.system_color = 'red'  # 'black' ou 'red' uniquement (jamais 'blue')

        self._load_config()
        self._init_window()
        self._init_state_variables()
        self._init_tk_variables()
        self._bind_buttons()
        # NOTE : _init_serial() et _start_display_loops() ne sont plus appeles ici.
        # Ils sont declenches par le bouton "Connecter" du panel serie.

    # ------------------------------------------------------------------
    # Sous-methodes d'initialisation
    # ------------------------------------------------------------------

    def _load_config(self):
        """Charge le fichier INI correspondant a la couleur du systeme."""
        self.folder_ini = os.path.dirname(os.path.abspath(sys.argv[0]))
        config_map = {
            'black': 'config_black.ini',
            'red':   'config_red.ini',
        }
        self._config_file = os.path.join(
            self.folder_ini, 'bin', config_map[self.system_color])
        self._config_path_save = os.path.join(
            self.folder_ini, 'bin', 'config_expressions_for_pycharm.txt')
        self.time_program_start = time.time()
        self.config = Config(self._config_file, self._config_path_save)
        self.test_config_values()

    def _init_window(self):
        """Configure la fenetre Tk principale."""
        self.title(self.config.default_windows.titre_application)
        w = self.winfo_screenwidth()
        h = self.winfo_screenheight()
        self.geometry(f"{w}x{h - 100}+0+0")
        self.attributes('-topmost', True)
        self.attributes('-topmost', False)
        self.protocol("WM_DELETE_WINDOW", lambda: self.exit_programm())
        self.interface = Layout(self, self.config)
        self.interface.create_app_windows()

    def _init_state_variables(self):
        """Initialise toutes les variables d'etat runtime."""
        #    Connexion serie
        self._serial_connected = False
        self._serial_baud      = 115200   # baudrate de la carte unique

        #    Boucles d'affichage
        self.print_output_values = False
        self.after_call_alive    = False

        #    Verrous
        self.file_data_save_lock          = Lock()
        self.file_data_finish_saving_lock = Lock()
        self.change_step_index_lock       = Lock()

        #    Etat DMA
        self.DMA_step_index                   = 0
        self.ongoing_DMA                      = False
        self.pause_at_step_end                = False
        self.id_kill_continous_rotation       = 0
        self.id_kill_DMA_intermediary_process = 0
        self.invert_lately_max                = False
        self.invert_lately_min                = False
        self.invert_lately_middle             = False
        self.invert_lately_start              = False
        self.pressure_max_dma_loc = self.config.default_system.pressure_max_dma
        self.pressure_min_dma_loc = self.config.default_system.pressure_min_dma

        #    Servo / capteurs
        self.continous_dir                              = 0
        self.monitor_continous_recent_homing            = False
        self.monitor_continous_recent_count             = False
        self.monitor_continous_last_sensor_count_state  = 0
        self.monitor_continous_last_sensor_homing_state = 0
        self.count_homing_sensor_up                     = 0
        self.count_homing_sensor_down                   = 0

        #    Sauvegarde
        self.show_tissu            = True
        self.currently_saving_data = False
        self.save_data_up_to_nb    = None
        self.abort_current_saving  = False
        self.x_plot_length         = 0

        #    File d'attente serie (une seule carte)
        self.queue_serial_data = queue.Queue()

    def _init_tk_variables(self):
        """Cree et relie toutes les variables Tkinter aux widgets et a la config."""
        self.tkvar_manometer_pressure = tk.DoubleVar()
        self.interface.Label_manometer_value.config(
            textvariable=self.tkvar_manometer_pressure)

        self.tkvar_Shape = tk.DoubleVar()
        self.interface.Label_shape_value.config(textvariable=self.tkvar_Shape)

        self.tkvar_current_test = tk.IntVar()
        self.tkvar_current_test.set(1)
        self.interface.Label_compte_test.config(textvariable=self.tkvar_current_test)

        self.tkvar_current_cycle = tk.IntVar()
        self.tkvar_current_cycle.set(0)
        self.interface.Label_compte_tour.config(textvariable=self.tkvar_current_cycle)

        self._bind_entry_var(
            tracker_attr='tracker_entry_compte_tour',
            entry=self.interface.Entry_compte_tour,
            var_attr='mastervar_nb_tours_per_test',
            var_type=tk.IntVar,
            initial_value=int(self.config.starting_param.nb_tours_per_test),
            config_key="config.starting_param.nb_tours_per_test",
        )
        self._bind_entry_var(
            tracker_attr='tracker_entry_compte_test',
            entry=self.interface.Entry_compte_test,
            var_attr='mastervar_nb_tests_per_position',
            var_type=tk.IntVar,
            initial_value=int(self.config.starting_param.nb_tests_per_position),
            config_key="config.starting_param.nb_tests_per_position",
        )
        self._bind_entry_var(
            tracker_attr='tracker_entry_max_pressure',
            entry=self.interface.Entry_max_pressure,
            var_attr='mastervar_max_pressure',
            var_type=tk.IntVar,
            initial_value=int(self.config.default_system.pressure_max_cycle),
            config_key="config.default_system.pressure_max_cycle",
        )

        self.mastervar_diameter_aperture = tk.StringVar()
        self.mastervar_diameter_aperture.set(self.config.starting_param.diameter_aperture)
        self.mastervar_diameter_aperture.trace_add('write', lambda n, i, m:
            self.fun_modify_initial_value(
                n, i, m, "config.starting_param.diameter_aperture",
                self.mastervar_diameter_aperture, None, None))
        self.mastervar_diameter_aperture.trace_add(
            'write', lambda *a: self.define_name_txt_saved())
        self.interface.Combobox_diameter_aperture.config(
            textvariable=self.mastervar_diameter_aperture)

        self.mastervar_perform_calib = tk.BooleanVar()
        self.mastervar_perform_calib.set(bool(self.config.starting_param.perform_calib))
        self.mastervar_perform_calib.trace_add('write', lambda n, i, m:
            self.fun_modify_initial_value(
                n, i, m, "config.starting_param.perform_calib",
                self.mastervar_perform_calib, None, None))

        self.mastervar_default_folder = tk.StringVar()
        self.mastervar_default_folder.trace_add('write', lambda n, i, m:
            self.fun_modify_initial_value(
                n, i, m, "config.starting_param.default_folder",
                self.mastervar_default_folder, None, None))
        self.mastervar_default_folder.trace_add(
            'write', lambda *a: self.implement_folder_structure())
        self.interface.labelfile_path_name.config(
            textvariable=self.mastervar_default_folder)
        self.interface.But_change_saving_folder.config(command=self.browse_folder)
        self.mastervar_default_folder.set(
            str(self.config.starting_param.default_folder))

        self.mastervar_default_name_base = tk.StringVar()
        self.mastervar_default_name_base.trace_add('write', lambda n, i, m:
            self.fun_modify_initial_value(
                n, i, m, "config.starting_param.default_name_base",
                self.mastervar_default_name_base, None, None))
        self.mastervar_default_name_base.trace_add(
            'write', lambda *a: self.define_name_txt_saved())
        self.interface.Entry_root_name_saving.config(
            textvariable=self.mastervar_default_name_base)
        self.mastervar_default_name_base.set(
            str(self.config.starting_param.default_name_base))

        self._compute_aperture_values()

    def _bind_entry_var(self, tracker_attr, entry, var_attr, var_type,
                        initial_value, config_key):
        """Helper : relie un widget Entry a une cle de config via une variable maitre."""
        setattr(self, tracker_attr, False)
        entry.bind('<Key>', self.make_on_entry_modified_by_user(tracker_attr))
        var = var_type()
        var.set(initial_value)
        setattr(self, var_attr, var)
        var.trace_add(
            'write',
            lambda n, i, m, _v=var, _t=tracker_attr, _e=entry:
                self.fun_modify_initial_value(
                    n, i, m, config_key, _v,
                    entry_possible_origine=_t, entry_object=_e),
        )
        entry.config(textvariable=var)

    def _compute_aperture_values(self):
        """Calcule les constantes physiques dependant du diametre d'ouverture."""
        self.syringe_section_ratio = (
            self.config.default_system.syringe_section_mat_line
            / self.config.default_system.syringe_section_ref_line
        )
        diam = self.mastervar_diameter_aperture.get()
        if diam != 'Ref':
            for i, item in enumerate(self.config.default_system.diameter_aperture_list):
                if str(item) == diam:
                    index_diam = i
                    break
            self.cup_mat_circuit_volumes_ini = (
                self.config.default_system.cup_mat_circuit_volumes_ini[index_diam])
            self.V_ref_aperture = 4000 / 6 * np.pi * (float(diam) / 2000) ** 3 * 1e6
            self.continous_rotation_speed = (
                self.config.starting_param.continous_rotation_speed_list[index_diam])
        else:
            self.cup_mat_circuit_volumes_ini = (
                self.config.default_system.cup_mat_circuit_volumes_ini[-1])
            self.continous_rotation_speed = (
                self.config.starting_param.continous_rotation_speed_list[0])
            self.V_ref_aperture = 10_000_000

    def _bind_buttons(self):
        """Associe chaque bouton de l'interface a sa commande."""
        ui = self.interface

        #    Connexion serie
        ui.But_connect_serial.config(command=self.toggle_serial_connection)
        ui.But_refresh_ports.config(command=self.refresh_serial_ports)

        #    Dossier / fichiers
        ui.But_open_folder_for_manual_delete.config(
            command=self.browse_for_manual_modifications)
        ui.But_update_file_number.config(command=self.define_name_txt_saved)

        #    Enregistrement
        ui.But_start_record.config(command=self.start_record)
        ui.But_stop_record.config(command=self.stop_record)
        ui.But_change_test_mode.config(command=self.change_calibration_or_test)
        ui.But_change_plot_style.config(command=lambda: self.set_plot_mode(None))
        ui.But_switch_x_span.config(command=self.set_plot_length)
        ui.But_pressure_offset.config(command=self.define_pressure_offset)
        ui.But_pressure_offset_main.config(command=self.define_pressure_offset)
        ui.But_synchronize.config(command=self.Board_synchronize, state='disabled')
        ui.But_print_data.config(command=self.change_print_data_mode)

        #    Servo continu
        ui.But_start_continous_servo.config(
            command=lambda: self.Set_continous_rotation(self.continous_rotation_speed, 0))
        ui.But_start_continous_servo_rev.config(
            command=lambda: self.Set_continous_rotation(-self.continous_rotation_speed, 0))
        ui.But_stop_continous_servo.config(
            command=lambda: self.Set_continous_rotation(0, 0))
        ui.But_homing_continous_servo.config(
            command=self.Homing_continous_rotation, state='normal')
        ui.But_continous_servo_limited.config(
            command=lambda: self.Set_continous_rotation(100, 0), state='normal')

        #    Vannes
        ui.But_open_tissue_valve.config(
            command=lambda: self.Modify_valve_position('Open', 0, 100),
            state='disabled')
        ui.But_close_tissue_valve.config(
            command=lambda: self.Modify_valve_position('Close', 0, 1500))
        ui.But_open_ref_valve.config(
            command=lambda: self.Modify_valve_position('Open', 1, 100),
            state='disabled')
        ui.But_close_ref_valve.config(
            command=lambda: self.Modify_valve_position('Close', 1, 1500))
        ui.But_open_both_valve.config(
            command=lambda: self.Modify_both_valves('Open'))
        ui.But_close_both_valve.config(
            command=lambda: self.Modify_both_valves('Close'))

        #    File DMA
        step0 = self.config.convention.ref_test_step_valve_open0_request
        ui.But_start_DMA.config(
            command=lambda: self.start_DMA('Real test', step0), bg='Light blue')
        ui.But_test_air_tighness.config(
            command=lambda: self.start_DMA('Air tightness test', step0))
        ui.But_next_test_DMA.config(
            command=lambda: self.next_test_DMA('Delete current saving'),
            state='disabled')
        ui.But_stop_DMA.config(
            command=lambda: self.stop_DMA('Delete current saving'),
            state='disabled')
        ui.But_next_test_DMA_nodelete.config(
            command=lambda: self.next_test_DMA(None), state='disabled')
        ui.But_stop_DMA_nodelete.config(
            command=lambda: self.stop_DMA(None), state='disabled')
        ui.But_pause_DMA_test_end.config(command=self.f_pause_at_step_end)

    # ------------------------------------------------------------------
    # Gestion de la connexion serie
    # ------------------------------------------------------------------

    def toggle_serial_connection(self):
        """Bascule entre connexion et deconnexion selon l'etat courant."""
        if self._serial_connected:
            self.disconnect_serial()
        else:
            self.connect_serial()

    def connect_serial(self):
        """Lance la connexion serie depuis l'UI dans un thread dedie."""
        ui = self.interface

        port = ui.Combobox_port_board[1].get().strip()
        if not port:
            messagebox.showwarning(
                "Port manquant",
                "Veuillez selectionner un port COM pour la carte.")
            return
        self.config.arduino[1].port = port
        self._serial_baud = int(ui.Combobox_baudrate_board[1].get())

        ui.But_connect_serial.config(state='disabled', text='Connexion...')
        ui.But_refresh_ports.config(state='disabled')
        ui.Label_serial_status.config(text='Connexion en cours...', fg='orange')
        ui.Combobox_port_board[1].config(state='disabled')
        ui.Combobox_baudrate_board[1].config(state='disabled')
        self.update_idletasks()

        t = threading.Thread(target=self._connect_serial_thread, daemon=True)
        t.start()

    def _connect_serial_thread(self):
        """Thread worker : ouvre le port et attend sa disponibilite."""
        try:
            self._init_serial()
            self.after(0, self._on_serial_connected)
        except Exception as e:
            self.after(0, lambda err=str(e): self._on_serial_error(err))

    def _on_serial_connected(self):
        """Appele dans le thread principal quand la connexion reussit."""
        ui = self.interface
        self._serial_connected = True
        ui.But_connect_serial.config(state='normal', text='Deconnecter', bg='salmon')
        ui.But_refresh_ports.config(state='disabled')
        ui.Label_serial_status.config(text='Connecte', fg='green')
        ui.Combobox_port_board[1].config(state='disabled')
        ui.Combobox_baudrate_board[1].config(state='disabled')
        ui.notebook.select(ui.Tab_Process_overview)
        self._start_display_loops()

    def _on_serial_error(self, error_msg):
        """Appele dans le thread principal quand la connexion echoue."""
        ui = self.interface
        self._serial_connected = False
        ui.But_connect_serial.config(state='normal', text='Connecter', bg='light green')
        ui.But_refresh_ports.config(state='normal')
        ui.Label_serial_status.config(text='Erreur de connexion', fg='red')
        ui.Combobox_port_board[1].config(state='normal')
        ui.Combobox_baudrate_board[1].config(state='readonly')
        print(f"[SERIAL] Erreur : {error_msg}")
        messagebox.showerror(
            "Erreur de connexion serie",
            f"Impossible d'ouvrir le port serie.\n\n{error_msg}")

    def disconnect_serial(self):
        """Ferme proprement le port serie et reinitialise l'etat."""
        self.after_call_alive    = False
        self.print_output_values = False

        self.stop_threads()

        try:
            self.link.connection.flushInput()
            self.link.close()
        except Exception:
            pass
        self.link = None
        self._serial_connected = False

        ui = self.interface
        ui.But_connect_serial.config(state='normal', text='Connecter', bg='light green')
        ui.But_refresh_ports.config(state='normal')
        ui.Label_serial_status.config(text='Deconnecte', fg='red')
        ui.Combobox_port_board[1].config(state='normal')
        ui.Combobox_baudrate_board[1].config(state='readonly')
        print('[SERIAL] Deconnexion effectuee.')

    def refresh_serial_ports(self):
        """Rafraichit la liste des ports COM disponibles dans l'UI."""
        ports   = [p.device for p in serial.tools.list_ports.comports()]
        ui      = self.interface
        current = ui.Combobox_port_board[1].get()
        ui.Combobox_port_board[1]['values'] = ports
        if current in ports:
            ui.Combobox_port_board[1].set(current)
        elif ports:
            ui.Combobox_port_board[1].current(0)
        else:
            ui.Combobox_port_board[1].set('')
        print(f"[SERIAL] Ports disponibles : {ports}")

    # ------------------------------------------------------------------
    # Initialisation serie
    # ------------------------------------------------------------------

    def _init_serial(self):
        """Ouvre le port serie, configure la carte et attend sa disponibilite.
        Leve une exception en cas d'echec."""
        cfg  = self.config.arduino[1]
        baud = self._serial_baud
        cfg.factor = (cfg.pmax - cfg.pmin) / cfg.pressure_index_range

        try:
            self.link = txfer.SerialTransfer(cfg.port, baud=baud)
        except Exception as e:
            raise ConnectionError(f"Port {cfg.port} introuvable : {e}")

        lnk = self.link
        lnk.saving_data_lock          = Lock()
        lnk.data_summary              = np.zeros(
            (self.config.default_system.nb_lignes_data, 8))
        lnk.pressure_offset2          = 0
        lnk.arduino_board_last_status = [""]
        lnk.arduino_previous_index    = None
        lnk.error_read_nb             = 0
        lnk.missing_index             = 0
        lnk.last_saved_index          = -1
        lnk.nb_index_time             = 0
        lnk.pressure_offset           = 0
        lnk.waiting_for_serial        = 0
        lnk.last_ticked_time          = 0
        lnk.set_callbacks([self._read_a_packet_to_queue])
        lnk.open()
        print(f"[SERIAL] Port {cfg.port} ouverture demandee.")

        try:
            self.Modify_pressure_sampling_rate(
                self.config.starting_param.sampling_rate_micro)
        except Exception:
            pass

        print('[SERIAL] Attente de disponibilite de la carte...')
        while True:
            if lnk.available():
                print(f"[SERIAL] Port {cfg.port} disponible.")
                break
            elif int(lnk.status.value) == 1:
                lnk.waiting_for_serial += 1
                time.sleep(0.1)
                if lnk.waiting_for_serial > 100:
                    lnk.waiting_for_serial = 0
                    print('[SERIAL] Tentative de redemarrage de la carte...')
                    time.sleep(2)
        print('[SERIAL] Carte disponible.')

    def _start_display_loops(self):
        """Initialise la carte et demarre les boucles d'affichage periodiques."""
        self.Board_synchronize()
        self.print_output_values = True
        self.after_call_alive    = True
        self.plot_subsampling    = 3
        self.set_plot_mode(self.config.default_plot.ref_plot_vs_time)
        self.after(self.config.default_system.print_last_data_every_ms, self.print_data)
        self.after(self.config.default_system.update_graph_every_ms,    self.plot_data)

    # ------------------------------------------------------------------
    # Methodes utilitaires (transversales)
    # ------------------------------------------------------------------

    def test_config_values(self):
        if self.config.starting_param.sampling_rate_micro > 9999:
            self.config.starting_param.sampling_rate_micro = 9999
        self.plot_delta_nb_pts = self.config.default_plot.max_number_points
        self.config.starting_param.frequence_unused = (
            1_000_000 / self.config.starting_param.sampling_rate_micro)

    def make_on_entry_modified_by_user(self, tracking_var):
        """Retourne un callback clavier qui marque tracking_var a True."""
        def on_entry_modified(event):
            setattr(self, tracking_var, True)
        return on_entry_modified

    def fun_modify_initial_value(self, name, index, mode, adress_in_self_config,
                                 master_variable, entry_possible_origine, entry_object):
        """Synchronise une variable maitre Tkinter vers l'objet config."""
        attr_list = adress_in_self_config.split('.')
        adress    = self
        for attr in attr_list[:-1]:
            adress = getattr(adress, attr)

        is_entry_responsible = False
        if entry_possible_origine is not None:
            is_entry_responsible = getattr(self, entry_possible_origine)
            if is_entry_responsible:
                new_value = entry_object.get()
                setattr(self, entry_possible_origine, False)

        if not is_entry_responsible:
            try:
                new_value = master_variable.get()
                if not isinstance(new_value, (bool, str)) and new_value < 1:
                    new_value = 1
                    master_variable.set(1)
                setattr(adress, attr_list[-1], new_value)
                print(f"Config {adress_in_self_config} modifiee (sans Entry) -> {new_value}")
            except Exception:
                pass
        else:
            if new_value != '':
                new_value = int(new_value)
                if new_value < 1:
                    new_value = 1
                    master_variable.set(1)
                setattr(adress, attr_list[-1], new_value)
                master_variable.set(new_value)
                print(f"Config {adress_in_self_config} modifiee via Entry -> {new_value}")

        if adress_in_self_config == "config.starting_param.diameter_aperture":
            self._compute_aperture_values()

    def change_calibration_or_test(self):
        """Bascule entre le mode calibration et le mode test normal."""
        if self.mastervar_perform_calib.get():
            self.mastervar_perform_calib.set(False)
            self.interface.Frame_test_type.config(bg='Light Blue')
            self.interface.Label_test_type.config(text='Test', bg='Light Blue')
            self.interface.But_change_test_mode.config(text='->Calib mode')
        else:
            self.mastervar_perform_calib.set(True)
            self.interface.Frame_test_type.config(bg='Purple')
            self.interface.Label_test_type.config(text='Calib', bg='Purple')
            self.interface.But_change_test_mode.config(text='->Test mode')
        self.implement_folder_structure()
        self.define_name_txt_saved()

    def change_print_data_mode(self):
        self.print_output_values = not self.print_output_values

    def exit_programm(self):
        """Arret propre : stoppe le DMA, sauvegarde la config, ferme le port."""
        if self._serial_connected:
            if self.ongoing_DMA:
                self.stop_DMA(mode='Delete current saving')
                self.Modify_both_valves(mode='Open')
                time.sleep(2)
            self.Set_continous_rotation(percentage=0, delay_ms=0)
            self.Modify_pressure_sampling_rate(sampling_rate_micro=0)
            t = time.time() - self.time_program_start
            while t - self.link.last_ticked_time < 0.2:
                t = time.time() - self.time_program_start
            with self.file_data_save_lock:
                try:
                    self.file_data_save_id.close()
                except Exception:
                    pass
            self.after_call_alive = False
            self.stop_threads()
            self.link.connection.flushInput()
            self.link.close()

        self.config.save()
        self.destroy()
        print('Programm exit is clean')

    def next_expected_index(self, last_index):
        """Retourne le prochain index Arduino attendu dans le cycle 0-255."""
        if last_index == 255:
            return 0
        elif last_index < 256:
            return last_index + 1
        breakpoint()

    def developp_status(self):
        """Affiche le decodage lisible du status byte de la carte."""
        status = self.link.arduino_board_last_status
        conv   = self.config.convention
        checks = [
            (conv.line_status_ser1_valve_state,  str(int(conv.ref_vanne_opened)),
             'Valve servo 1', 'OPEN',     'Close'),
            (conv.line_status_ser2_valve_state,  str(int(conv.ref_vanne_opened)),
             'Valve servo 2', 'OPEN',     'Close'),
            (conv.line_status_ser1_valve_moving, str(int(conv.ref_vanne_moving)),
             'Valve servo 1', 'Moving',   'Static'),
            (conv.line_status_ser2_valve_moving, str(int(conv.ref_vanne_moving)),
             'Valve servo 2', 'Moving',   'Static'),
            (conv.line_status_opto_homing,       '1',
             'Homing sensor', 'activated', 'not activated'),
            (conv.line_status_opto_count,        '1',
             'Count sensor',  'activated', 'not activated'),
            (conv.line_status_constant_ser,      '1',
             'Cont. rotation', 'activated', 'not activated'),
        ]
        for line, ref, label, true_str, false_str in checks:
            print(f"{label} : {true_str if status[line] == ref else false_str}")


# ------------------------------------------------------------------
# Fonctions module
# ------------------------------------------------------------------

def read_a_packet_solo(app):
    if app.link.available():
        rec = app.link.rx_obj(
            obj_type=list, list_format='B', obj_byte_size=4, start_pos=0)
        print('Values %d %d %d %d ' % tuple(int(v) for v in rec))


def send_communication(app, lettre, valeur):
    command    = lettre + str(valeur).zfill(4)
    send_bytes = app.link.tx_obj(command)
    app.link.send(send_bytes)


def main():
    print('Debut code Python')
    app = Application()
    app.mainloop()


if __name__ == "__main__":
    main()