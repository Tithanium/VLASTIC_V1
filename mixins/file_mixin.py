#v5
import os
import numpy as np
from tkinter.filedialog import askdirectory


class FileMixin:
    """Gestion des fichiers et dossiers de sauvegarde (carte unique)."""

    def implement_folder_structure(self):
        """Cree le dossier de sauvegarde s'il n'existe pas encore."""
        folder = self.mastervar_default_folder.get()
        if not os.path.exists(folder):
            os.makedirs(folder)

    def define_name_txt_saved(self):
        """Determine le prochain nom de fichier disponible dans le dossier courant."""
        diam = self.mastervar_diameter_aperture.get()

        if self.mastervar_perform_calib.get():
            partie  = 'Ref' if diam == 'Ref' else diam.split('.')[0]
            nom_base = f'Calibration_ap_{partie}mm_'
        else:
            if diam == 'Ref':
                nom_base = 'Calibration_ap_Refmm_'
            else:
                partie   = diam.split('.')[0]
                nom_base = f'{self.mastervar_default_name_base.get()}_ap_{partie}mm_'

        folder = self.mastervar_default_folder.get()
        if not os.path.exists(folder):
            os.makedirs(folder)

        # Fichier marqueur de couleur
        color_markers = {'black': 'BLACK.txt', 'red': 'RED.txt'}
        marker = color_markers.get(self.config.default_system.color)
        if marker:
            open(os.path.join(folder, marker), 'w').close()

        # Trouve le prochain index libre
        index_list = [0]
        for nom in os.listdir(folder):
            full_path = os.path.join(folder, nom)
            if not os.path.isdir(full_path) and len(nom) > len(nom_base) + 2:
                if nom[3:len(nom_base) + 3] == nom_base:
                    part = nom[len(nom_base) + 3:].split('_')[0]
                    if part.isdigit():
                        index_list.append(int(part))
        next_index = np.max(index_list) + 1

        txt_count = sum(1 for f in os.listdir(folder) if f.endswith('.txt'))
        self.save_data_name = f"{txt_count:03}{nom_base}{next_index}_raw.txt"
        self.interface.Label_full_name_saving.config(text=self.save_data_name)

    def start_record(self):
        """Ouvre le fichier de sauvegarde et active l'enregistrement."""
        folder = self.mastervar_default_folder.get()
        if not os.path.exists(folder):
            os.makedirs(folder)

        self.path_total_save_name_data = os.path.join(folder, self.save_data_name)

        with self.file_data_save_lock:
            if hasattr(self, 'file_data_save_id') and hasattr(self.file_data_save_id, 'close'):
                self.file_data_save_id.close()
            self.file_data_save_id = open(self.path_total_save_name_data, 'w')

        self.currently_saving_data = True
        self.save_data_up_to_nb    = None

        for btn in ('But_next_test_DMA', 'But_stop_DMA',
                    'But_next_test_DMA_nodelete', 'But_stop_DMA_nodelete'):
            getattr(self.interface, btn).config(state='normal')

        print(f"Open file {self.path_total_save_name_data} for saving the data.")
        self.interface.Frame_recording_status.config(bg='green')
        self.interface.Label_recording_status.config(text='Rec ON', bg='green')
        self.interface.But_change_test_mode.config(state='disabled')

    def stop_record(self):
        """Arrete l'enregistrement et ferme le fichier de sauvegarde."""
        # For the single board, saving is written directly in the consuming thread
        # so simply flag the stop; no need to wait for a stitching thread.
        self.currently_saving_data = False
        self.save_data_up_to_nb    = None

        with self.file_data_save_lock:
            try:
                if hasattr(self, 'file_data_save_id') and hasattr(self.file_data_save_id, 'close'):
                    self.file_data_save_id.close()
                    print(f"Stop recording and closed textfile {self.path_total_save_name_data}")
                    if self.abort_current_saving:
                        print(f"Removing the textfile {self.path_total_save_name_data}")
                        os.remove(self.path_total_save_name_data)
                        self.abort_current_saving = False
            except Exception:
                print("No recording in process")

        self.interface.Frame_recording_status.config(bg='red')
        self.interface.Label_recording_status.config(text='Rec OFF', bg='red')
        self.interface.But_change_test_mode.config(state='normal')
        self.define_name_txt_saved()

    def browse_for_manual_modifications(self):
        """Ouvre le dossier courant dans l'explorateur de fichiers."""
        os.startfile(self.mastervar_default_folder.get())

    def browse_folder(self):
        """Ouvre un selecteur de dossier et met a jour le dossier de sauvegarde."""
        chemin_base = self.mastervar_default_folder.get()
        proposed    = askdirectory(initialdir=os.path.dirname(chemin_base))
        if proposed:
            self.mastervar_default_folder.set(proposed)
        self.implement_folder_structure()