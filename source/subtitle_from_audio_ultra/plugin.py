#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    plugins.__init__.py

    Written by:               AudioscavengeR <dev@derewonko.com>
    Date:                     21 September 2026

    Copyright:
        Copyright (C) 2021 Josh.5 <jsunnex@gmail.com>, yajrendrag@gmail.com
        Copyright (C) 2026 AudioscavengeR <audioscavenger@gmail.com>

        Portions of this module rely on OpenAI's Whisper Speech Recognition which are governed by their license.

        This program is free software: you can redistribute it and/or modify it under the terms of the GNU General
        Public License as published by the Free Software Foundation, version 3.

        This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the
        implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
        for more details.

        You should have received a copy of the GNU General Public License along with this program.
        If not, see <https://www.gnu.org/licenses/>.

        Whisper Module:
        This Unmanic plugin module uses Whisper by OpenAI (<https://github.com/openai/whisper/>) which is governed by it's own
        license.  The text of this license has accompanied this program.  If for some reason you do not have it, please refer
        to <https://github.com/openai/whisper/blob/main/LICENSE/>.

        What this plugin does:
        For every audio stream in a video file, this plugin transcribes the stream with faster-whisper and writes
        out an external subtitle file named '{movie_file}.{lang}.srt'. If the "embed_subtitles" option is enabled,
        the generated subtitles are also muxed into the container when it is a format that supports soft subtitles
        (MKV/MP4/M4V).

"""
import logging
import hashlib
import os
from pathlib import Path
import subprocess
import shutil
import glob
import ctranslate2
from faster_whisper import WhisperModel
import ffmpeg
from langcodes import *
from langcodes.tag_parser import LanguageTagError

from unmanic.libs.unplugins.settings import PluginSettings

from subtitle_from_audio_ultra.lib.ffmpeg import Probe, Parser

from unmanic import config

# Configure plugin logger
logger = logging.getLogger("Unmanic.Plugin.subtitle_from_audio_ultra")

# Force DEBUG
logger.setLevel(logging.DEBUG)

# trick to show bold characters in the UI
normal_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
bold_chars   = "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
BOLD_MAP = str.maketrans(normal_chars, bold_chars)

# containers that support soft (muxed) subtitles - embedding is only attempted for these
EMBED_COMPATIBLE_FORMATS = ['mkv', 'mp4', 'm4v']


def get_file_extension(filepath: str):
    return os.path.splitext(filepath)[-1][1:].lower()


def is_embed_compatible(ext: str):
    return ext.lower() in EMBED_COMPATIBLE_FORMATS


class Settings(PluginSettings):
    settings = {
        "force_cpu": False,
        "model_name": "large-v3-turbo",
        "embed_subtitles": False,
        "force_overwrite": False,
    }
    # base: 55%
    # small: 73%
    # medium: 81%
    # large-v3-turbo: 84%

    def __init__(self, *args, **kwargs):
        super(Settings, self).__init__(*args, **kwargs)
        self.form_settings = {
            "force_cpu":    {
                "label":        "Disable GPU and run Whisper with {}".format('CPU'.translate(BOLD_MAP)),
                "description":  "Helpful if GPU processing crashes or doesn't release memory. Also bypasses the GPU check when you don't have a GPU",
            },
            "model_name":    {
                "label":        "Model",
                "description":  "Larger models need more GPU memory and produce more accurate transcriptions/subtitles. {} is fastest but least accurate.".format('tiny'.translate(BOLD_MAP)),
                "sub_setting":  True,
                "input_type":   "select",
                "select_options": [
                    {
                        "value": "tiny",
                        "label": "tiny: fastest, least accurate, 75 MB",
                    },
                    {
                        "value": "base",
                        "label": "base: 142 MB",
                    },
                    {
                        "value": "small",
                        "label": "small: 470MB",
                    },
                    {
                        "value": "large-v3-turbo",
                        "label": "turbo: 1.6GB FASTEST BESTEST",
                    },
                ],
            },
            "embed_subtitles":    {
                "label":        "Also embed subtitles in the container",
                "description":  "External SRT files are always created for every audio stream, named '{movie_file}.lang.srt'. Enabling this option additionally embeds the generated subtitles into the container when it's MKV/MP4/M4V.",
            },
            "force_overwrite":    {
                "label":        "Overwrite existing subtitles",
                "description":  "Without it, audio streams that already have a matching external SRT file (or, when embedding, an already-embedded subtitle track) are left untouched and not regenerated",
            },
        }


def get_audio_streams_with_positions(probe_streams):
    """
    Walk the probed streams and return a list of (position, stream) tuples for every audio stream,
    where 'position' is the index of that stream among audio streams only (i.e. what ffmpeg expects
    after '-map 0:a:').
    """
    result = []
    position = 0
    for stream in probe_streams:
        if stream.get('codec_type') == 'audio':
            result.append((position, stream))
            position += 1
    return result


def subtitles_need_generation(abspath, probe_streams, settings):
    """
    Decide whether a file should be queued for subtitle generation/embedding.
    """
    embed_subtitles = settings.get_setting('embed_subtitles')
    force_overwrite = settings.get_setting('force_overwrite')

    audio_streams = get_audio_streams_with_positions(probe_streams)
    if not audio_streams:
        return False

    if force_overwrite:
        return True

    base = os.path.splitext(abspath)[0]
    existing_srts = glob.glob(glob.escape(base) + ".*.srt")
    if len(existing_srts) < len(audio_streams):
        return True

    if embed_subtitles and is_embed_compatible(get_file_extension(abspath)):
        embedded_subs = sum(1 for s in probe_streams if s.get('codec_type') == 'subtitle')
        if embedded_subs < len(audio_streams):
            return True

    return False


def on_library_management_file_test(data, task_data_store=None, file_metadata=None):
    """
    Runner function - enables additional actions during the library management file tests.

    The 'data' object argument includes:
        library_id                      - The library that the current task is associated with
        path                            - String containing the full path to the file being tested.
        issues                          - List of currently found issues for not processing the file.
        add_file_to_pending_tasks       - Boolean, is the file currently marked to be added to the queue for processing.
        priority_score                  - Integer, an additional score that can be added to set the position of the new task in the task queue.
        shared_info                     - Dictionary, information provided by previous plugin runners. This can be appended to for subsequent runners.

    :param data:
    :return:

    """
    # Get the path to the original file
    abspath = data.get('path')

    # Configure settings object (maintain compatibility with v1 plugins)
    if data.get('library_id'):
        settings = Settings(library_id=data.get('library_id'))
    else:
        settings = Settings()

    # Get file probe
    probe = Probe(logger, allowed_mimetypes=['video'])
    if 'ffprobe' in data.get('shared_info', {}):
        if not probe.set_probe(data.get('shared_info', {}).get('ffprobe')):
            # Failed to set ffprobe from shared info.
            # Probably due to it being for an incompatible mimetype declared above
            return
    elif not probe.file(abspath):
        # File probe failed, skip the rest of this test
        return

    # Set file probe to shared info for subsequent file test runners
    if 'shared_info' not in data:
        data['shared_info'] = {}
    data['shared_info']['ffprobe'] = probe.get_probe()

    probe_streams = probe.get_probe()["streams"]

    # Check whether any audio stream is missing its subtitle file (or embedded track)
    if subtitles_need_generation(abspath, probe_streams, settings):
        data['add_file_to_pending_tasks'] = True
        logger.info("File '{}' should be added to task list. Subtitle generation is required.".format(abspath))
    else:
        logger.info("File '{}' should not be added to the task list. Subtitles already exist for all audio streams.".format(abspath))

    return data


def get_model(requested_model: str = 'large-v3-turbo'):
    """
    Attempts to load the requested Whisper model on CUDA. If it runs out of VRAM,
    it automatically falls back to progressively smaller models.
    If CUDA fails entirely, falls back to CPU using the originally requested model size.
    """

    device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"

    # Define models ordered from largest/most demanding to smallest
    # (Note: turbo is placed above medium as it generally requires slightly more VRAM/compute footprint than medium)
    model_hierarchy = ['large-v3-turbo', 'small', 'base', 'tiny']

    # Clean user input and ensure it's a valid choice
    requested_model = requested_model.lower().strip()
    if requested_model not in model_hierarchy:
        logger.warning(f"Unknown model '{requested_model}', defaulting to 'large-v3-turbo'")
        requested_model = 'large-v3-turbo'

    # Get the index of the requested model and slice the list to only test that model and smaller
    start_idx = model_hierarchy.index(requested_model)
    candidate_models = model_hierarchy[start_idx:]

    if device == "cuda":
        # Test if model fits (cascading downward)
        for current_model in candidate_models:
            try:
                logger.info(f"Attempting to load Whisper model '{current_model}' on CUDA...")
                model = WhisperModel(current_model, device="cuda", compute_type="float16")
                # Successfully loaded!
                logger.info(f"Successfully loaded '{current_model}' on CUDA.")
                del model
                return current_model, 'cuda', "float16"

            # CTranslate2 doesn't expose a distinct OOM exception class through faster-whisper - CUDA OOM
            # just surfaces as a plain RuntimeError, same as any other load failure
            except RuntimeError as e:
                logger.warning(f"Failed to load '{current_model}' on CUDA: {e}")
                continue
    else:
        logger.info("No GPU detected: Whisper will run on CPU.")

    # If we are CPU, or exhausted the loop, or hit a driver crash, fall back to CPU using the user's requested model
    # no test is performed as whisper cpu always works
    return requested_model, 'cpu', "int8"


def format_timestamp(seconds: float) -> str:
    """
    Format a number of seconds as an SRT timestamp: HH:MM:SS,mmm
    """
    if seconds < 0:
        seconds = 0
    total_millis = round(seconds * 1000)
    hours, total_millis = divmod(total_millis, 3600000)
    minutes, total_millis = divmod(total_millis, 60000)
    secs, millis = divmod(total_millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt_file(segments, srt_path):
    """
    Write out a list of faster-whisper segments (objects with .start, .end, .text) as an SRT file.
    """
    with open(srt_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(segments, start=1):
            text = segment.text.strip()
            if not text:
                continue
            f.write(f"{i}\n")
            f.write(f"{format_timestamp(segment.start)} --> {format_timestamp(segment.end)}\n")
            f.write(f"{text}\n\n")


def extract_audio_wav(vid_file, astream, tmp_dir):
    """
    Extract a single audio stream (by its position among audio streams) from vid_file into a mono,
    16kHz WAV file suitable for Whisper.
    """
    wav_path = os.path.join(tmp_dir, f"astream_{astream}.wav")
    command = [
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
        '-i', str(vid_file),
        '-map', f'0:a:{astream}',
        '-vn', '-ac', '1', '-ar', '16000', '-acodec', 'pcm_s16le',
        wav_path
    ]
    logger.debug(f"extract_audio_wav command: {command}")

    try:
        subprocess.run(command, shell=False, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        logger.error("Failed to extract audio stream '{}' from file '{}': {}".format(astream, vid_file, e.stderr.decode()))
        return None
    except OSError as e:
        logger.error(f"OSError extracting audio stream '{astream}': {e}")
        return None

    return wav_path


def transcribe_audio(wav_path, settings):
    """
    Run Whisper on a single-audio-stream WAV file. Returns (segments, language_alpha2).
    Language is auto-detected by Whisper from the audio itself.
    """
    force_cpu = settings.get_setting("force_cpu")
    model_name = settings.get_setting("model_name")

    if force_cpu:
        device, compute_type = 'cpu', 'int8'
    else:
        model_name, device, compute_type = get_model(model_name)

    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    logger.debug(f"transcribing '{wav_path}' with model '{model_name}' on '{device}'")

    segments_generator, info = model.transcribe(wav_path, beam_size=5, vad_filter=True)
    segments = list(segments_generator)

    logger.debug("detected language '{}' with probability {:.2f}".format(info.language, info.language_probability))

    try:
        del model
    except Exception:
        pass

    return segments, info.language


def generate_subtitles_for_file(vid_file, probe_streams, settings):
    """
    For every audio stream in vid_file, ensure an external SRT sidecar file exists, named
    '{vid_file_basename}.{lang}.srt' (or '{vid_file_basename}.{lang}.{astream}.srt' if more than
    one stream shares the same detected language).

    Streams that already carry a language tag matching an existing SRT file are skipped (unless
    force_overwrite is set), avoiding an unnecessary transcription pass.

    Returns a list of dicts: {'astream': position, 'lang3': code, 'srt_path': path, 'newly_generated': bool}
    """
    force_overwrite = settings.get_setting('force_overwrite')
    base = os.path.splitext(vid_file)[0]

    audio_streams = get_audio_streams_with_positions(probe_streams)
    if not audio_streams:
        return []

    settings2 = config.Config()
    cache_path = settings2.get_cache_path()
    src_file_hash = hashlib.md5(os.path.basename(vid_file).encode('utf8')).hexdigest()
    tmp_dir = os.path.join(cache_path, '{}'.format(src_file_hash))
    Path(tmp_dir).mkdir(parents=True, exist_ok=True)

    results = []
    used_lang_codes = {}

    for astream, stream_meta in audio_streams:
        # If this stream already carries a language tag, check whether a matching SRT already exists
        # so we can skip re-transcribing it when not forcing overwrite.
        tags = stream_meta.get('tags', {}) or {}
        hint_tag = tags.get('language')
        hint_lang3 = None
        if hint_tag and hint_tag != 'und':
            try:
                hint_lang3 = Language.get(standardize_tag(hint_tag)).to_alpha3()
            except (LanguageTagError, TypeError, AttributeError):
                hint_lang3 = None

        if hint_lang3 and not force_overwrite:
            candidate_count = used_lang_codes.get(hint_lang3, 0) + 1
            suffix = hint_lang3 if candidate_count == 1 else f"{hint_lang3}.{astream}"
            candidate_path = f"{base}.{suffix}.srt"
            if os.path.exists(candidate_path):
                used_lang_codes[hint_lang3] = candidate_count
                logger.info(f"SRT '{candidate_path}' already exists for audio stream {astream}, skipping")
                results.append({'astream': astream, 'lang3': hint_lang3, 'srt_path': candidate_path, 'newly_generated': False})
                continue

        wav_path = extract_audio_wav(vid_file, astream, tmp_dir)
        if wav_path is None:
            continue

        try:
            segments, lang2 = transcribe_audio(wav_path, settings)
        except Exception as e:
            logger.error(f"Failed to transcribe audio stream {astream} of '{vid_file}': {e}")
            continue
        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)

        if not segments:
            logger.warning(f"No speech detected for audio stream {astream} of '{vid_file}', skipping")
            continue

        try:
            lang3 = Language.get(standardize_tag(lang2)).to_alpha3()
        except (LanguageTagError, TypeError, AttributeError):
            lang3 = "und"

        candidate_count = used_lang_codes.get(lang3, 0) + 1
        used_lang_codes[lang3] = candidate_count
        suffix = lang3 if candidate_count == 1 else f"{lang3}.{astream}"
        srt_path = f"{base}.{suffix}.srt"

        if os.path.exists(srt_path) and not force_overwrite:
            logger.info(f"SRT '{srt_path}' already exists, skipping regeneration")
            results.append({'astream': astream, 'lang3': lang3, 'srt_path': srt_path, 'newly_generated': False})
            continue

        write_srt_file(segments, srt_path)
        logger.info(f"Created subtitle file '{srt_path}' for audio stream {astream}")
        results.append({'astream': astream, 'lang3': lang3, 'srt_path': srt_path, 'newly_generated': True})

    shutil.rmtree(tmp_dir, ignore_errors=True)
    return results


def on_worker_process(data):
    """
    Runner function - enables additional configured processing jobs during the worker stages of a task.

    The 'data' object argument includes:
        exec_command            - A command that Unmanic should execute. Can be empty.
        command_progress_parser - A function that Unmanic can use to parse the STDOUT of the command to collect progress stats. Can be empty.
        file_in                 - The source file to be processed by the command.
        file_out                - The destination that the command should output (may be the same as the file_in if necessary).
        original_file_path      - The absolute path to the original file.
        repeat                  - Boolean, should this runner be executed again once completed with the same variables.

    DEPRECIATED 'data' object args passed for legacy Unmanic versions:
        exec_ffmpeg             - Boolean, should Unmanic run FFMPEG with the data returned from this plugin.
        ffmpeg_args             - A list of Unmanic's default FFMPEG args.

    :param data:
    :return:

    """
    # Default to no FFMPEG command required. This prevents the FFMPEG command from running if it is not required
    data['exec_command'] = []
    data['repeat'] = False

    # Get the input and output file paths
    abspath = data.get('file_in')
    outfile = data.get('file_out')
    original_file_path = data.get('original_file_path', abspath)

    logger.debug(f"worker process output file: {outfile}")

    # Get file probe
    probe_data = Probe(logger, allowed_mimetypes=['video'])
    if probe_data.file(abspath):
        probe_streams = probe_data.get_probe()["streams"]
    else:
        logger.debug("Probe data failed - Blocking everything.")
        return data

    if data.get('library_id'):
        settings = Settings(library_id=data.get('library_id'))
    else:
        settings = Settings()

    embed_subtitles = settings.get_setting('embed_subtitles')
    force_overwrite = settings.get_setting('force_overwrite')

    # Always (re)generate the external SRT sidecar files for every audio stream that needs it.
    # The SRT files are named against the *original* file path so they sit alongside the movie file.
    generated = generate_subtitles_for_file(original_file_path, probe_streams, settings)

    if not generated:
        logger.info("File not processed - no audio streams available or nothing to transcribe")
        return data

    if not embed_subtitles:
        logger.info("External SRT files created; embedding not requested for this file")
        return data

    ext = get_file_extension(outfile)
    if not is_embed_compatible(ext):
        logger.info(f"External SRT files created; container '.{ext}' does not support embedded subtitles")
        return data

    # Work out which languages are already embedded so we don't duplicate them unless forcing overwrite
    existing_subtitle_langs = set()
    existing_sub_count = 0
    for stream in probe_streams:
        if stream.get('codec_type') == 'subtitle':
            existing_sub_count += 1
            lang = (stream.get('tags', {}) or {}).get('language')
            if lang:
                existing_subtitle_langs.add(lang)

    to_embed = [
        g for g in generated
        if force_overwrite or g['lang3'] not in existing_subtitle_langs
    ]

    if not to_embed:
        logger.info("Subtitles already embedded for all detected languages - no muxing required")
        return data

    sub_codec = 'mov_text' if ext in ('mp4', 'm4v') else 'srt'

    command = ['ffmpeg', '-hide_banner', '-loglevel', 'info', '-y', '-i', str(abspath)]
    for g in to_embed:
        command += ['-i', g['srt_path']]

    command += ['-max_muxing_queue_size', '4096', '-map', '0']
    for i in range(len(to_embed)):
        command += ['-map', f'{i + 1}:s']

    command += ['-c', 'copy', '-c:s', sub_codec]

    for i, g in enumerate(to_embed):
        command += [f'-metadata:s:s:{existing_sub_count + i}', f'language={g["lang3"]}']

    command += [outfile]

    data['exec_command'] = command
    logger.debug("command: '{}'".format(data['exec_command']))

    # Set the parser
    parser = Parser(logger)
    parser.set_probe(probe_data)
    data['command_progress_parser'] = parser.parse_progress

    return data