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
        out an external subtitle file named '{movie_file}.{lang}.srt' (2-letter language code). If the
        "embed_subtitles" option is enabled, the generated subtitles are also muxed into the container when it is a
        format that supports soft subtitles (MKV/MP4/M4V). Optionally, a "multilingual" mode independently detects
        the language of each spoken segment rather than assuming one language for the whole stream, so foreign
        language passages (e.g. a song in a different language than the main dialogue) are transcribed correctly.

"""
import logging
import hashlib
import os
from pathlib import Path
import subprocess
import shutil
import glob
import copy
import dataclasses
import ctranslate2
from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio
try:
    from faster_whisper.vad import get_speech_timestamps, VadOptions
except ImportError:  # pragma: no cover - depends on faster-whisper version
    get_speech_timestamps = None
    VadOptions = None
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

# subtitle timing tuning
MAX_SUBTITLE_GAP = 0.15       # seconds of breathing room left before the next line starts
MAX_SUBTITLE_DURATION = 7.0   # cap on how long a single line can stay on screen with no better evidence

# sentinel code (registered IANA/ISO-639-2 tag) used when a stream mixes multiple languages
MULTI_LANGUAGE_CODE = 'mul'


def get_file_extension(filepath: str):
    return os.path.splitext(filepath)[-1][1:].lower()


def is_embed_compatible(ext: str):
    return ext.lower() in EMBED_COMPATIBLE_FORMATS


def normalize_lang(tag):
    """
    Normalize a language tag (2 or 3 letter, or a legacy code) into (lang2, lang3).
    Returns (None, None) if the tag is missing, 'und', or not a real language.
    Special-cases the 'mul' (multiple languages) sentinel, which langcodes doesn't treat as a
    normal language.
    """
    if not tag or tag == 'und':
        return None, None
    if tag == MULTI_LANGUAGE_CODE:
        return MULTI_LANGUAGE_CODE, MULTI_LANGUAGE_CODE
    try:
        lang_obj = Language.get(standardize_tag(tag))
        if not lang_obj.is_valid():
            return None, None
        return lang_obj.language, lang_obj.to_alpha3()
    except (LanguageTagError, TypeError, AttributeError):
        return None, None


class Settings(PluginSettings):
    settings = {
        "force_cpu": False,
        "model_name": "small",
        "embed_subtitles": False,
        "force_overwrite": False,
        "multilingual": False,
    }
    # base: 55%
    # small: 73%
    # medium: 81%
    # large: 84%

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
            "multilingual":    {
                "label":        "Detect foreign-language segments (slower)",
                "description":  "By default the whole audio stream is transcribed assuming a single detected language. Enable this to detect the language independently for each spoken segment, so passages in a different language (e.g. a Japanese song in an English dub) are transcribed correctly too. This runs language detection many more times and noticeably increases processing time.",
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


def get_model(requested_model: str = 'small'):
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
        logger.warning(f"Unknown model '{requested_model}', defaulting to 'small'")
        requested_model = 'small'

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


def adjust_segment_timings(segments):
    """
    Whisper's raw segment.end timestamps are sometimes inflated (e.g. rounded up to a decoding
    chunk boundary), which makes a subtitle visually "hang" on screen well past when the line was
    actually spoken - right up until the next line appears. This tightens each segment's end time:
      - prefer the end of the last transcribed *word*, when word-level timestamps are available
      - never let a line overlap into the next line's start
      - cap how long a line can stay on screen when there's no better evidence for its end time

    Returns a list of (start, end, text) tuples in the same order as the input segments.
    """
    adjusted = []
    for i, segment in enumerate(segments):
        start = segment.start
        end = segment.end

        words = getattr(segment, 'words', None)
        if words:
            end = words[-1].end

        if end <= start:
            end = start + 0.5

        if end - start > MAX_SUBTITLE_DURATION:
            end = start + MAX_SUBTITLE_DURATION

        if i + 1 < len(segments):
            next_start = segments[i + 1].start
            if end > next_start - MAX_SUBTITLE_GAP:
                end = max(start + 0.5, next_start - MAX_SUBTITLE_GAP)

        adjusted.append((start, end, segment.text))

    return adjusted


def write_srt_file(segments, srt_path):
    """
    Write out a list of faster-whisper segments as an SRT file, with tightened display timings.
    """
    adjusted = adjust_segment_timings(segments)
    with open(srt_path, 'w', encoding='utf-8') as f:
        idx = 1
        for start, end, text in adjusted:
            text = text.strip()
            if not text:
                continue
            f.write(f"{idx}\n")
            f.write(f"{format_timestamp(start)} --> {format_timestamp(end)}\n")
            f.write(f"{text}\n\n")
            idx += 1


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


def _replace_fields(obj, **kwargs):
    """
    Return a copy of obj with the given fields updated, regardless of whether obj is a namedtuple
    (has ._replace), a dataclass, or a plain object. faster-whisper's Segment and Word classes have
    varied between versions, so this avoids assuming either one supports a specific replace API.
    """
    if hasattr(obj, '_replace'):
        return obj._replace(**kwargs)
    if dataclasses.is_dataclass(obj):
        return dataclasses.replace(obj, **kwargs)
    new_obj = copy.copy(obj)
    for key, value in kwargs.items():
        setattr(new_obj, key, value)
    return new_obj


def _shift_segment(segment, offset):
    """
    Shift a chunk-relative faster-whisper Segment (and its words, if present) back into the
    timeline of the whole audio stream.
    """
    if offset == 0:
        return segment
    new_words = None
    words = getattr(segment, 'words', None)
    if words:
        new_words = [_replace_fields(w, start=w.start + offset, end=w.end + offset) for w in words]
    return _replace_fields(segment, start=segment.start + offset, end=segment.end + offset, words=new_words)


def _transcribe_multilingual(model, wav_path):
    """
    Instead of assuming a single language for the whole stream, find speech chunks first (via VAD)
    and transcribe each one independently so foreign-language passages (e.g. a song in a different
    language than the main dialogue) get their own language detection instead of being forced
    through the dominant language. Considerably slower, since the model runs once per speech chunk.

    Returns (segments, language_code) where language_code is a 2-letter code, or 'mul' if more than
    one language made up a meaningful share of the total speech duration.
    """
    if get_speech_timestamps is None:
        logger.warning("faster_whisper.vad.get_speech_timestamps is unavailable, falling back to single-pass transcription")
        segments_generator, info = model.transcribe(wav_path, beam_size=5, vad_filter=True, word_timestamps=True)
        return list(segments_generator), info.language

    audio = decode_audio(wav_path, sampling_rate=16000)

    try:
        speech_chunks = get_speech_timestamps(audio, vad_options=VadOptions(min_silence_duration_ms=500))
    except Exception as e:
        logger.warning(f"VAD chunking failed ({e}), falling back to single-pass transcription")
        segments_generator, info = model.transcribe(wav_path, beam_size=5, vad_filter=True, word_timestamps=True)
        return list(segments_generator), info.language

    if not speech_chunks:
        return [], None

    all_segments = []
    lang_durations = {}

    for chunk in speech_chunks:
        start_sample, end_sample = chunk['start'], chunk['end']
        chunk_audio = audio[start_sample:end_sample]
        offset = start_sample / 16000.0
        duration = (end_sample - start_sample) / 16000.0

        try:
            segs_generator, info = model.transcribe(chunk_audio, beam_size=5, word_timestamps=True)
        except Exception as e:
            logger.warning(f"Failed to transcribe speech chunk at {offset:.1f}s: {e}")
            continue

        lang_durations[info.language] = lang_durations.get(info.language, 0) + duration

        for seg in segs_generator:
            all_segments.append(_shift_segment(seg, offset))

    if not lang_durations:
        return all_segments, None

    total_duration = sum(lang_durations.values())
    significant_langs = [lang for lang, dur in lang_durations.items() if dur / total_duration > 0.05]
    if len(significant_langs) > 1:
        overall_lang = MULTI_LANGUAGE_CODE
    else:
        overall_lang = max(lang_durations, key=lang_durations.get)

    return all_segments, overall_lang


def transcribe_audio(wav_path, settings):
    """
    Run Whisper on a single-audio-stream WAV file. Returns (segments, language_code).
    In single-pass mode the language is auto-detected once for the whole stream; in multilingual
    mode it is detected independently per speech chunk (see _transcribe_multilingual).
    """
    force_cpu = settings.get_setting("force_cpu")
    model_name = settings.get_setting("model_name")
    multilingual = settings.get_setting("multilingual")

    if force_cpu:
        device, compute_type = 'cpu', 'int8'
    else:
        model_name, device, compute_type = get_model(model_name)

    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    logger.debug(f"transcribing '{wav_path}' with model '{model_name}' on '{device}' (multilingual={multilingual})")

    if multilingual:
        segments, lang_raw = _transcribe_multilingual(model, wav_path)
    else:
        segments_generator, info = model.transcribe(wav_path, beam_size=5, vad_filter=True, word_timestamps=True)
        segments = list(segments_generator)
        lang_raw = info.language
        logger.debug("detected language '{}' with probability {:.2f}".format(info.language, info.language_probability))

    try:
        del model
    except Exception:
        pass

    return segments, lang_raw


def generate_subtitles_for_file(vid_file, probe_streams, settings):
    """
    For every audio stream in vid_file, ensure an external SRT sidecar file exists, named
    '{vid_file_basename}.{lang}.srt' using a 2-letter language code (or '{vid_file_basename}.mul.srt'
    when multilingual mode detects more than one language in the stream, or with a trailing stream
    index if more than one stream shares the same code).

    Streams that already carry a language tag matching an existing SRT file are skipped (unless
    force_overwrite is set), avoiding an unnecessary transcription pass.

    Returns a list of dicts: {'astream': position, 'lang2': code, 'lang3': code, 'srt_path': path, 'newly_generated': bool}
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
        hint_lang2, hint_lang3 = normalize_lang(tags.get('language'))

        if hint_lang2 and not force_overwrite:
            candidate_count = used_lang_codes.get(hint_lang2, 0) + 1
            suffix = hint_lang2 if candidate_count == 1 else f"{hint_lang2}.{astream}"
            candidate_path = f"{base}.{suffix}.srt"
            if os.path.exists(candidate_path):
                used_lang_codes[hint_lang2] = candidate_count
                logger.info(f"SRT '{candidate_path}' already exists for audio stream {astream}, skipping")
                results.append({'astream': astream, 'lang2': hint_lang2, 'lang3': hint_lang3, 'srt_path': candidate_path, 'newly_generated': False})
                continue

        wav_path = extract_audio_wav(vid_file, astream, tmp_dir)
        if wav_path is None:
            continue

        try:
            segments, lang_raw = transcribe_audio(wav_path, settings)
        except Exception as e:
            logger.error(f"Failed to transcribe audio stream {astream} of '{vid_file}': {e}")
            continue
        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)

        if not segments:
            logger.warning(f"No speech detected for audio stream {astream} of '{vid_file}', skipping")
            continue

        lang2, lang3 = normalize_lang(lang_raw)
        if lang2 is None:
            lang2, lang3 = "und", "und"

        candidate_count = used_lang_codes.get(lang2, 0) + 1
        used_lang_codes[lang2] = candidate_count
        suffix = lang2 if candidate_count == 1 else f"{lang2}.{astream}"
        srt_path = f"{base}.{suffix}.srt"

        if os.path.exists(srt_path) and not force_overwrite:
            logger.info(f"SRT '{srt_path}' already exists, skipping regeneration")
            results.append({'astream': astream, 'lang2': lang2, 'lang3': lang3, 'srt_path': srt_path, 'newly_generated': False})
            continue

        write_srt_file(segments, srt_path)
        logger.info(f"Created subtitle file '{srt_path}' for audio stream {astream}")
        results.append({'astream': astream, 'lang2': lang2, 'lang3': lang3, 'srt_path': srt_path, 'newly_generated': True})

    shutil.rmtree(tmp_dir, ignore_errors=True)
    return results


def on_worker_process(data, task_data_store=None, file_metadata=None):
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

    command += ['-max_muxing_queue_size', '9999', '-map', '0']
    for i in range(len(to_embed)):
        command += ['-map', f'{i + 1}:s']

    command += ['-c', 'copy']

    for i, g in enumerate(to_embed):
        out_sub_index = existing_sub_count + i
        command += [f'-c:s:{out_sub_index}', sub_codec]
        command += [f'-metadata:s:s:{out_sub_index}', f'language={g["lang3"]}']

    command += [outfile]

    data['exec_command'] = command
    logger.debug("command: '{}'".format(data['exec_command']))

    # Set the parser
    parser = Parser(logger)
    parser.set_probe(probe_data)
    data['command_progress_parser'] = parser.parse_progress

    return data