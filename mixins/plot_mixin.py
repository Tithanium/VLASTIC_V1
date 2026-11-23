#v5
class PlotMixin:
    """Mise a jour des valeurs affichees et du graphique matplotlib (carte unique)."""

    def update_values(self):
        """Met a jour les variables Tkinter affichant les pressions et la forme."""
        lnk = self.link
        if lnk is not None:
            with lnk.saving_data_lock:
                idx    = lnk.last_saved_index
                p_mat  = lnk.data_summary[idx, 2]
                p_ref  = lnk.data_summary[idx, 3]
                status = lnk.arduino_board_last_status

            # Manometer display
            if self.show_tissu:
                self.tkvar_manometer_pressure.set(int(p_mat * 100) / 100)
            else:
                self.tkvar_manometer_pressure.set(int(p_ref * 100) / 100)

            # Shape
            sys = self.config.default_system
            V_gaz    = p_mat * self.cup_mat_circuit_volumes_ini / (
                sys.athmopheric_pressure - p_mat)
            V_syr    = (self.syringe_section_ratio * p_ref
                        * sys.ref_circuit_volumes_ini
                        / (sys.athmopheric_pressure - p_ref))
            self.tkvar_Shape.set(int((V_syr - V_gaz) / self.V_ref_aperture * 100) / 100)

            # Homing sensor indicator
            if status != ['']:
                home_st = status[self.config.convention.line_status_opto_homing]
            else:
                home_st = '0'

            self.interface.Label_countsensor.config(
                text=str(self.config.arduino_general.count_sensor_number))

            color = 'Red' if home_st == '1' else 'Green'
            if self.interface.Frame_homesensor_status.cget('bg') != color:
                self.interface.Frame_homesensor_status.config(bg=color)
                self.interface.Label_countsensor.config(bg=color)

    def print_data(self):
        """Appele periodiquement : met a jour les valeurs et affiche en console."""
        self.update_values()
        if self.print_output_values:
            try:
                lnk = self.link
                print('Board status : %s. Index %d , P1 %f mbar , P2 %f mbar' % (
                    lnk.arduino_board_last_status,
                    lnk.data_summary[lnk.last_saved_index, 1],
                    lnk.data_summary[lnk.last_saved_index, 2],
                    lnk.data_summary[lnk.last_saved_index, 3]))
                print('Missing index: %d.' % lnk.missing_index)
            except Exception:
                print('No data read in queue')

        if self.after_call_alive:
            self.after(self.config.default_system.print_last_data_every_ms, self.print_data)

    def set_plot_mode(self, plot_mode_choice):
        """Definit le mode d'affichage du graphique."""
        cfg = self.config.default_plot

        if plot_mode_choice is None:
            if self.plot_output_values == cfg.ref_plot_one_vs_another:
                plot_mode_choice = cfg.ref_plot_vs_time
            elif self.plot_output_values == cfg.ref_plot_vs_time:
                plot_mode_choice = cfg.ref_plot_one_vs_another
            else:
                plot_mode_choice = cfg.ref_plot_vs_time

        ax    = self.interface.fig.ax
        lines = self.interface.fig.list_lines

        labels = {
            cfg.ref_plot_vs_index:                ('Arduino index (0-255)', 'Pressure (mbar)'),
            cfg.ref_plot_vs_time:                 ('Time (s)',              'Pressure (mbar)'),
            cfg.ref_plot_temp_vs_time_sensor_ref: ('Time (s)',              'Ref circuit Pressure (mbar) and Temperature (C)'),
            cfg.ref_plot_temp_vs_time_sensor_mat: ('Time (s)',              'Mat circuit Pressure (mbar) or Temperature (C)'),
            cfg.ref_plot_temp_vs_time:            ('Time (s)',              'Temperature (C)'),
        }

        if plot_mode_choice in labels:
            self.plot_output_values = plot_mode_choice
            xlabel, ylabel = labels[plot_mode_choice]
            ax.set_xlabel(xlabel, labelpad=0)
            ax.set_ylabel(ylabel, labelpad=0)
            lines[1].set_color(cfg.color_plot_board[1])

        elif plot_mode_choice == cfg.ref_plot_one_vs_another:
            self.plot_output_values = cfg.ref_plot_one_vs_another
            lines[3].set_xdata([]); lines[3].set_ydata([])
            lines[4].set_xdata([]); lines[4].set_ydata([])
            lines[1].set_color('green')
            ax.set_xlabel('Pressure in reference line (mbar)', labelpad=0)
            ax.set_ylabel('Pressure in material line (mbar)',  labelpad=0)

    def set_plot_length(self):
        """Bascule entre fenetre glissante de 5 s et vue complete."""
        if self.x_plot_length == 0:
            self.x_plot_length = int(5_000_000 / self.config.starting_param.sampling_rate_micro)
            self.interface.But_switch_x_span.config(
                text='Plot over %s s' % int(self.config.default_plot.temps_plot_s))
        else:
            self.x_plot_length = 0
            self.interface.But_switch_x_span.config(text='Plot over 5 s')

    def plot_data(self):
        """Met a jour le graphique matplotlib selon le mode actif."""
        cfg  = self.config.default_plot
        mode = self.plot_output_values
        try:
            if mode == cfg.ref_plot_vs_index:
                self._plot_vs_index()
            elif mode == cfg.ref_plot_vs_time:
                self._plot_vs_time()
            elif mode == cfg.ref_plot_one_vs_another:
                self._plot_one_vs_another()
            elif mode in (cfg.ref_plot_temp_vs_time_sensor_ref,
                           cfg.ref_plot_temp_vs_time_sensor_mat,
                           cfg.ref_plot_temp_vs_time):
                self._plot_temp(mode)
        except Exception:
            pass

        if self.after_call_alive:
            self.after(self.config.default_system.update_graph_every_ms, self.plot_data)

    # ---- helpers plot ----

    def _get_plot_indices(self):
        """Retourne (index_start, index_start_tip, index_stop)."""
        with self.link.saving_data_lock:
            i1 = self.link.last_saved_index
        i_tip = max(0, i1 - self.config.default_plot.number_points_tip)
        i0    = max(0, i1 - (self.x_plot_length if self.x_plot_length else self.plot_delta_nb_pts))
        return i0, i_tip, i1

    def _refresh_canvas(self):
        self.interface.fig.ax.relim()
        self.interface.fig.ax.autoscale_view()
        self.interface.fig.canvas.draw()

    def _plot_vs_index(self):
        i0, i_tip, i1 = self._get_plot_indices()
        sub = self.plot_subsampling
        with self.link.saving_data_lock:
            d = self.link.data_summary
            self.interface.fig.list_lines[1].set_xdata(d[i0:i1:sub, 1])
            self.interface.fig.list_lines[1].set_ydata(d[i0:i1:sub, 2])
            self.interface.fig.list_lines[2].set_xdata(d[i_tip:i1, 1])
            self.interface.fig.list_lines[2].set_ydata(d[i_tip:i1, 2])
        self._refresh_canvas()

    def _plot_vs_time(self):
        i0, i_tip, i1 = self._get_plot_indices()
        sub = self.plot_subsampling
        with self.link.saving_data_lock:
            d = self.link.data_summary
            self.interface.fig.list_lines[1].set_xdata(d[i0:i1:sub, 0] / 1000)
            self.interface.fig.list_lines[1].set_ydata(d[i0:i1:sub, 2])
            self.interface.fig.list_lines[2].set_xdata(d[i_tip:i1,  0] / 1000)
            self.interface.fig.list_lines[2].set_ydata(d[i_tip:i1,  2])
            self.interface.fig.list_lines[3].set_xdata(d[i0:i1:sub, 0] / 1000)
            self.interface.fig.list_lines[3].set_ydata(d[i0:i1:sub, 3])
            self.interface.fig.list_lines[4].set_xdata(d[i_tip:i1,  0] / 1000)
            self.interface.fig.list_lines[4].set_ydata(d[i_tip:i1,  3])
        self._refresh_canvas()

    def _plot_one_vs_another(self):
        i0, i_tip, i1 = self._get_plot_indices()
        sub = self.plot_subsampling
        with self.link.saving_data_lock:
            d = self.link.data_summary
            self.interface.fig.list_lines[1].set_xdata(d[i0:i1:sub, 3])
            self.interface.fig.list_lines[1].set_ydata(d[i0:i1:sub, 2])
            self.interface.fig.list_lines[2].set_xdata(d[i_tip:i1,  3])
            self.interface.fig.list_lines[2].set_ydata(d[i_tip:i1,  2])
        self._refresh_canvas()

    def _plot_temp(self, mode):
        cfg = self.config.default_plot
        sub = self.plot_subsampling
        i0, i_tip, i1 = self._get_plot_indices()
        with self.link.saving_data_lock:
            d = self.link.data_summary
            if mode == cfg.ref_plot_temp_vs_time_sensor_ref:
                col_p, col_t, ref_row = 3, 7, 1
            elif mode == cfg.ref_plot_temp_vs_time_sensor_mat:
                col_p, col_t, ref_row = 2, 6, 0
            else:  # ref_plot_temp_vs_time: overlay both temperature columns
                self.interface.fig.list_lines[1].set_xdata(d[i0:i1:sub, 0] / 1000)
                self.interface.fig.list_lines[1].set_ydata(d[i0:i1:sub, 6])
                self.interface.fig.list_lines[2].set_xdata(d[i_tip:i1,  0] / 1000)
                self.interface.fig.list_lines[2].set_ydata(d[i_tip:i1,  6])
                self.interface.fig.list_lines[3].set_xdata(d[i0:i1:sub, 0] / 1000)
                self.interface.fig.list_lines[3].set_ydata(d[i0:i1:sub, 7])
                self.interface.fig.list_lines[4].set_xdata(d[i_tip:i1,  0] / 1000)
                self.interface.fig.list_lines[4].set_ydata(d[i_tip:i1,  7])
                self._refresh_canvas()
                return

            self.interface.fig.list_lines[1].set_xdata(d[i0:i1:sub, 0] / 1000)
            self.interface.fig.list_lines[1].set_ydata(d[i0:i1:sub, col_p])
            self.interface.fig.list_lines[2].set_xdata(d[i_tip:i1,  0] / 1000)
            self.interface.fig.list_lines[2].set_ydata(d[i_tip:i1,  col_p])
            self.interface.fig.list_lines[3].set_xdata(d[i0:i1:sub, 0] / 1000)
            self.interface.fig.list_lines[3].set_ydata(
                (d[i0:i1:sub, col_t] - d[ref_row, col_t]) * 10)
            self.interface.fig.list_lines[4].set_xdata(d[i_tip:i1,  0] / 1000)
            self.interface.fig.list_lines[4].set_ydata(
                (d[i_tip:i1,  col_t] - d[ref_row, col_t]) * 10)
        self._refresh_canvas()