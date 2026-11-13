"""Construct constrained FFmpeg commands for supported output formats."""
import imageio_ffmpeg

PRESETS = {
    'mp4': ['-vf', 'scale=1280:720:force_original_aspect_ratio=decrease:force_divisible_by=2', '-r', '30', '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', '-c:a', 'aac'],
    'audio': ['-vn', '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le'],
}


def command(source, destination, options):
    fmt = 'mp4' if options['preset'] == 'mp4' else 'wav'
    return [imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-nostdin',
            '-ss', str(options['start']), '-i', str(source), '-t', str(options['duration']),
            *PRESETS[options['preset']], '-f', fmt, '-y', str(destination)]
