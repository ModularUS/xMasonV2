import math
import matplotlib.pyplot as plt
import glob, os
import pandas as pd
import yaml
import pickle

import numpy as np
import sys

from scipy.signal import find_peaks

sys.path.append('../..')  # Add parent directory to path

from app.data import data_loader
from app.models import tf_model
from app.utils import utils


def runYAMLSimulations(materials: pd.DataFrame, config_name=None):
    """
    This function can be called to run the "bulk simulation_scripts" feature. For more info check README.md
    :param materials: loaded material registry
    :param config_name: specific config file name to run (e.g., 'pvdfDstack.yaml')
    :return: simulation_scripts results and the config name used
    """
    configs = os.path.join(os.getcwd(), "config")
    plots = os.path.join(os.getcwd(), "result")
    
    # If specific config provided, use it; otherwise use all configs
    if config_name:
        files_to_process = [os.path.join(configs, config_name)]
    else:
        files_to_process = glob.glob(os.path.join(configs, "*.yaml"))
    
    for file in files_to_process:
        with open(file, "r") as stream:
            try:
                name = os.path.basename(file)
                f = yaml.safe_load(stream)

                diameter = f.get("diameter")
                side_length = f.get("side_length")
                area = f.get("area")

                if diameter is None and side_length is None and area is None:
                    print("No area specified. Skipping {}.".format(name))
                    continue

                if diameter is not None and diameter <= 0:
                    print("Diameter must be positive. Skipping {}.".format(name))
                    continue
                if side_length is not None and side_length <= 0:
                    print("Side length must be positive. Skipping {}.".format(name))
                    continue
                if area is not None and area <= 0:
                    print("Area must be positive. Skipping {}.".format(name))
                    continue

                if diameter is not None:
                    area = (diameter / 2) ** 2 * math.pi
                elif side_length is not None:
                    area = (side_length) ** 2

                connection = f.get("connection")
                if connection is None:
                    print("No connection type specified. Skipping {}.".format(name))
                    continue
                if not connection == "parallel-alternating" and not connection == "parallel" and not connection == "series":
                    print("Unrecognized connection type . Skipping {}.".format(name))
                    continue
                if connection == "parallel-alternating":
                    connection = "parallel_alt"

                backing_material = f.get("backing-material")
                transmission_material = f.get("transmission-material")
                if backing_material is None:
                    backing_material = "Air"
                elif not utils.materialExists(materials, backing_material):
                    print("Chosen backing material \"{}\" does not exist. Skipping {}."
                          .format(backing_material, name))
                    continue
                if transmission_material is None:
                    transmission_material = "Air"
                elif not utils.materialExists(materials, transmission_material):
                    print("Chosen transmission material \"{}\" does not exist. Skipping {}."
                          .format(transmission_material, name))
                    continue

                freq_band = f.get("frequency-band")
                if freq_band is None:
                    print("No frequency band specified. Skipping {}.".format(name))
                    continue
                min_frequency = freq_band["min"]
                if min_frequency is None:
                    print("No frequency band min specified. Skipping {}.".format(name))
                    continue
                elif not (0 < min_frequency):
                    print("Frequency band min must be positive. Skipping {}.".format(name))
                    continue
                max_frequency = freq_band["max"]
                if max_frequency is None:
                    print("No frequency band max specified. Skipping {}.".format(name))
                    continue
                elif not (0 < max_frequency):
                    print("Frequency band max must be positive. Skipping {}.".format(name))
                    continue

                if min_frequency > max_frequency:
                    print("Frequency band min must be smaller than max frequency. Skipping {}.".format(name))
                    continue

                freq_band = [min_frequency, max_frequency]

                stack = []
                validated = True
                for index, layer in enumerate(f["transducer"]):
                    material = layer.get("material")
                    if material is None:
                        print("No material specified for layer {}. Skipping {}.".format(index, name))
                        validated = False
                        break
                    if not utils.materialExists(materials, material):
                        print("Chosen material \"{}\" in layer {} does not exist. Skipping {}."
                              .format(material, index, name))
                        validated = False
                        break
                    thickness = layer.get("thickness")
                    if thickness is None:
                        print("No thickness specified for layer {}. Skipping {}.".format(index, name))
                        validated = False
                        break
                    if thickness <= 0:
                        print("Thickness for layer {} must be positive. Skipping {}.".format(index, name))
                        validated = False
                        break
                    thickness *= 1E-6

                    polarization = layer.get("counter-polarized")
                    if polarization is None:
                        polarization = False

                    stack.append([material, thickness, polarization])

                if not validated:
                    continue

                if len(stack) == 0:
                    print("No layers specified for transducer. Skipping {}.".format(name))
                    continue

                results, model = tf_model.runModel(
                    active_stack=stack,
                    frequency_band=freq_band,
                    materials=materials,
                    area=area,
                    mode=connection,
                    transmission_load=transmission_material,
                    backing_load=backing_material,
                )
                # plot = utils.setupPlot(True)
                # plot.plot(results["frequency"], results["impedance"], markersize=1, linewidth=2, color="#0050EF")
                # plt.savefig(os.path.join(plots, name[:-5] + ".png"), format="png")
                # Save simulation_scripts results with base name
                base_name = name[:-5]  # Remove .yaml extension
                pd.DataFrame(results).to_csv(os.path.join(plots, f"{base_name}_sim.csv"), index=False, header=True, sep=',')
                
                # Return both results and the base name for pairing
                return results, base_name

            except yaml.YAMLError as exc:
                print(exc)

    return None, None


def plot_sim_exp(sim, exp, result_id="comparison"):
    """
    Plot simulation_scripts vs experimental results.
    
    :param sim: Simulation results
    :param exp: Experimental results
    :param result_id: Unique identifier for saving results (e.g., 'pvdfDstack')
    """

    plot1 = setupPlot(logarithmic=False)
    #Data
    exp_data_s11 = {"frequency": np.squeeze(exp.f) * 10 ** -6, "impedance": np.squeeze(exp.s_db)}
    sim_s11 = -1 * 20 * np.log10(np.abs((np.array(sim["impedance"]) - 50) / (np.array(sim["impedance"]) + 50)))
    sim_data_s11 = {"frequency": sim["frequency"], "impedance": sim_s11}

    # Experiment
    plotSet(plot1, exp_data_s11,
            color="#647687", style="-", label="Experimental data", peaks=None)
    pk_exp, _ = find_peaks(np.array(exp_data_s11["impedance"]) * -1, prominence=0.01, distance=200)
    plot1.scatter(np.array(exp_data_s11["frequency"])[pk_exp],
                  np.array(exp_data_s11["impedance"])[pk_exp],
                  color='orange', marker='+', s=100)

    # Simulation
    plotSet(plot1, sim_data_s11,
            color="#0050EF", style="-", label="Model prediction", peaks=None)
    pk_sim, _ = find_peaks(np.array(sim_data_s11["impedance"]) * -1, prominence=0.01, distance=200)
    plot1.scatter(np.array(sim_data_s11["frequency"])[pk_sim],
                  np.array(sim_data_s11["impedance"])[pk_sim],
                  color='green', marker='+', s=100)
    plt.show()



    plot2 = setupPlot(logarithmic=True)
    # Data
    exp_data_imp = {"frequency": np.squeeze(exp.f) * 10 ** -6, "impedance": np.squeeze(exp.z_mag)}
    exp_peaks = {"x": np.array(exp_data_imp["frequency"])[pk_exp],
                 "y": np.array(exp_data_imp["impedance"])[pk_exp]}
    sim_data_imp = {"frequency": sim["frequency"], "impedance": np.abs(sim["impedance"])}
    sim_peaks = {"x": np.array(sim_data_imp["frequency"])[pk_sim],
                 "y": np.array(sim_data_imp["impedance"])[pk_sim]}
    # Experiment
    plotSet(plot2, exp_data_imp,
            color="#647687", style="--", label="Experimental data", peaks=exp_peaks, peak_color="black", marker="+", msize=250, malpha=0.9, order=2)
    # Simulation
    plotSet(plot2, sim_data_imp,
            color="#0050EF", style="-", lalpha=0.8, label="Model prediction", peaks=sim_peaks, peak_color="#417df2", marker="x", msize=250, malpha=0.9, order=3)
    plt.grid(True) #, which="both", linestyle="--", linewidth=0.7, alpha=0.7)
    plt.minorticks_on()
    plt.grid(True, which="major", linestyle="--", linewidth=0.6, color="gray", alpha=0.6)
    plt.grid(True, which="minor", linestyle=":", linewidth=0.4, color="gray", alpha=0.3)
    # Save with unique identifier
    plt.savefig(os.path.join(os.getcwd(), 'result', f'{result_id}_impedance_plot.png'), dpi=600)
    plt.show()

    metrics = performance_parameters(exp_peaks, sim_peaks)
    # Use result_id for transducer name if not customized
    latex_tab_converter(metrics, transducer_name=result_id.replace('_', ' ').title(), result_id=result_id)
    
    return metrics

def performance_parameters(exp_peaks, sim_peaks):

    min_len = min(len(exp_peaks['x']), len(sim_peaks['x']))
    
    # Extract frequency values
    f_exp = np.array(exp_peaks['x'][:min_len])
    f_sim = np.array(sim_peaks['x'][:min_len])
    
    # Calculate metrics
    f_delta = f_sim - f_exp
    f_relative = f_delta * 100 / f_exp
    f_ratio = f_sim / f_exp
    mae = np.mean(np.abs(f_delta))
    mre = np.mean(np.abs(f_relative))

    metrics = {"f_exp": np.round(f_exp, 3),
               "f_sim": np.round(f_sim, 3),
               "f_delta": np.round(f_delta, 3),
               "f_relative": np.round(f_relative, 3),
               "f_ratio": np.round(f_ratio, 3),
               "f_mae": np.round(mae, 3),
               "f_mre": np.round(mre, 3)}
    return metrics


def latex_tab_converter(metrics, transducer_name="Cascaded P(VDF-TrFE)", result_id="comparison"):
    """
    Convert performance metrics to LaTeX table format for direct copy-paste.
    
    The output format follows this LaTeX table structure:
    \\addlinespace[6pt]
    \\multicolumn{6}{l}{\\textbf{Transducer Name}}\\\\
    1 & f_pred & f_obs & Delta_f & Rel_error & ratio \\\\
    ...
    \\addlinespace[2pt]
    \\multicolumn{6}{r}{\\footnotesize Mean: MAE = \\SI{X.XXX}{\\mega\\hertz}, MRE = \\SI{XX.XX}{\\percent}}\\\\
    
    Parameters:
    -----------
    metrics : dict
        Dictionary containing f_sim, f_exp, f_delta, error_rel_pzt, f_ratio
    transducer_name : str
        Name of the transducer for the table header
    """
    
    # Start building the LaTeX output
    latex_lines = []
    
    # Add spacing and transducer header
    latex_lines.append("\\addlinespace[6pt]")
    latex_lines.append(f"\\multicolumn{{6}}{{l}}{{\\textbf{{{transducer_name}}}}}")
    latex_lines.append("\\\\")
    latex_lines.append("f_sim & f_exp & f_delta & err_rel & f_ratio \\\\")
    
    # Get the number of modes from the arrays
    num_modes = len(metrics["f_delta"])
    
    # Add data rows for each mode
    for i in range(num_modes):
        mode_num = i + 1
        
        # Extract values for this mode
        f_pred = metrics["f_sim"][i]
        f_obs = metrics["f_exp"][i]
        delta_f = metrics["f_delta"][i]
        rel_error = abs(metrics["f_relative"][i])  # Use absolute value for display
        ratio = metrics["f_ratio"][i]
        
        # Format the LaTeX row with proper spacing
        row = f"{mode_num} & {f_pred:7.3f} & {f_obs:7.3f} & {delta_f:7.3f} & {rel_error:6.3f} & {ratio:5.3f} \\\\"
        latex_lines.append(row)
    
    # Add the mean statistics footer
    latex_lines.append("\\addlinespace[2pt]")
    mae = metrics["f_mae"]
    mre = abs(metrics["f_mre"])  # Use absolute value for display
    footer = f"\\multicolumn{{6}}{{r}}{{\\footnotesize Mean: MAE = \\SI{{{mae:.3f}}}{{\\mega\\hertz}}, MRE = \\SI{{{mre:.3f}}}{{\\percent}}}}"
    latex_lines.append(footer)
    latex_lines.append("\\\\")
    
    # Join all lines
    latex_output = "\n".join(latex_lines)
    
    # Print the output with clear delimiters for easy copy-paste
    print("\n" + "="*70)
    print("LATEX TABLE OUTPUT (Copy-Paste Ready):")
    print("="*70)
    print(latex_output)
    print("="*70)
    
    # Also save to a text file for convenience with unique identifier
    output_file = os.path.join(os.getcwd(), 'result', f'{result_id}_latex_table.txt')
    with open(output_file, 'w') as f:
        f.write(latex_output)
    print(f"LaTeX table also saved to: {output_file}")
    print("="*70 + "\n")
    
    return latex_output




def setupPlot(logarithmic=True):
    fig = plt.figure(figsize=(5, 4), dpi=250)
    ax_1 = fig.add_subplot(111)

    if logarithmic:
        ax_1.set_yscale('log')
    ax_1.set_xlabel('Frequency [MHz]', fontsize=18)
    ax_1.set_ylabel(r'$\mid Z\mid [\Omega]$', fontsize=18)
    ax_1.tick_params(axis='x', labelsize=15)
    ax_1.tick_params(axis='y', labelsize=15)

    plt.tight_layout()

    return ax_1

def plotSet(plot, dataset, color="blue", style="-", lalpha=1, label="", peaks=None, peak_color="red", marker="x", msize=50, malpha=1, order=3):
    plot.plot(dataset["frequency"], dataset["impedance"], style,
              markersize=1,
              linewidth=2,
              color=color,
              label=label,
              alpha=lalpha)
    if peaks is not None:
        plot.scatter(x=peaks["x"], y=peaks["y"], color=peak_color, s=msize, linewidths=2, marker=marker, alpha=malpha, zorder=order)


def open_experiment(path):
    file = open(path, 'rb')
    ntwk_s11 = pickle.load(file)
    file.close()
    return ntwk_s11


def extract_result_id_from_filename(filename):
    """
    Extract a result ID from a filename.
    E.g., 'S11_1-50MHz_pvdfDstack.pkl' -> 'pvdfDstack'
    """
    import re
    # Remove path and extension
    base = os.path.basename(filename).rsplit('.', 1)[0]
    # Try to extract the transducer name (last part after underscore)
    parts = base.split('_')
    if len(parts) > 1:
        return parts[-1]
    return base


def save_comparison_summary(result_id, metrics, sim_file, exp_file):
    """
    Save a summary JSON file with all comparison metadata.
    """
    summary = {
        "result_id": result_id,
        "timestamp": pd.Timestamp.now().isoformat(),
        "files": {
            "simulation_config": sim_file,
            "experimental_data": exp_file,
            "simulation_results": f"{result_id}_sim.csv",
            "impedance_plot": f"{result_id}_impedance_plot.png",
            "latex_table": f"{result_id}_latex_table.txt"
        },
        "metrics": {
            "mae_mhz": float(metrics["f_mae"]),
            "mre_percent": float(abs(metrics["f_mre"])),
            "num_modes": len(metrics["f_delta"]),
            "frequency_pairs": [
                {"mode": i+1, "f_sim": float(metrics["f_sim"][i]), "f_exp": float(metrics["f_exp"][i])}
                for i in range(len(metrics["f_delta"]))
            ]
        }
    }
    
    import json
    output_file = os.path.join(os.getcwd(), 'result', f'{result_id}_summary.json')
    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"Summary saved to: {output_file}")


if __name__ == "__main__":
    materials = data_loader.loadMaterials()
    
    # Define the experiment-simulation_scripts pairs
    # Format: (experiment_file, yaml_config, result_id)
    experiment_pairs = [
        ('S11_1-50MHz_pvdfDstack.pkl', 'pvdfDstack.yaml', 'pvdfDstack'),
    ]
    
    for exp_file, yaml_config, result_id in experiment_pairs:
        print(f"\nProcessing pair: {result_id}")
        print("="*50)
        
        # Run simulation_scripts for specific config
        sim_results, config_base = runYAMLSimulations(materials, config_name=yaml_config)
        
        if sim_results is None:
            print(f"Simulation failed for {yaml_config}")
            continue
            
        # Load corresponding experimental results
        exp_path = os.path.join(os.getcwd(), 'result', exp_file)
        if os.path.exists(exp_path):
            exp_results = open_experiment(exp_path)
            
            # Plot comparison with unique identifier
            metrics = plot_sim_exp(sim_results, exp_results, result_id=result_id)
            
            # Save comparison summary
            save_comparison_summary(result_id, metrics, yaml_config, exp_file)
            
            print(f"Results saved with prefix: {result_id}_")
        else:
            print(f"Experimental file not found: {exp_path}")