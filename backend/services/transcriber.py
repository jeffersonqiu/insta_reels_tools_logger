import os

import assemblyai as aai

from config import settings


class TranscriptionError(Exception):
    pass


def transcribe_audio_file(audio_path: str) -> str:
    if not settings.assemblyai_api_key:
        raise TranscriptionError("ASSEMBLYAI_API_KEY is missing.")

    aai.settings.api_key = settings.assemblyai_api_key
    transcriber = aai.Transcriber()

    try:
        transcript = transcriber.transcribe(audio_path)
        if transcript.status == aai.TranscriptStatus.error:
            raise TranscriptionError(f"AssemblyAI failed: {transcript.error}")
        return transcript.text or ""
    except Exception as exc:
        raise TranscriptionError(f"Failed to transcribe audio: {exc}") from exc
    finally:
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except OSError:
            pass
