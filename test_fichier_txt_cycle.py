import matplotlib.pyplot as plt

def check_column_increments_and_plot(chemin_txt):
    with open(chemin_txt, 'r') as file:
        lines = file.readlines()

    total_lines = len(lines)
    previous_value = None
    issue_lines = []
    col2 = []
    col4 = []

    for line_number, line in enumerate(lines, start=1):
        columns = line.split(';')
        current_value = int(columns[0])
        col2.append(float(columns[1]))
        col4.append(float(columns[3]))

        if previous_value is not None:
            if not ((current_value == previous_value + 1) or (previous_value == 255 and current_value == 0)):
                issue_lines.append(line_number)

        previous_value = current_value

    print(f"Total number of lines: {total_lines}")
    print(f"Lines with issues: {issue_lines}")

    # Plotting
    plt.figure()
    plt.plot(range(total_lines), col2, label='Column 2')
    plt.plot(range(total_lines), col4, label='Column 4')
    plt.xlabel('Line Index')
    plt.ylabel('Value')
    plt.title('Column 2 and 4 Values')
    plt.legend()
    plt.show(block=True)

# Example usage:
chemin_txt = "C:\\Users\\connessn\\Datas\\02_RECHERCHE\\03_suction\\06_tests\\poubelle\\Calibration_ap_Refmm_1_raw.txt"
issues = check_column_increments_and_plot(chemin_txt)
