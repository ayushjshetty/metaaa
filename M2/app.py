from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
from werkzeug.utils import secure_filename
import os
import io
import zipfile
import json
from utils.formatters import convert_metadata_format
from utils.file_processing import process_uploaded_files, process_pasted_code
from parsers.cobol import parse_cobol
# from parsers.pascal import parse_pascal  # Example for more languages
# from gpt4o_integration import enrich_metadata  # Stub for future GPT-4o
# from interface_mapping import map_interfaces  # Stub for future interface mapping

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = set(['cob', 'bas', 'asm', 'jcl', 'for', 'pas', 'ada', 'pli', 'rpg', 'zip', 'txt'])

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    files = request.files.getlist('file')
    code_text = request.form.get('code_text', '')
    language = request.form.get('language', '').lower()
    metadata = []
    if files and files[0].filename:
        metadata = process_uploaded_files(files, language)
    elif code_text:
        metadata = process_pasted_code(code_text, language)
    else:
        return render_template('index.html', error='No input provided.')
    # session or temp storage for metadata
    request.environ['metadata'] = metadata
    return render_template('preview.html', metadata=metadata, format='json')

@app.route('/preview', methods=['POST'])
def preview():
    metadata = request.form.get('metadata')
    fmt = request.form.get('format', 'json')
    if not metadata:
        return jsonify({'error': 'No metadata to preview.'}), 400
    metadata_obj = json.loads(metadata)
    converted = convert_metadata_format(metadata_obj, fmt)
    return jsonify({'preview': converted})

@app.route('/download', methods=['POST'])
def download():
    metadata = request.form.get('metadata')
    fmt = request.form.get('format', 'json')
    filename = f'metadata.{fmt}'
    if not metadata:
        return 'No metadata to download.', 400
    metadata_obj = json.loads(metadata)
    converted = convert_metadata_format(metadata_obj, fmt)
    return send_file(io.BytesIO(converted.encode('utf-8')), as_attachment=True, download_name=filename, mimetype='text/plain')

if __name__ == '__main__':
    app.run(debug=True) 