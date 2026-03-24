import pandas as pd
import numpy as np

def process_gla(input_path, output_path):

    # -------------------------------
    # Read File
    # -------------------------------
    df = pd.read_excel(input_path)

    # -------------------------------
    # Basic Validation
    # -------------------------------
    if df.shape[1] < 49:
        raise ValueError("Invalid GLA file format: Required columns are missing")

    # -------------------------------
    # Column Mapping (Index-based)
    # -------------------------------
    STATUS = df.iloc[:, 1]
    CNTTYPE = df.iloc[:, 24]
    PREM_TERM = pd.to_numeric(df.iloc[:, 28], errors='coerce')
    PREMCESDTE = pd.to_datetime(df.iloc[:, 33], errors='coerce')
    ORIGINAL_SA = pd.to_numeric(df.iloc[:, 44], errors='coerce')
    NEXT_PAYDATE = pd.to_datetime(df.iloc[:, 48], errors='coerce')

    # -------------------------------
    # Calculations
    # -------------------------------

    # TAT Calculation
    tat_days = (NEXT_PAYDATE - PREMCESDTE).dt.days

    # GLA Calculation
    gla_calc = np.where(
        (STATUS == 'IF') & (CNTTYPE.isin(['MSB', 'SMB'])),
        0.01 * ORIGINAL_SA * PREM_TERM,
        0
    )

    # -------------------------------
    # Add Output Columns
    # -------------------------------
    df['TAT for Payment Due date'] = tat_days
    df['Protiviti_GLA_Calculation'] = np.round(gla_calc, 2)

    # -------------------------------
    # Write Output
    # -------------------------------
    df.to_excel(output_path, index=False)