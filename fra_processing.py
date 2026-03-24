import pandas as pd
import numpy as np

def process_fra(input_path, output_path):

    df = pd.read_excel(input_path)

    STATUS = df.iloc[:, 1]
    CNTTYPE = df.iloc[:, 24]
    RISK_TERM = pd.to_numeric(df.iloc[:, 27], errors='coerce')
    PREM_TERM = pd.to_numeric(df.iloc[:, 28], errors='coerce')
    FREQUENCY = pd.to_numeric(df.iloc[:, 29], errors='coerce')
    RCDDATE = pd.to_datetime(df.iloc[:, 30], errors='coerce')
    PAIDTODATE = pd.to_datetime(df.iloc[:, 31], errors='coerce')
    PREMCESDTE = pd.to_datetime(df.iloc[:, 33], errors='coerce')
    NEXT_PAYDATE = pd.to_datetime(df.iloc[:, 48], errors='coerce')
    BASE_PREMIUM = pd.to_numeric(df.iloc[:, 51], errors='coerce')

    # -------------------------------
    # Calculations
    # -------------------------------

    policy_year_check = RISK_TERM - ((NEXT_PAYDATE - RCDDATE).dt.days // 365)
    years_premium_paid = (PAIDTODATE - RCDDATE).dt.days // 365

    annualized_premium = np.round(np.select(
        [FREQUENCY == 1, FREQUENCY == 2, FREQUENCY == 4, FREQUENCY == 12],
        [BASE_PREMIUM,
         BASE_PREMIUM / 0.51,
         BASE_PREMIUM / 0.26,
         BASE_PREMIUM / 0.09083],
        default=np.nan
    ), 2)

    paid_up_factor = (PAIDTODATE - RCDDATE).dt.days / (PREMCESDTE - RCDDATE).dt.days
    paid_up_factor = np.round(paid_up_factor, 2)
    paid_up_factor[(PREMCESDTE <= RCDDATE) | (PREMCESDTE.isna())] = np.nan

    # -------------------------------
    # FRA Calculation
    # -------------------------------

    def calc_fra(idx):
        if CNTTYPE.iloc[idx] == "FSP" and policy_year_check.iloc[idx] == 1:
            if STATUS.iloc[idx] in ["DH", "SU", "CF"]:
                return 0.0
            elif STATUS.iloc[idx] == "IF":
                return round(
                    annualized_premium[idx] * 0.08 +
                    annualized_premium[idx] * 0.09 +
                    annualized_premium[idx] * 0.10 * (RISK_TERM.iloc[idx] - 2), 2
                )
            else:
                return round(
                    annualized_premium[idx] * 0.08 +
                    annualized_premium[idx] * 0.09 +
                    annualized_premium[idx] * 0.10 * (years_premium_paid.iloc[idx] - 2) +
                    annualized_premium[idx] * paid_up_factor.iloc[idx] *
                    (RISK_TERM.iloc[idx] - years_premium_paid.iloc[idx]) * 0.10, 2
                )
        return np.nan

    fra_values = [calc_fra(i) for i in range(len(df))]

    # -------------------------------
    # New columns
    # -------------------------------

    new_cols = pd.DataFrame({
        'Policy Year Check': policy_year_check.values,
        'Number of years Premium is paid': years_premium_paid.values,
        'Annualized Premium': annualized_premium,
        'Paid up factor': paid_up_factor.values,
        'Protiviti Output FRA': np.round(fra_values, 2),
    })

    # -------------------------------
    # Insert columns
    # -------------------------------

    if 'BASE_PREMIUM' not in df.columns:
        raise ValueError("BASE_PREMIUM column not found")

    base_idx = df.columns.get_loc('BASE_PREMIUM')

    df.insert(base_idx + 1, 'Unnamed: 52', np.nan)

    for i, col in enumerate(new_cols.columns):
        df.insert(base_idx + 2 + i, col, new_cols[col])

    # -------------------------------
    # Write output
    # -------------------------------

    with pd.ExcelWriter(output_path, engine='xlsxwriter', datetime_format='dd-mmm-yy') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')

        wb = writer.book
        ws = writer.sheets['Sheet1']

        date_fmt = wb.add_format({'num_format': 'dd-mmm-yy'})
        dec2_fmt = wb.add_format({'num_format': '0.00'})

        for col_idx in [30, 31, 33, 48]:
            ws.set_column(col_idx, col_idx, 15, date_fmt)

        for col_name in ['Annualized Premium', 'Paid up factor', 'Protiviti Output FRA']:
            if col_name in df.columns:
                col_idx = df.columns.get_loc(col_name)
                ws.set_column(col_idx, col_idx, 18, dec2_fmt)