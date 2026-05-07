import whisper,io,librosa,numpy as np
import soundfile as rf
from functools import lru_cache

#Load model once cached - use base on free tier to save RAM

@lru_cache
def get_model():
    return whisper.load('base')

FILLER_WORDS = {'um', 'uh', 'like', 'you know', 'basically', 'literally',
                'actually', 'so', 'right', 'okay', 'kind of', 'sort of'}

async def whisper_transcribe(audio_bytes: bytes) -> str:
    '''Transcribe audio bytes to text using Whisper.'''
    model = get_model()
    # Write to temp buffer whisper can read
    audio_array, sr = sf.read(io.BytesIO(audio_bytes))
    if sr != 16000:
        audio_array = librosa.resample(audio_array, orig_sr=sr, target_sr=16000)
    result = model.transcribe(audio_array.astype(np.float32), language='en')
    return result['text'].strip()

async def analyse_speech(audio_bytes: bytes) -> dict:
    '''Analyse speech metrics: WPM, filler words, speaking time.'''
    audio_array, sr = sf.read(io.BytesIO(audio_bytes))
    duration_seconds = len(audio_array) / sr
    transcript = await whisper_transcribe(audio_bytes)
    words      = transcript.split()
    word_count = len(words)
    wpm        = int((word_count / duration_seconds) * 60) if duration_seconds > 0 else 0
    # Count filler words
    lower_t = transcript.lower()
    filler_count = sum(lower_t.count(fw) for fw in FILLER_WORDS)
    # Estimate silence ratio via RMS energy
    rms = librosa.feature.rms(y=audio_array)[0]
    silence_ratio = float(np.mean(rms < 0.01))
    return {
        'wpm': wpm,
        'filler_count': filler_count,
        'word_count': word_count,
        'duration_seconds': round(duration_seconds, 1),
        'silence_ratio': round(silence_ratio, 2),
        'transcript': transcript
    }