# Reference Audio for CosyVoice Voice Cloning

This directory contains reference audio files used for zero-shot voice cloning with CosyVoice.

## Adding a New Reference Audio

1. Record or obtain a WAV audio file of the target speaker (15-60 seconds recommended).
2. Save it in this directory with a descriptive name, e.g. `zhang_san_ref.wav`.
3. Register it in the `VOICE_PROFILES` dict in `src/tts/cosyvoice_client.py`:

```python
VOICE_PROFILES = {
    "tong_jincheng": {
        "ref_audio": "ref_audio/tong_jincheng_ref.wav",
        "ref_text": "You are a helpful assistant.<|endofprompt|>大家好。"
    },
    "zhang_san": {
        "ref_audio": "ref_audio/zhang_san_ref.wav",
        "ref_text": "You are a helpful assistant.<|endofprompt|>你好，我是张三。"
    }
}
```

4. Set the default voice via environment variable or config:

```
COSYVOICE_DEFAULT_VOICE=zhang_san
```

## Recommended Audio Format

- Format: WAV (PCM)
- Sample rate: 16kHz or 24kHz
- Duration: 15-60 seconds
- Content: Natural speech, clean background, no music or noise
- Tip: Record yourself speaking naturally for about 30 seconds. The reference text in the profile should match what is spoken in the audio.
