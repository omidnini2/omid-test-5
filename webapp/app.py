from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
import uuid
from tempfile import NamedTemporaryFile
from pydub import AudioSegment
from TTS.api import TTS

app = Flask(__name__, static_folder='static')
CORS(app)

# Ensure output directory exists
OUTPUT_DIR = 'generated'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load XTTS model once at startup
print("Loading TTS model ... this may take a while on first run.")
try:
    tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2.0.3", progress_bar=False, gpu=False)
except Exception as e:
    print("Failed to load TTS model: ", e)
    tts = None

@app.route('/')
def root():
    # Serve SPA index
    return send_from_directory('static', 'index.html')

@app.route('/api/clone', methods=['POST'])
def clone_voice():
    """Accepts multipart/form-data with fields: voice (file), text (str)"""
    if 'voice' not in request.files:
        return jsonify({'error': 'voice file missing'}), 400
    text = request.form.get('text', '')
    if not text:
        return jsonify({'error': 'text missing'}), 400

    voice_file = request.files['voice']

    # Validate size
    voice_file.seek(0, os.SEEK_END)
    size_mb = voice_file.tell() / (1024 * 1024)
    voice_file.seek(0)
    if size_mb > 50:
        return jsonify({'error': 'Voice file exceeds 50MB limit.'}), 400

    # Save uploaded sample to temp wav
    with NamedTemporaryFile(delete=False, suffix='.wav') as tf:
        voice_path = tf.name
        voice_file.save(voice_path)

    # Convert to 16k wav mono using pydub if not already
    try:
        audio = AudioSegment.from_file(voice_path)
        audio = audio.set_frame_rate(16000).set_channels(1)
        audio.export(voice_path, format='wav')
    except Exception as e:
        return jsonify({'error': f'Unable to process voice file: {e}'}), 500

    if tts is None:
        return jsonify({'error': 'TTS model not loaded.'}), 500

    out_filename = f"{uuid.uuid4().hex}.wav"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    try:
        # If text is too long, you might want to chunk; naive chunk here 5000 chars
        max_len = 5000
        if len(text) > max_len:
            segments = [text[i:i+max_len] for i in range(0, len(text), max_len)]
            combined = None
            for seg in segments:
                temp_seg = NamedTemporaryFile(delete=False, suffix='.wav').name
                tts.tts_to_file(seg, speaker_wav=voice_path, file_path=temp_seg, language='fa')
                seg_audio = AudioSegment.from_wav(temp_seg)
                if combined is None:
                    combined = seg_audio
                else:
                    combined += seg_audio
                os.remove(temp_seg)
            combined.export(out_path, format='wav')
        else:
            tts.tts_to_file(text, speaker_wav=voice_path, file_path=out_path, language='fa')
    except Exception as e:
        return jsonify({'error': f'TTS generation failed: {e}'}), 500
    finally:
        os.remove(voice_path)

    return jsonify({'audio_url': f'/api/download/{out_filename}'})

@app.route('/api/download/<filename>')
def download(filename):
    return send_file(os.path.join(OUTPUT_DIR, filename), as_attachment=True, download_name='cloned_voice.wav')

@app.route('/api/languages')
def languages():
    # Example list; adjust with actual supported languages by XTTS or engine
    lang_list = [
        'fa', 'en', 'ar', 'fr', 'de', 'es', 'ru', 'zh', 'hi', 'ja', 'ko', 'tr', 'it', 'pt',
        # ... add as needed ...
    ]
    return jsonify({'languages': lang_list})

# Serve static files
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)