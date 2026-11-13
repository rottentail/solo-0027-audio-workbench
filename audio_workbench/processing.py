import array
import math
from .waveio import Audio


def number(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{name} must be a finite number between {low} and {high}')
    return value


def saturate(value):
    return max(-32768, min(32767, round(value)))


def inspect(audio):
    return {'sample_rate': audio.rate, 'channels': audio.channels, 'frames': audio.frames,
            'duration_seconds': audio.frames / audio.rate,
            'peak': max(abs(s) for s in audio.samples) / 32768}


def clip(audio, start, end, gain):
    start = number(start, 'start', 0, 30)
    end = number(end, 'end', 0, 30)
    gain = number(gain, 'gain', 0, 4)
    first, last = round(start * audio.rate), round(end * audio.rate)
    if first >= last or last > audio.frames:
        raise ValueError('clip interval must contain frames within the audio')
    samples = (saturate(s * gain) for s in audio.samples[first * audio.channels:last * audio.channels])
    return Audio(audio.rate, audio.channels, array.array('h', samples))


def mix(tracks):
    reference = tracks[0][0]
    for audio, offset, gain in tracks:
        if (audio.rate, audio.channels) != (reference.rate, reference.channels):
            raise ValueError('track formats must match')
        number(offset, 'offset', 0, 30)
        number(gain, 'gain', 0, 4)
    length = max(round(offset * reference.rate) + audio.frames for audio, offset, _ in tracks)
    if length > reference.rate * 30:
        raise ValueError('mixed audio exceeds 30 seconds')
    sums = [0.0] * (length * reference.channels)
    for audio, offset, gain in tracks:
        position = round(offset * audio.rate) * audio.channels
        for index, sample in enumerate(audio.samples):
            sums[position + index] += sample * gain
    return Audio(reference.rate, reference.channels, array.array('h', (saturate(x) for x in sums)))
