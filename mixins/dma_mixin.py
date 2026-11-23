#v5
from tkinter import messagebox


class DMAMixin:
    """Machine d'etats gerant la sequence complete d'un test DMA (carte unique)."""

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def start_DMA(self, mode, step_index):
        self.define_name_txt_saved()
        self.interface.But_start_DMA.config(state='disabled')
        self.interface.But_test_air_tighness.config(state='disabled')
        self.Board_synchronize()
        self.ongoing_DMA = True
        self.tkvar_current_test.set(1)
        self.tkvar_current_cycle.set(0)
        with self.change_step_index_lock:
            self.DMA_step_index = step_index
        self.master_DMA(mode)

    def f_pause_at_step_end(self):
        self.pause_at_step_end = not self.pause_at_step_end
        color = 'green' if self.pause_at_step_end else 'light gray'
        self.interface.But_pause_DMA_test_end.config(bg=color)

    def next_test_DMA(self, mode):
        if mode == 'Delete current saving':
            self.abort_current_saving = True
        with self.change_step_index_lock:
            self.DMA_step_index = self.config.convention.ref_test_step_forward_finish
        self.Set_continous_rotation(percentage=self.continous_rotation_speed, delay_ms=0)
        self._disable_dma_buttons()

    def stop_DMA(self, mode):
        if mode == 'Delete current saving':
            self.abort_current_saving = True
        with self.change_step_index_lock:
            self.DMA_step_index = self.config.convention.ref_test_step_forward_finish
            self.Set_continous_rotation(percentage=self.continous_rotation_speed, delay_ms=0)
        self.tkvar_current_test.set(self.mastervar_nb_tests_per_position.get() + 1)
        self._disable_dma_buttons()

    def master_DMA_debug(self, mode):
        self.id_kill_DMA_intermediary_process = self.after(50, lambda: self.master_DMA(mode))

    # ------------------------------------------------------------------
    # Machine d'etats principale
    # ------------------------------------------------------------------

    def master_DMA(self, mode):
        delay_wait = 50
        conv = self.config.convention
        lnk  = self.link   # single board; replaces self.link[bref] and self.link[btis]

        # ---- Ouverture des vannes (initialisation) ----
        if self.DMA_step_index == conv.ref_test_step_valve_open0_request:
            with lnk.saving_data_lock:
                v1 = lnk.arduino_board_last_status[conv.line_status_ser1_valve_state]
                v2 = lnk.arduino_board_last_status[conv.line_status_ser2_valve_state]
            if v1 == '1' or v2 == '1':
                self.Modify_both_valves(mode='Open')

            if mode == 'Real test':
                self.interface.But_next_test_DMA.config(state='normal')
                self.interface.But_stop_DMA.config(state='normal')
                self.interface.But_next_test_DMA_nodelete.config(state='normal')
                self.interface.But_stop_DMA_nodelete.config(state='normal')
            else:
                self.interface.But_next_test_DMA.config(state='disabled')
                self.interface.But_stop_DMA.config(state='normal')
                self.interface.But_next_test_DMA_nodelete.config(state='disabled')
                self.interface.But_stop_DMA_nodelete.config(state='normal')

            next_step = (conv.ref_test_step_valve_open0_process
                         if (v1 == '1' or v2 == '1')
                         else conv.ref_test_step_pause0_request)
            with self.change_step_index_lock:
                if self.DMA_step_index != conv.ref_test_step_forward_finish:
                    self.DMA_step_index = next_step

        if self.DMA_step_index == conv.ref_test_step_valve_open0_process:
            delay_wait = 1
            with lnk.saving_data_lock:
                v1 = lnk.arduino_board_last_status[conv.line_status_ser1_valve_state]
                v2 = lnk.arduino_board_last_status[conv.line_status_ser2_valve_state]
            if v1 == '1' and v2 == '1':
                with self.change_step_index_lock:
                    self.DMA_step_index = conv.ref_test_step_pause0_request

        # ---- Pause 0 ----
        if self.DMA_step_index == conv.ref_test_step_pause0_request:
            if conv.ref_activate_pause6_:
                messagebox.showinfo("Pause 0",
                    "Pause requise apres l'ouverture des vannes. Cliquer 'ok' pour continuer.")
            with self.change_step_index_lock:
                self.DMA_step_index = conv.ref_test_step_prehoming_request

        # ---- Pre-homing ----
        if self.DMA_step_index == conv.ref_test_step_prehoming_request:
            with lnk.saving_data_lock:
                home = lnk.arduino_board_last_status[conv.line_status_opto_homing]
            if home == '1':
                self.DMA_step_index = conv.ref_test_step_not_home_request
            else:
                direction = 100 if self.config.arduino_general.count_sensor_number > 30 else -99
                self.Set_continous_rotation(percentage=direction, delay_ms=0)
                self.DMA_step_index = conv.ref_test_step_prehoming_process

        if self.DMA_step_index == conv.ref_test_step_prehoming_process:
            with lnk.saving_data_lock:
                home = lnk.arduino_board_last_status[conv.line_status_opto_homing]
            if home == '1':
                self.Set_continous_rotation(percentage=0, delay_ms=0)
                self.DMA_step_index = conv.ref_test_step_prehoming_finish

        if self.DMA_step_index == conv.ref_test_step_prehoming_finish:
            with lnk.saving_data_lock:
                rot = lnk.arduino_board_last_status[conv.line_status_constant_ser]
            if rot == '0':
                self.DMA_step_index = conv.ref_test_step_not_home_request

        # ---- Liberer le capteur de homing ----
        if self.DMA_step_index == conv.ref_test_step_not_home_request:
            with lnk.saving_data_lock:
                home = lnk.arduino_board_last_status[conv.line_status_opto_homing]
            if home == '1':
                self.Set_continous_rotation(percentage=-99, delay_ms=1000)
                with self.change_step_index_lock:
                    if self.DMA_step_index != conv.ref_test_step_forward_finish:
                        self.DMA_step_index = conv.ref_test_step_not_home_process
            else:
                with self.change_step_index_lock:
                    if self.DMA_step_index != conv.ref_test_step_forward_finish:
                        self.DMA_step_index = conv.ref_test_step_pause1_request

        if self.DMA_step_index == conv.ref_test_step_not_home_process:
            delay_wait = 10
            with lnk.saving_data_lock:
                home = lnk.arduino_board_last_status[conv.line_status_opto_homing]
            if home == '0':
                self.Set_continous_rotation(percentage=0, delay_ms=0)
                with self.change_step_index_lock:
                    if self.DMA_step_index != conv.ref_test_step_forward_finish:
                        self.DMA_step_index = conv.ref_test_step_not_home_finish

        if self.DMA_step_index == conv.ref_test_step_not_home_finish:
            with lnk.saving_data_lock:
                rot = lnk.arduino_board_last_status[conv.line_status_constant_ser]
            if rot == '0':
                with self.change_step_index_lock:
                    if self.DMA_step_index != conv.ref_test_step_forward_finish:
                        self.DMA_step_index = conv.ref_test_step_pause1_request

        # ---- Pause 1 ----
        if self.DMA_step_index == conv.ref_test_step_pause1_request:
            if conv.ref_activate_pause1_:
                messagebox.showinfo("Pause 1",
                    "Pause requise une fois le homing sensor libere. Cliquer 'ok' pour continuer.")
            with self.change_step_index_lock:
                if self.DMA_step_index != conv.ref_test_step_forward_finish:
                    self.DMA_step_index = conv.ref_test_step_homing_request

        # ---- Homing ----
        if self.DMA_step_index == conv.ref_test_step_homing_request:
            self.Homing_continous_rotation()
            with self.change_step_index_lock:
                if self.DMA_step_index != conv.ref_test_step_forward_finish:
                    self.DMA_step_index = conv.ref_test_step_homing_process

        if self.DMA_step_index == conv.ref_test_step_homing_process:
            delay_wait = 10
            with lnk.saving_data_lock:
                home = lnk.arduino_board_last_status[conv.line_status_opto_homing]
            if home == '1':
                with self.change_step_index_lock:
                    if self.DMA_step_index != conv.ref_test_step_forward_finish:
                        self.DMA_step_index = conv.ref_test_step_homing_finish

        if self.DMA_step_index == conv.ref_test_step_homing_finish:
            with lnk.saving_data_lock:
                rot = lnk.arduino_board_last_status[conv.line_status_constant_ser]
            if rot == '0':
                with self.change_step_index_lock:
                    if self.DMA_step_index != conv.ref_test_step_forward_finish:
                        self.DMA_step_index = conv.ref_test_step_pause2_request

        # ---- Pause 2 ----
        if self.DMA_step_index == conv.ref_test_step_pause2_request:
            if conv.ref_activate_pause2_:
                messagebox.showinfo("Pause 2",
                    "Pause requise apres le homing. Cliquer 'ok' pour continuer.")
            with self.change_step_index_lock:
                if self.DMA_step_index != conv.ref_test_step_forward_finish:
                    self.DMA_step_index = conv.ref_test_step_valve_close_request

        # ---- Fermeture des vannes ----
        if self.DMA_step_index == conv.ref_test_step_valve_close_request:
            with lnk.saving_data_lock:
                v1 = lnk.arduino_board_last_status[conv.line_status_ser1_valve_state]
                v2 = lnk.arduino_board_last_status[conv.line_status_ser2_valve_state]
            if v1 == '0' or v2 == '0':
                self.Modify_both_valves(mode='Close')
                self.DMA_step_index = conv.ref_test_step_valve_close_process
            else:
                self.DMA_step_index = conv.ref_test_step_pause3_request

        if self.DMA_step_index == conv.ref_test_step_valve_close_process:
            delay_wait = 1
            with lnk.saving_data_lock:
                m1 = lnk.arduino_board_last_status[conv.line_status_ser1_valve_moving]
                m2 = lnk.arduino_board_last_status[conv.line_status_ser2_valve_moving]
            if m1 == '1' or m2 == '1':
                with self.change_step_index_lock:
                    if self.DMA_step_index != conv.ref_test_step_forward_finish:
                        self.DMA_step_index = conv.ref_test_step_valve_close_process2_

        if self.DMA_step_index == conv.ref_test_step_valve_close_process2_:
            delay_wait = 1
            with lnk.saving_data_lock:
                v1 = lnk.arduino_board_last_status[conv.line_status_ser1_valve_state]
                v2 = lnk.arduino_board_last_status[conv.line_status_ser2_valve_state]
                m1 = lnk.arduino_board_last_status[conv.line_status_ser1_valve_moving]
                m2 = lnk.arduino_board_last_status[conv.line_status_ser2_valve_moving]
            if v1 == '1' and v2 == '1' and m1 == '0' and m2 == '0':
                with self.change_step_index_lock:
                    if self.DMA_step_index != conv.ref_test_step_forward_finish:
                        self.DMA_step_index = conv.ref_test_step_pause3_request

        # ---- Pause 3 ----
        if self.DMA_step_index == conv.ref_test_step_pause3_request:
            if conv.ref_activate_pause3_:
                messagebox.showinfo("Pause 3",
                    "Pause requise apres fermeture des vannes. Cliquer 'ok' pour continuer.")
            with self.change_step_index_lock:
                if self.DMA_step_index != conv.ref_test_step_forward_finish:
                    self.DMA_step_index = conv.ref_test_step_backward_request

        # ---- Mouvement backward ----
        if self.DMA_step_index == conv.ref_test_step_backward_request:
            self.Set_continous_rotation(percentage=-self.continous_rotation_speed, delay_ms=1000)
            with self.change_step_index_lock:
                if self.DMA_step_index != conv.ref_test_step_forward_finish:
                    self.DMA_step_index = conv.ref_test_step_backward_process

        if self.DMA_step_index == conv.ref_test_step_backward_process:
            delay_wait = 1
            with lnk.saving_data_lock:
                rot = lnk.arduino_board_last_status[conv.line_status_constant_ser]
            if rot == '1':
                with self.change_step_index_lock:
                    if self.DMA_step_index != conv.ref_test_step_forward_finish:
                        self.DMA_step_index = conv.ref_test_step_backward_finish

        if self.DMA_step_index == conv.ref_test_step_backward_finish:
            delay_wait = 1
            with lnk.saving_data_lock:
                rot = lnk.arduino_board_last_status[conv.line_status_constant_ser]
            if rot == '0':
                with self.change_step_index_lock:
                    if self.DMA_step_index != conv.ref_test_step_forward_finish:
                        self.DMA_step_index = conv.ref_test_step_pause4_request

        # ---- Pause 4 ----
        if self.DMA_step_index == conv.ref_test_step_pause4_request:
            if conv.ref_activate_pause4_:
                messagebox.showinfo("Pause 4",
                    "Pause requise apres le mouvement backward. Cliquer 'ok' pour continuer.")
            with self.change_step_index_lock:
                if self.DMA_step_index != conv.ref_test_step_forward_finish:
                    self.DMA_step_index = conv.ref_test_step_forward_request

        # ---- Demarrage des cycles (forward) ----
        if self.DMA_step_index == conv.ref_test_step_forward_request:
            self.set_plot_mode(self.config.default_plot.ref_plot_one_vs_another)
            if mode == 'Real test':
                self.start_record()
            self.tkvar_current_cycle.set(0)
            self.Set_continous_rotation(percentage=self.continous_rotation_speed, delay_ms=0)
            with self.change_step_index_lock:
                if self.DMA_step_index != conv.ref_test_step_forward_finish:
                    self.DMA_step_index = conv.ref_test_step_forward_process

        # ---- Boucle de cycles ----
        if self.DMA_step_index == conv.ref_test_step_forward_process:
            delay_wait = 1
            with lnk.saving_data_lock:
                home      = lnk.arduino_board_last_status[conv.line_status_opto_homing]
                cur_mat_p = lnk.data_summary[lnk.last_saved_index, 2]
                cur_ref_p = lnk.data_summary[lnk.last_saved_index, 3]

            loading = self.interface.Combobox_loading_mode.get()
            if loading == 'Full cycle up to Shape max':
                self._handle_loading_shape_max(mode, home, cur_mat_p, cur_ref_p)
            if loading == 'Full cycle up to Pressure max' or mode != 'Real test':
                self._handle_loading_pressure_max(mode, home, cur_mat_p)
            if loading == 'DMA pressure':
                self._handle_loading_dma_pressure(cur_mat_p)
            if loading == 'DMA pressure change':
                self._handle_loading_dma_pressure_change(cur_mat_p)
            if loading == 'DMA Counts':
                self._handle_loading_dma_counts()

        if self.DMA_step_index == conv.ref_test_step_forward_prefinish:
            with lnk.saving_data_lock:
                home = lnk.arduino_board_last_status[conv.line_status_opto_homing]
            if home == '1':
                self.DMA_step_index = conv.ref_test_step_forward_finish

        # ---- Fin de cycles : arret de l'enregistrement ----
        if self.DMA_step_index == conv.ref_test_step_forward_finish:
            with lnk.saving_data_lock:
                home = lnk.arduino_board_last_status[conv.line_status_opto_homing]
            delay_wait = 1
            if home == '0':
                self.stop_record()
                with self.change_step_index_lock:
                    self.DMA_step_index = conv.ref_test_step_released_homing_process
                self.set_plot_mode(self.config.default_plot.ref_plot_vs_time)
                self.Set_continous_rotation(percentage=0, delay_ms=1000)

        if self.DMA_step_index == conv.ref_test_step_released_homing_process:
            delay_wait = 1
            with lnk.saving_data_lock:
                rot = lnk.arduino_board_last_status[conv.line_status_constant_ser]
            if rot == '0':
                with self.change_step_index_lock:
                    self.DMA_step_index = conv.ref_test_step_pause5_request

        # ---- Pause 5 ----
        if self.DMA_step_index == conv.ref_test_step_pause5_request:
            if conv.ref_activate_pause5_:
                messagebox.showinfo("Pause 5",
                    "Pause requise avant l'ouverture des vannes. Cliquer 'ok' pour continuer.")
            with self.change_step_index_lock:
                self.DMA_step_index = conv.ref_test_step_valve_open_request

        # ---- Reouverture des vannes (fin de test) ----
        if self.DMA_step_index == conv.ref_test_step_valve_open_request:
            with lnk.saving_data_lock:
                v1 = lnk.arduino_board_last_status[conv.line_status_ser1_valve_state]
                v2 = lnk.arduino_board_last_status[conv.line_status_ser2_valve_state]
            if v1 == '1' or v2 == '1':
                self.Modify_both_valves(mode='Open')
                with self.change_step_index_lock:
                    self.DMA_step_index = conv.ref_test_step_valve_open_process
            else:
                with self.change_step_index_lock:
                    self.DMA_step_index = conv.ref_test_step_pause6_request

        if self.DMA_step_index == conv.ref_test_step_valve_open_process:
            delay_wait = 1
            with lnk.saving_data_lock:
                m1 = lnk.arduino_board_last_status[conv.line_status_ser1_valve_moving]
                m2 = lnk.arduino_board_last_status[conv.line_status_ser2_valve_moving]
            if m1 == '1' or m2 == '1':
                with self.change_step_index_lock:
                    self.DMA_step_index = conv.ref_test_step_valve_open_process2_

        if self.DMA_step_index == conv.ref_test_step_valve_open_process2_:
            delay_wait = 1
            with lnk.saving_data_lock:
                v1 = lnk.arduino_board_last_status[conv.line_status_ser1_valve_state]
                v2 = lnk.arduino_board_last_status[conv.line_status_ser2_valve_state]
            if v1 == '0' and v2 == '0':
                with self.change_step_index_lock:
                    self.DMA_step_index = conv.ref_test_step_pause6_request

        # ---- Pause 6 ----
        if self.DMA_step_index == conv.ref_test_step_pause6_request:
            if conv.ref_activate_pause6_:
                messagebox.showinfo("Pause 6",
                    "Pause requise apres l'ouverture des vannes. Cliquer 'ok' pour continuer.")
            with self.change_step_index_lock:
                self.DMA_step_index = conv.ref_test_step_backward_end_request
                direction = 100 if self.config.arduino_general.count_sensor_number > 30 else -99
                self.Set_continous_rotation(percentage=direction, delay_ms=0)

        if self.DMA_step_index == conv.ref_test_step_backward_end_request:
            with lnk.saving_data_lock:
                home = lnk.arduino_board_last_status[conv.line_status_opto_homing]
            if home == '1':
                with self.change_step_index_lock:
                    self.DMA_step_index = conv.ref_test_step_backward_end_process
                self.Set_continous_rotation(percentage=-99, delay_ms=0)

        if self.DMA_step_index == conv.ref_test_step_backward_end_process:
            delay_wait = 1
            with lnk.saving_data_lock:
                home = lnk.arduino_board_last_status[conv.line_status_opto_homing]
            if home == '0':
                with self.change_step_index_lock:
                    self.DMA_step_index = conv.ref_test_step_backward_end_finish
                self.Set_continous_rotation(percentage=-99, delay_ms=100)

        if self.DMA_step_index == conv.ref_test_step_backward_end_finish:
            with lnk.saving_data_lock:
                rot = lnk.arduino_board_last_status[conv.line_status_constant_ser]
            if rot == '0':
                with self.change_step_index_lock:
                    self.DMA_step_index = conv.ref_test_step_next_step_request

        # ---- Passage au test suivant ou fin de sequence ----
        if self.DMA_step_index == conv.ref_test_step_next_step_request:
            delay_wait = 0
            if self.pause_at_step_end:
                self.f_pause_at_step_end()
                messagebox.showinfo("Pause", "Cliquer sur 'ok' pour continuer la serie de tests.")

            if mode == 'Real test':
                self.pressure_max_dma_loc = self.config.default_system.pressure_max_dma
                self.pressure_min_dma_loc = self.config.default_system.pressure_min_dma
                if self.tkvar_current_test.get() >= self.config.starting_param.nb_tests_per_position:
                    self._end_dma_sequence()
                else:
                    self.tkvar_current_test.set(self.tkvar_current_test.get() + 1)
                    with self.change_step_index_lock:
                        self.DMA_step_index = conv.ref_test_step_not_home_request
            else:
                self._end_dma_sequence()

        # Planifier le prochain tick
        try:
            self.after_cancel(self.id_kill_DMA_intermediary_process)
        except Exception:
            pass
        if self.after_call_alive and self.ongoing_DMA:
            self.id_kill_DMA_intermediary_process = self.after(
                delay_wait, lambda: self.master_DMA(mode))

    # ------------------------------------------------------------------
    # Helpers prives : fin de sequence et gestion des flags
    # ------------------------------------------------------------------

    def _end_dma_sequence(self):
        """Remet l'interface dans l'etat initial apres la fin de la sequence DMA."""
        self.tkvar_current_test.set(1)
        self.tkvar_current_cycle.set(1)
        self.ongoing_DMA = False
        self.interface.But_start_DMA.config(state='normal')
        self.interface.But_test_air_tighness.config(state='normal')
        self.interface.But_start_continous_servo.config(state='normal')
        self._disable_dma_buttons()

    def _disable_dma_buttons(self):
        for btn in ('But_next_test_DMA', 'But_stop_DMA',
                    'But_next_test_DMA_nodelete', 'But_stop_DMA_nodelete'):
            getattr(self.interface, btn).config(state='disabled')

    def _reset_invert_flags(self):
        self.invert_lately_max    = False
        self.invert_lately_min    = False
        self.invert_lately_middle = False
        self.invert_lately_start  = False

    def _toggle_direction(self):
        """Inverse le sens de rotation du servo continu."""
        if self.continous_dir == 1:
            self.Set_continous_rotation(percentage=-self.continous_rotation_speed, delay_ms=0)
        else:
            self.Set_continous_rotation(percentage=self.continous_rotation_speed, delay_ms=0)

    def _count_homing_cycles(self, home):
        """Incremente les compteurs du capteur de homing ; retourne True si un cycle est complet."""
        if home == '1':
            self.count_homing_sensor_up += 1
            if self.count_homing_sensor_up > 10 and self.count_homing_sensor_down > 100:
                self.count_homing_sensor_up   = 0
                self.count_homing_sensor_down = 0
                return True
        else:
            self.count_homing_sensor_down += 1
        return False

    def _increment_cycle_and_check_finish(self, mode, use_prefinish=False):
        """
        Incremente le compteur de cycles et declenche la fin si le quota est atteint.
        Retourne True si la sequence doit s'arreter.
        """
        self.tkvar_current_cycle.set(self.tkvar_current_cycle.get() + 1)
        limit = self.config.starting_param.nb_tours_per_test if mode == 'Real test' else 2
        if self.tkvar_current_cycle.get() > limit:
            finish = (self.config.convention.ref_test_step_forward_prefinish
                      if use_prefinish
                      else self.config.convention.ref_test_step_forward_finish)
            with self.change_step_index_lock:
                self.DMA_step_index = finish
            self._reset_invert_flags()
            return True
        return False

    # ------------------------------------------------------------------
    # Helpers prives : modes de chargement
    # ------------------------------------------------------------------

    def _handle_loading_shape_max(self, mode, home, cur_mat_p, cur_ref_p):
        sys = self.config.default_system
        Vgaz     = cur_mat_p * self.cup_mat_circuit_volumes_ini / (
            sys.athmopheric_pressure - cur_mat_p)
        Vsyringe = (self.syringe_section_ratio * cur_ref_p * sys.ref_circuit_volumes_ini) / (
            sys.athmopheric_pressure - cur_ref_p)
        shape    = (Vsyringe - Vgaz) / self.V_ref_aperture

        if (shape > sys.shape_max_cycle or cur_mat_p > sys.pressure_max_cycle) \
                and not self.invert_lately_max:
            self.invert_lately_max = True
            self._toggle_direction()
            print('Inversion : depassement de shape ou de pression')

        if shape < (sys.shape_max_cycle - sys.delta_shape_hysteresis_cycle) \
                and cur_mat_p < sys.pressure_max_cycle - 10 \
                and self.invert_lately_max:
            self.invert_lately_max = False

        if self._count_homing_cycles(home):
            self._increment_cycle_and_check_finish(mode, use_prefinish=True)

    def _handle_loading_pressure_max(self, mode, home, cur_mat_p):
        sys = self.config.default_system
        if cur_mat_p > sys.pressure_max_cycle and not self.invert_lately_max:
            self.invert_lately_max = True
            self._toggle_direction()

        if cur_mat_p < sys.pressure_max_cycle and self.invert_lately_max:
            self.invert_lately_max = False

        if self._count_homing_cycles(home):
            self._increment_cycle_and_check_finish(mode, use_prefinish=False)

    def _handle_loading_dma_pressure(self, cur_mat_p):
        sys = self.config.default_system
        if cur_mat_p > sys.pressure_max_dma and not self.invert_lately_max:
            self.invert_lately_max    = True
            self.invert_lately_middle = True
            self._toggle_direction()

        if cur_mat_p < (sys.pressure_max_dma - sys.delta_pressure_hysteresis_cycle) \
                and self.invert_lately_max:
            self.invert_lately_max = False

        if self.invert_lately_middle:
            if cur_mat_p < sys.pressure_min_dma and not self.invert_lately_min:
                self.invert_lately_min = True
                self._toggle_direction()
                finished = self._increment_cycle_and_check_finish('Real test', use_prefinish=True)
                if finished:
                    self._toggle_direction()
            if cur_mat_p > sys.pressure_min_dma and self.invert_lately_min:
                self.invert_lately_min = False

    def _handle_loading_dma_pressure_change(self, cur_mat_p):
        sys = self.config.default_system
        if cur_mat_p > self.pressure_max_dma_loc and not self.invert_lately_max:
            self.invert_lately_max    = True
            self.invert_lately_middle = True
            self._toggle_direction()
            self.pressure_max_dma_loc += sys.pressure_change_max

        if cur_mat_p < (self.pressure_max_dma_loc - sys.delta_pressure_hysteresis_cycle) \
                and self.invert_lately_max:
            self.invert_lately_max = False

        if self.invert_lately_middle:
            if cur_mat_p < self.pressure_min_dma_loc and not self.invert_lately_min:
                self.invert_lately_min = True
                self._toggle_direction()
                self.pressure_min_dma_loc += sys.pressure_change_min
                finished = self._increment_cycle_and_check_finish('Real test', use_prefinish=True)
                if finished:
                    self._toggle_direction()
            if cur_mat_p > self.pressure_min_dma_loc and self.invert_lately_min:
                self.invert_lately_min = False

    def _handle_loading_dma_counts(self):
        sys   = self.config.default_system
        count = self.config.arduino_general.count_sensor_number

        if not self.invert_lately_start:
            if count < sys.count_min_cycle and self.continous_dir == 1:
                self.invert_lately_start = True

        if self.invert_lately_start:
            if count >= sys.count_max_cycle and not self.invert_lately_max:
                self.invert_lately_max    = True
                self.invert_lately_middle = True
                self._toggle_direction()

            if count < sys.count_max_cycle and self.invert_lately_max:
                self.invert_lately_max = False

            if self.invert_lately_middle:
                if count <= sys.count_min_cycle and not self.invert_lately_min:
                    self.invert_lately_min = True
                    self._toggle_direction()
                    finished = self._increment_cycle_and_check_finish('Real test', use_prefinish=True)
                    if finished:
                        self._toggle_direction()

                if count > sys.count_min_cycle and self.invert_lately_min and self.invert_lately_middle:
                    self.invert_lately_min = False