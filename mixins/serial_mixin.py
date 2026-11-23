#v5
import threading
import time
import traceback
import numpy as np
from pySerialTransfer import pySerialTransfer as txfer


class SerialMixin:
    """Threads serie, lecture des paquets, stockage des donnees (carte unique)."""

    # ------------------------------------------------------------------
    # Thread : tick du port serie -> alimente la queue
    # ------------------------------------------------------------------

    def _th_extract_data_from_serials(self):
        self._stop_event_ticking = threading.Event()
        print('Start Thread : ticking the board serial')

        self.link.connection.flushInput()
        self.link.rx_buff = bytearray(0xFE)
        self.link.tx_buff = bytearray(0xFE)

        while not self._stop_event_ticking.is_set():
            try:
                self.link.tick()
            except Exception as e:
                print(f"[THREAD TICKING] EXCEPTION : {e}")
                traceback.print_exc()

        self.link.connection.flushInput()
        self.link.rx_buff = bytearray(0xFE)
        self.link.tx_buff = bytearray(0xFE)

        print('Thread stopped : not ticking the board serial')

    # ------------------------------------------------------------------
    # Thread : consommation de la queue -> decodage et stockage
    # ------------------------------------------------------------------

    def th_consume_queue(self):
        print('Start Thread : consuming the queue')
        self._stop_event_consuming = threading.Event()

        cfg = self.config.arduino[1]

        while not self._stop_event_consuming.is_set():
            try:
                item = self.queue_serial_data.get()
                if item is None:
                    continue

                # Packet layout (6 bytes from rx_buff):
                #   [0] brd_time_ind   (Arduino index 0-255)
                #   [1] status byte    (decoded as binary string)
                #   [2] pressure1 high byte
                #   [3] pressure1 low  byte
                #   [4] pressure2 high byte
                #   [5] pressure2 low  byte
                brd_time_ind         = item[0]
                arduino_board_status = bin(item[1])[2:].zfill(8)

                Pressure_sensor = (
                    cfg.pmin
                    + (256 * item[2] + item[3] - cfg.pressure_index_at_pmin)
                    * cfg.factor
                    - self.link.pressure_offset
                )
                Pressure_sensor2 = (
                    cfg.pmin
                    + (256 * item[4] + item[5] - cfg.pressure_index_at_pmin)
                    * cfg.factor
                    - self.link.pressure_offset2
                )

                # Index continuity check
                if self.link.arduino_previous_index is not None:
                    delta = brd_time_ind - self.link.arduino_previous_index
                    if delta == -255:
                        self.link.nb_index_time += 1
                    elif delta != 1:
                        if delta < 0:
                            delta += 256
                        self.link.missing_index += delta

                t_from_index = (
                    (self.link.nb_index_time * 256 + brd_time_ind)
                    * self.config.starting_param.sampling_rate_micro / 1000
                )

                with self.link.saving_data_lock:
                    self._grow_data_array_if_needed()
                    self.monitor_continous_last_sensor_count_state = int(
                        self.link.data_summary[self.link.last_saved_index, 5])
                    self.monitor_continous_last_sensor_homing_state = int(
                        self.link.data_summary[self.link.last_saved_index, 4])
                    self.link.arduino_board_last_status = arduino_board_status
                    self.link.arduino_previous_index    = brd_time_ind
                    self.link.last_saved_index         += 1
                    self.link.data_summary[self.link.last_saved_index, :] = [
                        t_from_index, brd_time_ind,
                        Pressure_sensor, Pressure_sensor2,
                        int(arduino_board_status[
                            self.config.convention.line_status_opto_homing]),
                        int(arduino_board_status[
                            self.config.convention.line_status_opto_count]),
                        0, 0,  # columns 6-7 reserved (temperature etc.)
                    ]

                self._update_sensor_counters(arduino_board_status)
                self._save_raw_to_file_if_recording(
                    brd_time_ind, Pressure_sensor, Pressure_sensor2, arduino_board_status)

            except Exception:
                print('Error during the consuming thread.')

        while not self.queue_serial_data.empty():
            self.queue_serial_data.get()
            print('Discard a value from queue serial')
        print('Thread stopped : stop consuming the queue')

    # ---- helpers de th_consume_queue ----

    def _grow_data_array_if_needed(self):
        """Agrandit data_summary si plein (a appeler sous saving_data_lock)."""
        if self.link.last_saved_index + 1 >= self.link.data_summary.shape[0]:
            self.link.data_summary = np.concatenate((
                self.link.data_summary,
                np.zeros((self.config.default_system.nb_lignes_data,
                          self.link.data_summary.shape[1]))
            ))

    def _update_sensor_counters(self, status):
        """Met a jour les compteurs homing/count."""
        conv      = self.config.convention
        direction = int(status[conv.line_status_rotation_direction])
        homing    = int(status[conv.line_status_opto_homing])
        count     = int(status[conv.line_status_opto_count])
        prev_h    = self.monitor_continous_last_sensor_homing_state
        prev_c    = self.monitor_continous_last_sensor_count_state

        # Front homing
        if direction == 0 and homing - prev_h == 1 and not self.monitor_continous_recent_homing:
            self.config.arduino_general.count_sensor_number = 60
            print('Reset Sensor count to %s' % self.config.arduino_general.count_sensor_number)
            self.monitor_continous_recent_homing = True
        if direction != 0 and homing - prev_h == -1 and not self.monitor_continous_recent_homing:
            self.config.arduino_general.count_sensor_number = 60
            print('Reset Sensor count to %s' % self.config.arduino_general.count_sensor_number)
            self.monitor_continous_recent_homing = True

        # Front count - forward
        if direction == 0:
            if count - prev_c == 1 and not self.monitor_continous_recent_count:
                self.config.arduino_general.count_sensor_number += 1
                self.monitor_continous_recent_count = True
                while self.config.arduino_general.count_sensor_number > 60:
                    self.config.arduino_general.count_sensor_number -= 60
                print('Current Sensor count is %s' % self.config.arduino_general.count_sensor_number)
            if count - prev_c == -1:
                self.monitor_continous_recent_count  = False
                self.monitor_continous_recent_homing = False
        # Front count - backward
        else:
            if count - prev_c == -1 and not self.monitor_continous_recent_count:
                self.config.arduino_general.count_sensor_number -= 1
                self.monitor_continous_recent_count = True
                while self.config.arduino_general.count_sensor_number < 1:
                    self.config.arduino_general.count_sensor_number += 60
                print('Current Sensor count is %s' % self.config.arduino_general.count_sensor_number)
            if count - prev_c == 1:
                self.monitor_continous_recent_count  = False
                self.monitor_continous_recent_homing = False

    def _save_raw_to_file_if_recording(self, brd_time_ind, p1, p2, status):
        """Ecrit une ligne brute dans le fichier si l'enregistrement est actif."""
        if not self.currently_saving_data:
            return
        conv = self.config.convention
        line = (
            str(int(brd_time_ind)) + ';'
            + str(-1 * p1) + ';0;'
            + str(-1 * p2) + ';'
            + str(int(status[conv.line_status_opto_homing])) + ';'
            + str(int(status[conv.line_status_opto_count])) + ';'
            + str(int(status[conv.line_status_rotation_direction])) + '\n'
        )
        with self.file_data_save_lock:
            try:
                self.file_data_save_id.write(line)
            except Exception:
                print('Error writing raw data to %s' % self.path_total_save_name_data)

    # ------------------------------------------------------------------
    # Callback tick -> queue
    # ------------------------------------------------------------------

    def _read_a_packet_to_queue(self):
        """Callback appele par link.tick() des qu'un paquet complet est disponible."""
        lnk = self.link
        if lnk.status in (txfer.Status.CRC_ERROR,
                           txfer.Status.PAYLOAD_ERROR,
                           txfer.Status.STOP_BYTE_ERROR):
            lnk.error_read_nb += 1
            return
        rec = [int(b) for b in lnk.rx_buff[:6]]
        self.queue_serial_data.put(rec)
        lnk.last_ticked_time = time.time() - self.time_program_start

    # ------------------------------------------------------------------
    # Arret des threads
    # ------------------------------------------------------------------

    def stop_threads(self):
        """Arrete proprement tous les threads actifs."""
        self.print_output_values = False
        try:
            self._stop_event_ticking.set()
            self.ticking_serials_thread.join()
        except Exception:
            pass
        try:
            self._stop_event_consuming.set()
            self.queue_serial_data.put(None)
            self.consume_queue_thread.join()
        except Exception:
            pass