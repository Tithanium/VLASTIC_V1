#v5

import math
import time
import threading
import numpy as np


class HardwareMixin:
    """ContrÃ´le du hardware : servo continu, vannes, offset pression, initialisation."""

    def Modify_pressure_sampling_rate(self, sampling_rate_micro):
        """Envoie la frequence d'echantillonnage a la carte Arduino."""
        if sampling_rate_micro != 0:
            self.plot_delta_nb_pts = int(
                1_000_000 * self.config.default_plot.temps_plot_s / sampling_rate_micro
            )
            facteur = self.plot_delta_nb_pts / self.config.default_plot.max_number_points
            self.plot_subsampling = math.ceil(facteur) if facteur > 1 else 1
            self.config.starting_param.sampling_rate_micro = sampling_rate_micro

        print(f"Requires pressure serial transfer every {sampling_rate_micro} micro seconds.")
        command = 'P' + str(sampling_rate_micro).zfill(4)
        self.link.send(self.link.tx_obj(command))

    def Board_synchronize(self):
        """Stoppe les threads, reinitialise le buffer et redemarre la capture serie."""
        self.Modify_pressure_sampling_rate(sampling_rate_micro=0)

        # Attendre que le dernier paquet en transit soit traite
        t = time.time() - self.time_program_start
        while t - self.link.last_ticked_time < 0.2:
            t = time.time() - self.time_program_start

        self.stop_threads()

        # Creation des threads
        self.ticking_serials_thread = threading.Thread(
            target=self._th_extract_data_from_serials, name="Ticking_serial")
        self.consume_queue_thread = threading.Thread(
            target=self.th_consume_queue, name="Consume_queue_serial")

        # Reinitialisation du buffer de donnees
        with self.link.saving_data_lock:
            self.link.data_summary = np.zeros(
                (self.config.default_system.nb_lignes_data, 8))
            self.link.error_read_nb   = 0
            self.link.last_saved_index = -1
            self.link.nb_index_time   = 0
            print("Table for board is erased.")

        # Demarrage des threads
        self.consume_queue_thread.start()
        self.ticking_serials_thread.start()

        self.Modify_pressure_sampling_rate(self.config.starting_param.sampling_rate_micro)

    def Set_continous_rotation(self, percentage, delay_ms):
        """Envoie une commande de rotation continue et met a jour l'interface."""
        if self.interface.var_override_speed.get():  # True / False
            raw_val = self.interface.Entry_manual_rotation_speed.get()
            if percentage == 0:
                override_speed = 0                                         # Stop toujours respecté
            else:
                sign = 1 if percentage > 0 else -1                         # Sens préservé
                override_speed = (int(raw_val) * sign
                                if raw_val.isdigit() and 0 <= int(raw_val) <= 100
                                else percentage)
                
            command = 'R' + str(override_speed).zfill(4)
            self.link.send(self.link.tx_obj(command))

            if abs(override_speed) > 5:
                self.interface.Label_rotation_servo.config(text='Cyclic ON', bg='Red')
                self.interface.Frame_rotation_servo.config(bg='Red')
                self.interface.But_start_continous_servo.config(state='disable')
                self.interface.But_continous_servo_limited.config(state='disable')
                self.interface.But_homing_continous_servo.config(state='disable')
                if override_speed > 0:
                    self.continous_dir = 1
                    self.interface.Label_continuous_servo_direction.config(text='F', bg='Cyan')
                    self.interface.Frame_continuous_servo_direction.config(bg='Cyan')
                    print('Forward request to continous motor')
                else:
                    self.continous_dir = -1
                    self.interface.Label_continuous_servo_direction.config(text='B', bg='Magenta')
                    self.interface.Frame_continuous_servo_direction.config(bg='Magenta')
                    print('Backward request to continous motor')
            else:
                self.interface.Label_rotation_servo.config(text='Cyclic OFF', bg='Green')
                self.interface.Frame_rotation_servo.config(bg='Green')
                self.interface.But_start_continous_servo.config(state='normal')
                self.interface.But_continous_servo_limited.config(state='normal')
                self.interface.But_homing_continous_servo.config(state='normal')
                self.continous_dir = 0
                
        else: 
            command = 'R' + str(percentage).zfill(4)
            self.link.send(self.link.tx_obj(command))

            if abs(percentage) > 5:
                self.interface.Label_rotation_servo.config(text='Cyclic ON', bg='Red')
                self.interface.Frame_rotation_servo.config(bg='Red')
                self.interface.But_start_continous_servo.config(state='disable')
                self.interface.But_continous_servo_limited.config(state='disable')
                self.interface.But_homing_continous_servo.config(state='disable')
                if percentage > 0:
                    self.continous_dir = 1
                    self.interface.Label_continuous_servo_direction.config(text='F', bg='Cyan')
                    self.interface.Frame_continuous_servo_direction.config(bg='Cyan')
                    print('Forward request to continous motor')
                else:
                    self.continous_dir = -1
                    self.interface.Label_continuous_servo_direction.config(text='B', bg='Magenta')
                    self.interface.Frame_continuous_servo_direction.config(bg='Magenta')
                    print('Backward request to continous motor')
            else:
                self.interface.Label_rotation_servo.config(text='Cyclic OFF', bg='Green')
                self.interface.Frame_rotation_servo.config(bg='Green')
                self.interface.But_start_continous_servo.config(state='normal')
                self.interface.But_continous_servo_limited.config(state='normal')
                self.interface.But_homing_continous_servo.config(state='normal')
                self.continous_dir = 0

        try:
            self.after_cancel(self.id_kill_continous_rotation)
        except Exception:
            pass

        if self.after_call_alive and delay_ms > 0:
            self.id_kill_continous_rotation = self.after(
                delay_ms, lambda: self.Set_continous_rotation(percentage=0, delay_ms=0))

        self.monitor_continous_recent_count  = False
        self.monitor_continous_recent_homing = False

    def Homing_continous_rotation(self):
        """Envoie la commande de homing a la carte."""
        command = 'H' + str(0).zfill(4)
        self.link.send(self.link.tx_obj(command))

    def Modify_both_valves(self, mode):
        """Ouvre ou ferme les deux vannes simultanement."""
        if mode == 'Open':
            self.Modify_valve_position('Open', 0, 100)
            self.Modify_valve_position('Open', 1, 100)
        else:
            self.Modify_valve_position('Close', 0, 3000)
            self.Modify_valve_position('Close', 1, 3000)

    def Modify_valve_position(self, mode, valve, speed):
        """Ouvre ou ferme une vanne specifique et met a jour l'interface."""
        # Selectionne la vanne
        command = 'S' + str(valve).zfill(4)
        self.link.send(self.link.tx_obj(command))

        # Envoie la commande Open ou Close
        letter  = 'O' if mode == 'Open' else 'C'
        command = letter + str(speed).zfill(4)
        self.link.send(self.link.tx_obj(command))

        # Met a jour les labels et boutons correspondants
        if valve == 0:
            frame          = self.interface.Frame_tissue_valve
            label          = self.interface.Label_tissue_valve
            btn_open       = self.interface.But_open_tissue_valve
            btn_close      = self.interface.But_close_tissue_valve
            label_open_txt  = 'T ValveO'
            label_close_txt = 'T Valve C'
        else:
            frame          = self.interface.Frame_secondary_valve
            label          = self.interface.Label_secondary_valve
            btn_open       = self.interface.But_open_ref_valve
            btn_close      = self.interface.But_close_ref_valve
            label_open_txt  = 'R ValveO'
            label_close_txt = 'R Valve C'

        if mode == 'Open':
            frame.config(bg='Green')
            label.config(text=label_open_txt, bg='Green')
            btn_open.config(state='disabled')
            btn_close.config(state='normal')
        else:
            frame.config(bg='Red')
            label.config(text=label_close_txt, bg='Red')
            btn_close.config(state='disabled')
            btn_open.config(state='normal')

    def define_pressure_offset(self):
        """Calcule et applique l'offset de pression sur les derniers points acquis."""
        nb_pts = self.config.default_system.offset_nb_pts

        with self.link.saving_data_lock:
            if self.link.last_saved_index > nb_pts:
                stop = self.link.last_saved_index
                self.link.pressure_offset  += np.mean(
                    self.link.data_summary[stop - nb_pts:stop, 2])
                self.link.pressure_offset2 += np.mean(
                    self.link.data_summary[stop - nb_pts:stop, 3])
            else:
                print(f"Offset non modifie : attendez {nb_pts} points.")