from flask import Flask, render_template, request, send_file, Response
import os
import json
import math
import pandas as pd
import numpy as np
from werkzeug.utils import secure_filename

from fra_processing import process_fra
from gla_processing import process_gla

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# ── Bulletproof value sanitiser: NaN/Inf/numpy → plain Python ─────────────────
def _safe_val(v):
    if v is None:
        return None
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(v, float):
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(v, np.ndarray):
        return [_safe_val(x) for x in v.tolist()]
    return v


def _walk(obj):
    """Recursively sanitise a nested dict/list structure."""
    if isinstance(obj, dict):
        return {k: _walk(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_walk(v) for v in obj]
    return _safe_val(obj)


def safe_jsonify(payload, status=200):
    body = json.dumps(_walk(payload), ensure_ascii=False)
    return Response(body, status=status, mimetype='application/json')


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    try:
        file      = request.files['file']
        calc_type = request.form['calc_type']

        filename    = secure_filename(file.filename)
        input_path  = os.path.join(UPLOAD_FOLDER, filename)
        output_path = os.path.join(OUTPUT_FOLDER, "output_" + filename)

        file.save(input_path)

        if calc_type == "FRA":
            result_df = process_fra(input_path, output_path)
            calculated_cols = [
                'Policy Year Check',
                'Number of years Premium is paid',
                'Annualized Premium',
                'Paid up factor',
                'Protiviti Output FRA',
            ]
        elif calc_type == "GLA":
            result_df = process_gla(input_path, output_path)
            calculated_cols = [
                'TAT for Payment Due date',
                'Protiviti GLA Calculation',
            ]
        else:
            return safe_jsonify({'error': 'Invalid calculation type'}, 400)

        # ── Build preview (first 200 rows) ──────────────────────────────────
        preview_df = result_df.head(200).copy()

        # Stringify datetime columns
        for col in preview_df.columns:
            if pd.api.types.is_datetime64_any_dtype(preview_df[col]):
                preview_df[col] = preview_df[col].dt.strftime('%d-%b-%y')

        # Replace pandas NaT / NaN with None
        preview_df = preview_df.where(pd.notnull(preview_df), None)

        # Convert to safe Python lists
        rows = [
            [_safe_val(v) for v in row]
            for row in preview_df.values.tolist()
        ]

        return safe_jsonify({
            'columns':         list(preview_df.columns),
            'rows':            rows,
            'total_rows':      len(result_df),
            'preview_rows':    len(rows),
            'calculated_cols': calculated_cols,
            'output_file':     "output_" + filename,
            'calc_type':       calc_type,
        })

    except Exception as e:
        import traceback
        return safe_jsonify({'error': str(e), 'trace': traceback.format_exc()}, 500)


@app.route('/download/<filename>')
def download(filename):
    output_path = os.path.join(OUTPUT_FOLDER, filename)
    if os.path.exists(output_path):
        return send_file(output_path, as_attachment=True)
    return "File not found", 404


if __name__ == "__main__":
    app.run(debug=True)
