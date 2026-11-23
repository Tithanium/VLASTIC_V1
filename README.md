# VLASTIC_V1

**VLASTIC method to evaluate in vivo mechanical properties**

The current software is associated with the **V1 hardware** — with a slider-crank mechanism.
Install it to perform in vivo measurements with different cup sizes.
https://github.com/Tithanium/VLASTIC_V1

## Starting with VS Code
 0. Install VS code / download the containt of this github in a VLASTIC_software folder
 1. In VS code: File ▸ Open Folder… → select the VLASTIC_software folder.
 2. Ctrl+Shift+P → Python: Create Environment
 3. Pick Venv → pick the interpreter (Python 3.14.0 for the last working test) → on the next prompt tick
    requirements.txt → it creates .venv\ and installs everything.
 4. Done: VS Code auto-selects ./.venv as the interpreter.

## Usage Memento
-	In the Direct control panel: select the proper COM, “Connect”.
-	If nothing move during a test, check that the line is plugged (not only the usb !!)

- **For each patient**, create a folder in `D:\Patient\sacrum_PatientNAME\`

- **Open the program folder and check it contains**
  - `main.py`,
  - `interface_layout.py`,
  - `requirements.txt`,
  - `bin\config_black.ini`.

- **(Optional)** You may change line 7 of `config_black.ini` so that it indicates `default_folder = D:/Patient/sacrum_PatientNAME`.

- **In the graphical interface, select:**
  - 3 tests,
  - 5 cycles,
  - Check the folder `D:/Patient/sacrum_PatientNAME` is selected.
  - Click on "Set Pressure offset"

- **Calibration:**
  - connect the main tube to the reference tube,
  - select diameter = REF,
  - launch the calibration. Once a file is saved, you can stop the calibration.

- **Tests:**
  - Set a new cup on the main tube (6, 10, 15 and 20 mm),
  - Select the proper diameter in the graphical interface (name is updated).
  - "Start test queue" ⇒ the 3 tests are performed in a row.
  - Check for leakage during the test!!
  - At the end, check that the folder contains:
    - `BLACK.txt` (size 0 ko)
    - 12 files (3 per cup diameter, labelled `XXXTest_ap_YYmm_ZZ_raw.txt`, YY for cup diam, ZZ for test index, XXX for global index)
    - Calibration files (at least 1, example: `001Calibration_ap_Refmm_1_raw.txt`)

- **Send the folders to** nathanael.connesson@univ-grenoble-alpes.fr

## Citation (bibtex)

```bibtex
@article{connesson2023,
  author   = {Connesson, Nathanael and Briot, No{\'e}mie and Rohan, Pierre-Yves and Barraud, Pierre-Alain and Elahi, Seyed Ali and Payan, Yohan},
  keywords = {important},
  title    = {Bilayer Stiffness Identification of Soft Tissues by Suction},
  journal  = {Experimental Mechanics},
  year     = {2023},
  volume   = {63},
  pages    = {715--742},
  doi      = {10.1007/s11340-023-00946-x}
}
```
