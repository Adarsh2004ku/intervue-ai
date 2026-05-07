import os
import tempfile
import whisper,io,librosa,numpy as np
import soundfile as sf
from functools import lru_cache

#Load model once cached - use base on free tier to save RAM

@lru_cache
def get_model():
    return whisper.load_model('base')

FILLER_WORDS = {'um', 'uh', 'like', 'you know', 'basically', 'literally',
                'actually', 'so', 'right', 'okay', 'kind of', 'sort of'}

async def whisper_transcribe(audio_bytes: bytes) -> str:
    '''Transcribe audio bytes to text using Whisper.'''
    model = get_model()

    try:
        audio_array, sr = sf.read(io.BytesIO(audio_bytes))
        if sr != 16000:
            audio_array = librosa.resample(audio_array, orig_sr=sr, target_sr=16000)
        result = model.transcribe(audio_array.astype(np.float32), language='en')
        return result['text'].strip()
    except Exception:
        suffix = '.webm'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            result = model.transcribe(tmp_path, language='en')
        finally:
            os.unlink(tmp_path)

    return result['text'].strip()

async def analyse_speech(audio_bytes: bytes) -> dict:
    '''Analyse speech metrics: WPM, filler words, speaking time.'''
    transcript = await whisper_transcribe(audio_bytes)

    try:
        audio_array, sr = sf.read(io.BytesIO(audio_bytes))
        duration_seconds = len(audio_array) / sr
        rms = librosa.feature.rms(y=audio_array)[0]
        silence_ratio = float(np.mean(rms < 0.01))
    except Exception:
        duration_seconds = max(len(transcript.split()) / 2.4, 1)
        silence_ratio = 0

    words      = transcript.split()
    word_count = len(words)
    wpm        = int((word_count / duration_seconds) * 60) if duration_seconds > 0 else 0
    # Count filler words
    lower_t = transcript.lower()
    filler_count = sum(lower_t.count(fw) for fw in FILLER_WORDS)
    return {
        'wpm': wpm,
        'filler_count': filler_count,
        'word_count': word_count,
        'duration_seconds': round(duration_seconds, 1),
        'silence_ratio': round(silence_ratio, 2),
        'transcript': transcript
    }
