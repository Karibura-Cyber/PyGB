"""Audio subsystem — four Game Boy sound channels.

Channel 1 : Pulse with frequency sweep  (sound effects, lead melody)
Channel 2 : Pulse                        (harmony)
Channel 3 : Programmable wave            (custom waveforms)
Channel 4 : Noise                        (drums, explosions)

Sounds are generated as 16-bit PCM and played via pygame.mixer.
"""

from __future__ import annotations
import math
import random
import struct
from typing import Optional

SAMPLE_RATE = 44100


def _to_sound(samples_16bit: bytearray):
    """Wrap raw stereo 16-bit PCM bytes in a pygame Sound object."""
    import pygame
    return pygame.mixer.Sound(buffer=bytes(samples_16bit))


def _pack_stereo(buf: bytearray, i: int, val: int) -> None:
    """Write a stereo sample (left + right) at byte offset i*4."""
    clamped = max(-32768, min(32767, val))
    struct.pack_into("<hh", buf, i * 4, clamped, clamped)


def _square_wave(
    freq: float,
    duration_ms: float,
    volume: float = 0.5,
    duty: float = 0.5,
) -> bytearray:
    """Generate a stereo 16-bit square wave PCM buffer at the given frequency."""
    n = max(1, int(SAMPLE_RATE * duration_ms / 1000))
    buf = bytearray(n * 4)  # stereo 16-bit
    period = SAMPLE_RATE / max(freq, 1.0)
    amp = int(32767 * volume)
    for i in range(n):
        phase = (i % period) / period
        val = amp if phase < duty else -amp
        _pack_stereo(buf, i, val)
    return buf


def _noise_wave(duration_ms: float, volume: float = 0.5) -> bytearray:
    """Generate a stereo 16-bit white-noise PCM buffer."""
    n = max(1, int(SAMPLE_RATE * duration_ms / 1000))
    buf = bytearray(n * 4)
    amp = int(32767 * volume)
    for i in range(n):
        val = random.randint(-amp, amp)
        _pack_stereo(buf, i, val)
    return buf


def _wave_channel(
    wavetable: list[int],  # 32 4-bit samples (0–15)
    freq: float,
    duration_ms: float,
    volume: float = 0.5,
) -> bytearray:
    """Generate a stereo 16-bit PCM buffer by cycling through a 32-entry wavetable."""
    n = max(1, int(SAMPLE_RATE * duration_ms / 1000))
    buf = bytearray(n * 4)
    period = SAMPLE_RATE / max(freq, 1.0)
    amp = int(32767 * volume)
    for i in range(n):
        phase = (i % period) / period
        sample_idx = int(phase * 32) % 32
        val = int((wavetable[sample_idx] / 15.0 * 2 - 1) * amp)
        _pack_stereo(buf, i, val)
    return buf


class Channel:
    """One of the four GB audio channels."""

    def __init__(self, channel_id: int) -> None:
        """Initialize a mixer channel with the given pygame channel ID."""
        self._id = channel_id
        self._pygame_channel = None
        self._volume = 1.0

    def _get_channel(self):
        """Return the pygame mixer channel, creating it lazily on first access."""
        import pygame
        if self._pygame_channel is None:
            self._pygame_channel = pygame.mixer.Channel(self._id)
        return self._pygame_channel

    def play_sound(self, sound, loops: int = 0) -> None:
        """Play a pygame Sound object on this channel, optionally looping."""
        try:
            self._get_channel().play(sound, loops=loops)
        except Exception:
            pass

    def stop(self) -> None:
        """Stop playback on this channel immediately."""
        try:
            self._get_channel().stop()
        except Exception:
            pass

    def is_busy(self) -> bool:
        """Return True if this channel is currently playing a sound."""
        try:
            return self._get_channel().get_busy()
        except Exception:
            return False

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        self._volume = max(0.0, min(1.0, value))
        try:
            self._get_channel().set_volume(self._volume)
        except Exception:
            pass


class PulseChannel(Channel):
    """Square-wave channel (Ch1 and Ch2)."""

    def __init__(self, channel_id: int, has_sweep: bool = False) -> None:
        """Create a pulse channel; set has_sweep=True for Ch1 frequency sweep support."""
        super().__init__(channel_id)
        self.has_sweep = has_sweep
        self.duty = 0.5  # 12.5%, 25%, 50%, 75%

    def tone(
        self,
        frequency: float,
        duration_ms: float = 100,
        volume: Optional[float] = None,
        duty: Optional[float] = None,
        loops: int = 0,
    ) -> None:
        """Play a square wave at *frequency* Hz for *duration_ms* milliseconds."""
        vol = volume if volume is not None else self._volume
        d   = duty   if duty   is not None else self.duty
        buf = _square_wave(frequency, duration_ms, vol, d)
        self.play_sound(_to_sound(buf), loops)

    def note(self, note: str, octave: int = 4, duration_ms: float = 200) -> None:
        """Play a musical note by name, e.g. note('C', 4)."""
        freq = _note_to_freq(note, octave)
        self.tone(freq, duration_ms)


class WaveChannel(Channel):
    """Programmable wave channel (Ch3) — uses a 32-sample wavetable."""

    SINE = [int((math.sin(2 * math.pi * i / 32) * 0.5 + 0.5) * 15) for i in range(32)]
    SAWTOOTH = [int(i / 31 * 15) for i in range(32)]
    TRIANGLE = [int(abs(i - 16) / 16 * 15) for i in range(32)]

    def __init__(self, channel_id: int) -> None:
        """Initialize the wave channel with a default sine wavetable."""
        super().__init__(channel_id)
        self.wavetable: list[int] = self.SINE[:]

    def play(self, frequency: float, duration_ms: float = 200) -> None:
        """Play the current wavetable at *frequency* Hz for *duration_ms* milliseconds."""
        buf = _wave_channel(self.wavetable, frequency, duration_ms, self._volume)
        self.play_sound(_to_sound(buf))

    def set_waveform(self, samples: list[int]) -> None:
        """Set 32 samples, each 0–15."""
        if len(samples) != 32:
            raise ValueError("Wave channel needs exactly 32 samples")
        self.wavetable = [max(0, min(15, int(s))) for s in samples]


class NoiseChannel(Channel):
    """LFSR noise channel (Ch4) — for drums and explosions."""

    def burst(self, duration_ms: float = 100, volume: Optional[float] = None) -> None:
        """Play a burst of white noise for *duration_ms* milliseconds."""
        vol = volume if volume is not None else self._volume
        buf = _noise_wave(duration_ms, vol)
        self.play_sound(_to_sound(buf))


class Audio:
    """Main audio system — exposes ch1–ch4 matching GB hardware."""

    def __init__(self) -> None:
        """Create all four GB audio channels (ch1–ch4)."""
        self.ch1 = PulseChannel(0, has_sweep=True)
        self.ch2 = PulseChannel(1)
        self.ch3 = WaveChannel(2)
        self.ch4 = NoiseChannel(3)
        self._master_volume = 1.0

    def init(self) -> None:
        """Initialize pygame mixer at 44100 Hz stereo 16-bit for GB-style audio."""
        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)
        pygame.mixer.set_num_channels(4)

    def beep(
        self,
        freq: float = 440,
        duration_ms: float = 100,
        channel: int = 0,
        volume: float = 0.5,
    ) -> None:
        """Quick square-wave beep on the given channel (0–3)."""
        ch = [self.ch1, self.ch2, self.ch3, self.ch4][channel % 4]
        if isinstance(ch, PulseChannel):
            ch.tone(freq, duration_ms, volume)
        elif isinstance(ch, WaveChannel):
            ch.play(freq, duration_ms)
        elif isinstance(ch, NoiseChannel):
            ch.burst(duration_ms, volume)

    def stop_all(self) -> None:
        """Stop playback on all four channels immediately."""
        for ch in (self.ch1, self.ch2, self.ch3, self.ch4):
            ch.stop()

    @property
    def master_volume(self) -> float:
        return self._master_volume

    @master_volume.setter
    def master_volume(self, value: float) -> None:
        self._master_volume = max(0.0, min(1.0, value))
        try:
            import pygame
            pygame.mixer.music.set_volume(self._master_volume)
        except Exception:
            pass


# Note → frequency helpers
_NOTE_SEMITONES = {
    "C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3,
    "E": 4, "F": 5, "F#": 6, "GB": 6, "G": 7, "G#": 8,
    "AB": 8, "A": 9, "A#": 10, "BB": 10, "B": 11,
}


def _note_to_freq(note: str, octave: int = 4) -> float:
    """Convert a note name (e.g. 'C#') and octave number to a frequency in Hz."""
    semitone = _NOTE_SEMITONES.get(note.upper().replace("b", "B"))
    if semitone is None:
        raise ValueError(f"Unknown note: {note!r}")
    n = (octave - 4) * 12 + semitone
    return 440.0 * (2 ** (n / 12))
