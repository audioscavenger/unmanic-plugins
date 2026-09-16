#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    Written by:               AudioscavengeR <dev@derewonko.com>
    Date:                     16 September 2026

    Copyright:
        Unmanic plugin code Copyright (C) 2026 Eric Derewonko
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

"""
import logging
import hashlib
import os
import whisper
# from faster_whisper import WhisperModel
from pathlib import Path
import subprocess
import random
import shutil
import os
import glob
import torch
import ffmpeg
from langcodes import *
from langcodes.tag_parser import LanguageTagError

from unmanic.libs.unplugins.settings import PluginSettings

from language_whisper_ultra.lib.ffmpeg import Probe, Parser

from unmanic import config

# Configure plugin logger
logger = logging.getLogger("Unmanic.Plugin.language_whisper_ultra")

class Settings(PluginSettings):
    settings = {
        "force_cpu": False,
        "model_name": "small",
        "force_rescan": False,
        "force_samples": False,
        "samples": 3,
        "tag_style": "3",
    }
    # base: 55%
    # small: 73%
    # medium: 81%
    # large: 84%

    def __init__(self, *args, **kwargs):
        super(Settings, self).__init__(*args, **kwargs)
        self.form_settings = {
            "force_cpu":    {
                "label":        "Disable GPU and run Whisper with CPU.",
                "description":  "Helpful if GPU processing crash or don't release memory. Also bypass the GPU check when you don't have a GPU.",
            },
            "model_name":    {
                "label":        "Whisper Mode;",
                "description":  "Larger models need more GPU memory. Base is correct 100% for mainstream Western languages and Japanese/Chinese",
                "sub_setting":  True,
                "input_type":   "select",
                "select_options": [
                    {
                        "value": "tiny",
                        "label": "tiny: 50% accuracy, 75 MB",
                    },
                    {
                        "value": "base",
                        "label": "base: 55% accuracy, 142 MB",
                    },
                    {
                        "value": "small",
                        "label": "small: 73% accuracy, 470MB",
                    },
                    {
                        "value": "medium",
                        "label": "medium: 81% accuracy, 1.5GB",
                    },
                    {
                        "value": "turbo",
                        "label": "turbo: 84% accuracy, 1.6GB FASTEST BESTEST",
                    },
                ],
            },
            "force_rescan":    {
                "label":        "Force reprocess all audio tracks",
            },
            "force_samples":    {
                "label":        "Input your own odd number of 30s samples",
                "description":  "Use only odd numbers: the logic is to elect a winner when multiple languages are detected.",
            },
            "samples":        self.__set_samples(),
            "tag_style": {
                "label":        "Language Tag Style",
                "description":  "Select 2 or 3 characters language tags: en or eng?",
                "input_type":   "select",
                "select_options": [
                    {
                        "value": "2",
                        "label": "2 chars: en",
                    },
                    {
                        "value": "3",
                        "label": "3 chars: eng",
                    },
                ],
            }
        }

    def __set_samples(self):
        values = {
            "label":        "30s samples",
            "description":  "3 samples are sufficient but you do you",
            "sub_setting":  True,
            "input_type":   "slider",
            "slider_options": {
                "min": 1,
                "max": 9,
                "step": 2,
            },
        }
        if not self.get_setting('force_samples'):
            values["display"] = 'hidden'
        return values


def get_audio_streams(probe_streams, force_rescan=False):

    # Get settings and test astreams for language, return the position of that stream among audio streams only
    astreams = []
    firstAudio = True
    minus = 0
    for i in range(len(probe_streams)):
      if probe_streams[i]['codec_type'] == 'audio':
        if firstAudio:
          minus = i
        if force_rescan:
          astreams.append(i - minus)
        else:
          if 'tags' in probe_streams[i]:
            if 'language' in probe_streams[i]['tags']:
              if probe_streams[i]['tags']['language'] == 'und':
                astreams.append(i - minus)
            else:
              astreams.append(i - minus)
          else:
            astreams.append(i - minus)

    return astreams


def on_library_management_file_test(data):
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
    # Configure settings object (maintain compatibility with v1 plugins)
    if data.get('library_id'):
        settings = Settings(library_id=data.get('library_id'))
    else:
        settings = Settings()

    # Get the path to the file
    abspath = data.get('path')

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

    # Set file probe to shared infor for subsequent file test runners
    if 'shared_info' not in data:
        data['shared_info'] = {}
    data['shared_info']['ffprobe'] = probe.get_probe()

    probe_streams = probe.get_probe()["streams"]

    # check if any audio streams have missing audio language tags or are tagged as undefined
    force_rescan = settings.get_setting("force_rescan")
    streams_needing_tags = get_audio_streams(probe_streams, force_rescan)
    if streams_needing_tags:
        logger.debug("streams_needing_tags: '{}'".format(streams_needing_tags))
        # Mark this file to be added to the pending tasks
        data['add_file_to_pending_tasks'] = True
        logger.info("File '{}' should be added to task list. File has audio streams without language tags or have language tags of undefined.".format(abspath))
    else:
        logger.info("File '{}' should not be added to the task list.  All audio streams have language tags.".format(abspath))

    return data

def tag_streams(astreams, vid_file, settings):
    settings2 = config.Config()
    cache_path = settings2.get_cache_path()

    # create temporary work space in cache
    src_file_hash = hashlib.md5(os.path.basename(vid_file).encode('utf8')).hexdigest()
    #tmp_dir = os.path.join('/tmp/unmanic/', '{}'.format(src_file_hash))
    tmp_dir = os.path.join(cache_path, '{}'.format(src_file_hash))
    dir=Path(tmp_dir)
    dir.mkdir(parents=True, exist_ok=True)

    # initialize return array of language metadata tags
    tag_args = []

    # for each audio stream needing a tag, create video file with that single audio stream
    # for astream, _ in enumerate(astreams): -map 0:a:N expects N to be the position of that stream among audio streams only
    for astream in astreams:
        sfx = os.path.splitext(os.path.basename(vid_file))[1]
        temp_sfx = '.mkv'
        output_file = tmp_dir + '/' + str(os.path.splitext(os.path.basename(vid_file))[0]) + '.' + str(astream) + temp_sfx
        command = ['ffmpeg', '-hide_banner', '-loglevel', 'info', '-i', str(vid_file), '-strict', '-2', '-max_muxing_queue_size', '9999', '-map', '0:v:0', '-map', '0:a:'+str(astream), '-map_metadata', '-1', '-c', 'copy', '-y', output_file]
        logger.debug(f"tag_streams output_file: {output_file}")
        logger.debug(f"command: {command}")

        try:
            result = subprocess.run(command, shell=False, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            reason = e.stderr.decode()
            logger.error("Can not create output for audio stream '{}' of file '{}', so skipping stream".format(astream, vid_file))
            continue
        except OSError as e:
            logger.error(f"OSError: {e}, skipping stream")
            continue
        else:
            logger.debug("temp video file to detect language in: '{}".format(output_file))

        tag_anyway = settings.get_setting('tag_anyway')
        lang_tag = detect_language(output_file, tmp_dir, settings)
        logger.debug(f"astream: {astream}, lang_tag: {lang_tag}")
        try:
            if not Language.get(lang_tag).is_valid():
                lang_tag = "und" if tag_anyway else ""
        except (LanguageTagError, TypeError, AttributeError):
            lang_tag = "und" if tag_anyway else ""
      
        if lang_tag:
            # apparently int are forbidden in a "select" input_type
            tag_style = settings.get_setting('tag_style')
            if tag_style == "2":
                lang_tag = standardize_tag(lang_tag)
            else:
                lang_tag = Language.get(standardize_tag(lang_tag)).to_alpha3()
            tag_args += ["-metadata:s:a:"+str(astream), 'language='+lang_tag]
        else:
            logger.error("Language not successfully identified for audio stream '{}' of file '{}', so skipping stream".format(astream, vid_file))

    for f in glob.glob(tmp_dir + "/*.wav"):
        os.remove(f)
    for f in glob.glob(tmp_dir + '/*' + temp_sfx):
        os.remove(f)

    shutil.rmtree(dir, ignore_errors=True)
    return tag_args

def get_model(requested_model: str = 'small'):
    """
    Attempts to load the requested Whisper model on CUDA. If it runs out of VRAM,
    it automatically falls back to progressively smaller models. 
    If CUDA fails entirely, falls back to CPU using the originally requested model size.
    """
    # Define models ordered from largest/most demanding to smallest
    # (Note: turbo is placed above medium as it generally requires slightly more VRAM/compute footprint than medium)

    # According to OpenAI's official research paper, the language identification accuracy 
    # across Whisper's 99 supported languages scales heavily with model size:
    # base: 55%
    # small: 73%
    # medium: 81%
    # large: 84%
    # -> base model will likely get English, Spanish, French, German, Japanese, or Mandarin 100% of the time
    # -> for exotic languages like Estonian, Swahili, Welsh, etc, use small or turbo. medium is garbage, turbo is 6x faster
    # -> unless your life depends on it, maybe the disk space they take will take you out of it?
    model_hierarchy = ['turbo', 'medium', 'small', 'base', 'tiny']
    
    # Clean user input and ensure it's a valid choice
    requested_model = requested_model.lower().strip()
    if requested_model not in model_hierarchy:
        logger.warning(f"Unknown model '{requested_model}', defaulting to 'small'")
        requested_model = 'small'
        
    # Get the index of the requested model and slice the list to only test that model and smaller
    start_idx = model_hierarchy.index(requested_model)
    candidate_models = model_hierarchy[start_idx:]
    
    # 1. Attempt GPU Strategy (Cascading downward)
    for current_model in candidate_models:
        try:
            logger.info(f"Attempting to load Whisper model '{current_model}' on CUDA...")
            model_instance = whisper.load_model(current_model, device='cuda')
            
            # Successfully loaded!
            logger.info(f"Successfully loaded '{current_model}' on CUDA.")
            return model_instance, 'cuda'
            
        except torch.OutOfMemoryError:
            logger.warning(f"VRAM OutOfMemoryError with model '{current_model}'.")
            torch.cuda.empty_cache()  # Clear leftover fragments before trying a smaller model
            continue  # Loop naturally moves to the next smaller model
            
        except RuntimeError as e:
            # Catches driver issues, missing CUDA, or corrupted environments entirely
            logger.error(f"RuntimeError on CUDA device: {e}. Switching strategy to CPU.")
            break 

    # 2. Fallback Strategy (CPU)
    # If we exhausted the loop or hit a driver crash, fall back to CPU using their target choice
    logger.error(f"Insufficient GPU resources or driver error. Falling back to CPU with '{requested_model}'.")
    try:
        model_instance = whisper.load_model(requested_model, device='cpu')
        return model_instance, 'cpu'
    except Exception as e:
        logger.critical(f"Critical failure loading Whisper on CPU: {e}")
        raise e


def detect_language(video_file, tmp_dir, settings):
    force_cpu = settings.get_setting("force_cpu")
    force_samples = settings.get_setting("force_samples")
    samples = settings.get_setting("samples")
    model_name = settings.get_setting("model_name")

    # Load Whisper model
    if force_cpu:
        device = 'cpu'
    else:
        model_name, device = get_model(model_name)
    
    # model was test-loaded in get_model()
    model = whisper.load_model(model_name, device)
    logger.debug("video_file: '{}'; tmp_dir: '{}'".format(video_file, tmp_dir))

    # Load video and get duration
    duration = float(ffmpeg.probe(video_file)['format']['duration'])

    # Define subclip to start 2 minutes into video and end 7 minutes before end
    # Sample x random spots from the trimmed video
    if force_samples:
      samples = int(settings.get_setting("samples"))
    else:
      samples = 3
      
    if duration < 90:
        samples = 1
    elif duration < 30:
        logger.info("File '{}' too short to process (<30 seconds), skipping".format(video_file))
        return None
    
    duration2end = int(duration * 0.06)
    durationFromStart = int(duration * 0.02)
    sample_times = sorted(random.sample(range(int((duration - duration2end) - durationFromStart)), samples))
    logger.debug("sample_times: '{}'".format(sample_times))

    detected_languages = []

    # Analyze the audio at each of the sample times
    for sample_time in sample_times:

        # Extract 30 seconds of audio clip from the video
        audio_file = f"{tmp_dir}/sample_{str(sample_time)}.wav"
        ffmpeg.input(video_file, ss=sample_time, t=30).output(audio_file, vn=None, acodec='pcm_s16le').run()
        logger.debug("audio_file: '{}'".format(audio_file))
        audio = whisper.load_audio(audio_file)
        audio = whisper.pad_or_trim(audio)

        # Run Whisper to detect language from the audio sample
        n_mels = model.dims.n_mels
        mel = whisper.log_mel_spectrogram(audio, n_mels=n_mels).to(model.device)
        _, probs = model.detect_language(mel)
        lang = max(probs, key=probs.get)
        detected_languages.append(lang)
        logger.debug(f"lang {lang} detected in sample {sample_time}")

    # try to force removal of resources left in GPU
    # move model to CPU
    # delete model
    # empty cuda cache
    if not force_cpu:
        try:
            model.cpu()
            del model
        except:
            pass
        torch.cuda.empty_cache()

    # elect a language majority, return the first if samples = 1
    if len(set(detected_languages)) == 1:
        return detected_languages[0]
    else:
        # do not rely on fixed number of samples
        return max(set(detected_languages), key=detected_languages.count)

    return []

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
    global duration

    # Default to no FFMPEG command required. This prevents the FFMPEG command from running if it is not required
    data['exec_command'] = []
    data['repeat'] = False

    # Get the input and output file paths
    abspath = data.get('file_in')
    outfile = data.get('file_out')

    logger.debug(f"worker process output file: {outfile}")

    # Get file probe
    probe_data = Probe(logger, allowed_mimetypes=['video'])

    # Get stream data from probe
    if probe_data.file(abspath):
        probe_streams = probe_data.get_probe()["streams"]
        probe_format = probe_data.get_probe()["format"]
    else:
        logger.debug("Probe data failed - Blocking everything.")
        return data

    if data.get('library_id'):
        settings = Settings(library_id=data.get('library_id'))
    else:
        settings = Settings()

    # Find audio streams that need language tags, if any, and add metadata to set the language tags
    force_rescan = settings.get_setting("force_rescan")
    streams_needing_tags = get_audio_streams(probe_streams, force_rescan)
    logger.debug(f"streams_needing_tags: {streams_needing_tags}")
    if streams_needing_tags:

        tag_args = tag_streams(streams_needing_tags, abspath, settings)

        if tag_args:
            ffmpeg_args = ['-hide_banner', '-loglevel', 'info', '-i', str(abspath), '-max_muxing_queue_size', '9999', '-map', '0', '-c', 'copy'] + tag_args + [ '-y', outfile]

            # Apply ffmpeg args to command
            data['exec_command'] = ['ffmpeg']
            data['exec_command'] += ffmpeg_args

            logger.debug("command: '{}'".format(data['exec_command']))

            # Set the parser
            parser = Parser(logger)
            parser.set_probe(probe_data)
            data['command_progress_parser'] = parser.parse_progress
        else:
            logger.info("File not processed - no streams identified or duration too short")

    return data

