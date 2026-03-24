from flask import Flask, render_template, request, send_file
import os
from werkzeug.utils import secure_filename

from fra_processing import process_fra
from gla_processing import process_gla   # 👈 new file

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    try:
        file = request.files['file']
        calc_type = request.form['calc_type']

        filename = secure_filename(file.filename)

        input_path = os.path.join(UPLOAD_FOLDER, filename)
        output_path = os.path.join(OUTPUT_FOLDER, "output_" + filename)

        file.save(input_path)

        # 🔥 SWITCH LOGIC
        if calc_type == "FRA":
            process_fra(input_path, output_path)

        elif calc_type == "GLA":
            process_gla(input_path, output_path)

        else:
            return "Invalid calculation type"

        return send_file(output_path, as_attachment=True)

    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    app.run(debug=True)