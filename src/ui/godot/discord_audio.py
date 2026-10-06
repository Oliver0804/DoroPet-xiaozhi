"""把 Discord 語音頻道的一段 wav 送進小智，並把小智的回覆收成 wav."""

from __future__ import annotations

import base64
import io
import wave

import numpy as np

from src.bootstrap.protocols import PluginCommands
from src.constants.constants import AudioConfig, ListeningMode
from src.logging import get_logger

logger = get_logger()


def decode_wav_b64(payload: str) -> tuple[np.ndarray, int]:
    raw = base64.b64decode(payload)
    with wave.open(io.BytesIO(raw), "rb") as handle:
        rate = handle.getframerate()
        channels = handle.getnchannels()
        frames = handle.readframes(handle.getnframes())
        width = handle.getsampwidth()
    if width != 2:
        raise ValueError(f"只接受 16-bit wav，實際是 {width} bytes")
    pcm = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        pcm = pcm.reshape(-1, channels).mean(axis=1)
    return pcm, rate


def encode_wav_b64(pcm: np.ndarray, sample_rate: int) -> str:
    clipped = np.clip(pcm, -1.0, 1.0)
    ints = (clipped * 32767.0).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(ints.tobytes())
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _resample(pcm: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    if src_rate == dst_rate or pcm.size == 0:
        return pcm
    try:
        import soxr

        return soxr.resample(pcm, src_rate, dst_rate).astype(np.float32)
    except Exception:
        step = src_rate / dst_rate
        idx = np.arange(0, pcm.size, step)
        idx = np.clip(idx.astype(np.int64), 0, pcm.size - 1)
        return pcm[idx]


async def submit_wav(cmd: PluginCommands, wav_b64: str, user_name: str) -> None:
    """一段別人的話：送進小智做辨識，不把桌面的連續對話關掉."""
    AudioConfig.reload()
    pcm, rate = decode_wav_b64(wav_b64)
    pcm = _resample(pcm, rate, AudioConfig.INPUT_SAMPLE_RATE)
    frame = AudioConfig.INPUT_FRAME_SIZE
    if pcm.size < frame:
        return
    from src.audio_codecs.opus_codec import OpusCodec

    codec = OpusCodec(
        input_sample_rate=AudioConfig.INPUT_SAMPLE_RATE,
        output_sample_rate=AudioConfig.OUTPUT_SAMPLE_RATE,
        channels=AudioConfig.CHANNELS,
    )
    try:
        logger.info("Discord 收到 %s 的語音，送進小智", user_name or "某人")
        await cmd.start_listening(ListeningMode.MANUAL)
        offset = 0
        while offset + frame <= pcm.size:
            packet = codec.encode(pcm[offset : offset + frame], frame)
            await cmd.send_audio(packet)
            offset += frame
        await cmd.stop_listening()
    finally:
        codec.close()
