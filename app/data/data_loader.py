import cmath

import pandas as pd
import os

"""
   This file contains helper methods to load certain files such as the material registry "materials.csv" and the
   example datasets.
"""
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
epsilon = 8.85418782E-12

def loadCSV(path: str) -> pd.DataFrame:
    """
    :param path: the path to the csv file starting from work directory
    :return: the loaded csv file as a panda dataframe
    """
    return pd.read_csv(os.path.join(os.getcwd(), path))

def writeCSV(df: pd.DataFrame, path: str):
    """
    :param path: the path where you want to write the csv file starting from work directory
    :param df: the dataframe to be written
    :return: nothing
    """
    df.to_csv(os.path.join(os.getcwd(), path), index=False)

def loadMaterials():
    """
    Load the material data from "data/materials.csv" and calculate missing constants if necessary and possible
    :return: panda dataframe with material constants
    """
    df = pd.read_csv(os.path.join(PROJECT_ROOT, "data/materials.csv")).drop(columns=["Source"])
    df.index = df["Material"].tolist()
    df = df.drop(index=["Description", "Units"]).drop(columns=["Material"]).infer_objects(copy=False).fillna(0)
    standardize(df)
    return df

def loadISAFDataset(name: str, maxFreq: int):
    """
    Load example ISAF dataset from folder "simulation_scripts/examples/IUS2025/data
    :param name: the name of the dataset
    :param maxFreq: the maximum frequency to be loaded
    :return: dictionary with keys "frequency" and "impedance" which contain the x and y values of the datapoints
    respectively
    """
    maxFreq *= 1E6
    data = pd.read_csv(os.path.join(PROJECT_ROOT, "simulation_scripts/examples/IUS2025/data", name))
    frequency = data["Frequency(Hz)"]
    impedance = data["|Z|"]
    index = len(frequency) - 1
    for i in range(len(frequency)):
        if frequency[i] > maxFreq:
            index = i
            break
    frequency = frequency[:index] / 1E6
    impedance = impedance[:index]
    return {"impedance": impedance, "frequency": frequency}

# Calculates missing material parameters by using other ones, for example the speed of sound from
# the stiffness constant and density
def standardize(df: pd.DataFrame):
    """
    Internal function called in `loadMaterials()` to standardize the material constants. It calculates the following
    if missing: the imaginary component of the stiffness constant c33 from the quality factor Q_m. The speed of sound
    from c33 and density rho, the electric permittivity eps33 from the vacuum permittivity epsilon (defined in this
    file), the electrical loss tangent tan(sigma_e) and the relative permittivity eps_r33.
    :param df: the name of the dataset
    :param maxFreq: the maximum frequency to be loaded
    :return: dictionary with keys "frequency" and "impedance" which contain the x and y values of the datapoints
    respectively
    """
    for i, mat in df.iterrows():
        c = complex(mat["c33"])
        if c.__abs__() != 0:
            Q = float(mat["Q_m"])
            if c.imag == 0 and Q != 0:
                im = (1./Q) * c.real
                c = complex(c.real, im)
                mat["c33"] = c
            if float(mat["v"]) == 0:
                v = cmath.sqrt(c.real/float(mat["roh"]))
                mat["v"] = v

        eps = complex(mat["eps33"])
        eps_r = eps.real
        eps_i = eps.imag
        tan = float(mat["tan(sigma_e)"])
        if eps_r == 0:
            eps_r = epsilon * float(mat["eps_r33"])
        if eps_i == 0 and tan != 0:
            eps_i = eps_r * tan
        mat["eps33"] = complex(eps_r, eps_i)

        df.loc[i] = mat

