#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    Written by:               AudioscavengeR <dev@derewonko.com>
    Date:                     16 September 2026

    Copyright:
        Copyright (C) 2021 Josh.5 <jsunnex@gmail.com>
        Copyright (C) 2026 AudioscavengeR <audioscavenger@gmail.com>

        This program is free software: you can redistribute it and/or modify it under the terms of the GNU General
        Public License as published by the Free Software Foundation, version 3.

        This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the
        implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
        for more details.

        You should have received a copy of the GNU General Public License along with this program.
        If not, see <https://www.gnu.org/licenses/>.

"""
import logging
import os

from unmanic.libs.unplugins.settings import PluginSettings

from stereo_transcoder_ultra.lib.ffmpeg import StreamMapper, Probe, Parser

# Configure plugin logger
logger = logging.getLogger("Unmanic.Plugin.stereo_transcoder_ultra")

# trick to show bold characters in the UI
normal_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
bold_chars   = "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
BOLD_MAP = str.maketrans(normal_chars, bold_chars)

# Map of settings key -> list of exact codec_name values it should match.
# PCM and WMA are handled separately below via prefix match, since ffprobe reports variants
# like pcm_s16le / pcm_s24le / pcm_u8 and wmav1 / wmav2 / wmapro / wmalossless rather than a
# bare "pcm" or "wma".
#
# Note: 'aac' is deliberately never in this map - it's this plugin's own output codec, so
# an AAC stream is always left alone unless "force_transcode_all" is enabled.
CODEC_SETTING_INPUT_MAP = {
    'convert_dts':    ['dts'],
    'convert_mp3':    ['mp3'],
    'convert_flac':   ['flac'],
    'convert_ogg':    ['ogg'],
    'convert_opus':   ['opus'],
    'convert_vorbis': ['vorbis'],
    'convert_eac3':   ['eac3'],
    'convert_ac3':    ['ac3'],
    'convert_aac':    ['aac'],
}

# This is how ffmpeg is compiled on unmanic LXC container:
# ffmpeg version 7.1.5-0+deb13u1 Copyright (c) 2000-2026 the FFmpeg developers
  # built with gcc 14 (Debian 14.2.0-19)
  # configuration: --prefix=/usr --extra-version=0+deb13u1 --toolchain=hardened --libdir=/usr/lib/x86_64-linux-gnu --incdir=/usr/include/x86_64-linux-gnu --arch=amd64 --enable-gpl --disable-stripping --disable-libmfx --disable-omx --enable-gnutls --enable-libaom --enable-libass --enable-libbs2b --enable-libcdio --enable-libcodec2 --enable-libdav1d --enable-libflite --enable-libfontconfig --enable-libfreetype --enable-libfribidi --enable-libglslang --enable-libgme --enable-libgsm --enable-libharfbuzz --enable-libmp3lame --enable-libmysofa --enable-libopenjpeg --enable-libopenmpt --enable-libopus --enable-librubberband --enable-libshine --enable-libsnappy --enable-libsoxr --enable-libspeex --enable-libtheora --enable-libtwolame --enable-libvidstab --enable-libvorbis --enable-libvpx --enable-libwebp --enable-libx265 --enable-libxml2 --enable-libxvid --enable-libzimg --enable-openal --enable-opencl --enable-opengl --disable-sndio --enable-libvpl --enable-libdc1394 --enable-libdrm --enable-libiec61883 --enable-chromaprint --enable-frei0r --enable-ladspa --enable-libbluray --enable-libcaca --enable-libdvdnav --enable-libdvdread --enable-libjack --enable-libpulse --enable-librabbitmq --enable-librist --enable-libsrt --enable-libssh --enable-libsvtav1 --enable-libx264 --enable-libzmq --enable-libzvbi --enable-lv2 --enable-sdl2 --enable-libplacebo --enable-librav1e --enable-pocketsphinx --enable-librsvg --enable-libjxl --enable-shared
  # libavutil      59. 39.100 / 59. 39.100
  # libavcodec     61. 19.101 / 61. 19.101
  # libavformat    61.  7.103 / 61.  7.103
  # libavdevice    61.  3.100 / 61.  3.100
  # libavfilter    10.  5.100 / 10.  5.100
  # libswscale      8.  3.100 /  8.  3.100
  # libswresample   5.  3.100 /  5.  3.100
  # libpostproc    58.  3.100 / 58.  3.100

CODEC_SETTING_OUTPUT_DEFAULT = 'aac'

# Encoder rate-control modes supported by each output encoder. CVBR is an
# Opus/libopus feature; AAC and MP3 have VBR/CBR modes, while AC3/EAC3
# are treated as CBR because their FFmpeg encoders do not expose a VBR mode
# comparable to Opus.
RATECONTROL_OPTIONS_BY_CODEC = {
    'aac': [
        {'value': 'VBR', 'label': 'VBR - Variable Bitrate (Quality 3)'},
        {'value': 'CBR', 'label': 'CBR - Constant Bitrate'},
    ],
    'opus': [
        {'value': 'VBR', 'label': 'VBR - Variable Bitrate'},
        {'value': 'CVBR', 'label': 'CVBR - Constrained Variable Bitrate'},
        {'value': 'CBR', 'label': 'CBR - Constant Bitrate'},
    ],
    'mp3': [
        {'value': 'VBR', 'label': 'VBR - Variable Bitrate (Quality 2)'},
        {'value': 'CBR', 'label': 'CBR - Constant Bitrate'},
    ],
    'ac3': [
        {'value': 'CBR', 'label': 'CBR - Constant Bitrate'},
    ],
    'eac3': [
        {'value': 'CBR', 'label': 'CBR - Constant Bitrate'},
    ],
}

# Which source channel counts should be processed.  The default keeps the
# plugin's original behaviour: mono and stereo only.
CHANNEL_TARGET_OPTIONS = [
    {'value': 'mono',   'label': '🔈 1.0 - Mono only'},
    {'value': 'stereo', 'label': '🎧 2.0 - Stereo only'},
    {'value': 'le2',    'label': '🔈🎧 - Mono and stereo'},
    {'value': 'gt2',    'label': '📽️ 5.1/7.1 - Surround only (downmix to 2.0)'},
    {'value': 'all',    'label': '🌌 Anything - (downmix to 2.0)'},
]

# These are libswresample downmix controls, expressed in dB.  Keeping the
# surround level below the center level helps preserve dialogue intelligibility
# when a 5.1/7.1 source is reduced to stereo.
DEFAULT_DOWNMIX_CENTER_DB = -3
DEFAULT_DOWNMIX_SURROUND_DB = -6
DEFAULT_DOWNMIX_LFE_DB = -32

# Surround -> stereo downmix formula presets.  The channel indices follow FFmpeg's
# conventional layouts: 5.1 = FL FR FC LFE BL BR; 7.1 = FL FR FC LFE BL BR SL SR.
# The dialogue-focused preset deliberately omits LFE and keeps the center channel
# at full level while bringing the other main/surround channels in at 30%.
DOWNMIX_FORMULA_OPTIONS = [
    {
        'value': 'automatic',
        'label': '✨ Automatic - FFmpeg layout-aware downmix',
    },
    {
        'value': 'dialogue',
        'label': '🗣️ Dialogue-focused - Center 100%, other channels 30%',
    },
    {
        'value': 'custom',
        'label': '⚙️ Custom - Edit the 5.1 / 7.1 pan formulas',
    },
]

DEFAULT_51_PAN_FORMULA = 'pan=stereo|c0=c2+0.30*c0+0.30*c4|c1=c2+0.30*c1+0.30*c5'
DEFAULT_71_PAN_FORMULA = 'pan=stereo|c0=c2+0.30*c0+0.30*c4+0.30*c6|c1=c2+0.30*c1+0.30*c5+0.30*c7'

CODEC_SETTING_OUTPUT_MAP = {
    'aac':  'aac',
    'opus': 'libopus',
    'ac3':  'ac3',
    'eac3': 'eac3',
    'mp3':  'libmp3lame',
}

CODEC_SETTING_OUTPUT_CHOICE = [
  {
    'value': "aac",
    'label': "🔊 {}: Modern audio codec of choice".format('AAC'.translate(BOLD_MAP)),
  },
  {
    'value': "opus",
    'label': "◉ {}: Another great, open-source codec of choice".format('OPUS'.translate(BOLD_MAP)),
  },
  {
    'value': "ac3",
    'label': "💿 {}: Standard multi-channel DVD/Blu-ray audio format".format('AC3 (Dolby Digital)'.translate(BOLD_MAP)),
  },
  {
    'value': "eac3",
    'label': "✨ {}: Enhanced version used for modern streaming".format('EAC3 (Dolby Digital+)'.translate(BOLD_MAP)),
  },
  {
    'value': "mp3",
    'label': "🎧 {}: Why would you ever use that...".format('MP3'.translate(BOLD_MAP)),
  },
]

# Codec labels use Unicode symbols rather than HTML <i> tags because Unmanic's documented select_options contract only guarantees string labels.
# Which output codecs are known to mux reliably into which container extensions.
# MKV is essentially permissive for everything. MP4/M4V/MOV are fine for the common
# lossy codecs but not really used for FLAC/Vorbis/PCM in practice. Legacy AVI can still
# take MP3/AC3 (many old rips already have these), but does NOT reliably support AAC or
# Opus - which is exactly the failure mode this plugin needs to guard against, since AAC
# is this plugin's default output.
#
# An extension not present in this map at all is treated as incompatible (safer default
# than assuming an unknown container will accept the stream).
CONTAINER_COMPATIBLE_OUTPUT_CODECS = {
    'mkv': {'aac', 'opus', 'ac3', 'eac3', 'mp3'},
    'mp4': {'aac', 'opus', 'ac3', 'eac3', 'mp3'},
    'm4v': {'aac', 'opus', 'ac3', 'eac3', 'mp3'},
    'mov': {'aac', 'ac3', 'eac3', 'mp3'},
    'avi': {'mp3', 'ac3'},
}

# Values ffprobe commonly reports for a stream with no real language tag set.
UNSET_LANGUAGE_VALUES = ('', 'und', 'unk', 'undefined', 'undetermined')


def get_file_extension(filepath: str):
    return os.path.splitext(filepath)[-1][1:].lower()


def is_container_compatible(container_ext: str, output_codec: str):
    """
    Returns True only if `container_ext` is known to reliably support `output_codec`.
    An unrecognised container extension is treated as incompatible - see the comment
    on CONTAINER_COMPATIBLE_OUTPUT_CODECS above.

    :param container_ext:
    :param output_codec:
    :return:
    """
    compatible_codecs = CONTAINER_COMPATIBLE_OUTPUT_CODECS.get(container_ext)
    if compatible_codecs is None:
        return False
    return output_codec in compatible_codecs


def stream_language_is_missing(stream_info: dict):
    tags = stream_info.get('tags') or {}
    language = (tags.get('language') or '').strip().lower()
    return language in UNSET_LANGUAGE_VALUES

# Rough, widely-cited perceptual bitrate equivalencies relative to AAC-LC, used only when
# "auto_reduce_bitrate" is enabled. These come from long-running community listening tests
# (see the Hydrogenaudio wiki, e.g. https://wiki.hydrogenaudio.org/index.php?title=Opus and
# https://wiki.hydrogenaudio.org/index.php?title=Ogg_Vorbis) rather than a precise
# psychoacoustic formula - actual results vary by encoder implementation/version and by
# content, so treat these as ballpark heuristics, not lab-grade constants.
#
# A factor < 1.0 means AAC needs LESS bitrate than the source codec for equivalent quality
# (so the source's bitrate is scaled down before being used as a cap). A factor > 1.0 means
# AAC needs MORE bitrate to match the source (e.g. Opus is more efficient than AAC).
AAC_EQUIVALENT_BITRATE_FACTORS = {
    'dts':    0.5,
    'mp3':    0.75,
    'vorbis': 0.95,
    'wma':    0.8,   # covers wmav1 / wmav2 / wmapro / wmalossless via prefix match
    'opus':   1.3,
    'eac3':   0.75,
    'ac3':    0.7,
    'aac':    1.0,
}

# Lossless codecs are intentionally excluded from the bitrate cap: their bitrate reflects
# sample rate/bit depth, not perceptual quality, so it isn't a useful ceiling here.
LOSSLESS_CODEC_PREFIXES = ('flac', 'pcm')

# Codec checkbox labels, shared between the settings dict defaults and the dynamically
# generated form_settings entries below.
CODEC_CHECKBOX_LABELS = {
    'convert_dts':    {'label': 'DTS - Digital Theater Systems', 'description': 'Fixes legacy surround/downmix compatibility issues.'},
    'convert_mp3':    {'label': 'MP3 - MPEG-1/2 Audio Layer III', 'description': 'Fixes non-standard VBR/CBR sync errors common in old VirtualDub AVIs.'},
    'convert_flac':   {'label': 'FLAC - Free Lossless Audio Codec', 'description': 'Converts lossless audio when standardizing to the selected output codec.'},
    'convert_ogg':    {'label': 'OGG - Ogg container audio', 'description': 'Replaces older web-stream audio formats with the selected output codec.'},
    'convert_pcm':    {'label': 'PCM - Uncompressed audio', 'description': 'Converts raw/uncompressed audio to the selected output codec to reduce file size.'},
    'convert_wma':    {'label': 'WMA - Windows Media Audio', 'description': 'Resolves proprietary Microsoft audio compatibility issues on non-Windows players.'},
    'convert_vorbis': {'label': 'Vorbis - Ogg Vorbis', 'description': 'Fixes older OGM/AVI container audio compatibility issues; generally superseded by Opus.'},
    'convert_opus':   {'label': 'Opus - Modern open audio codec', 'description': 'Converts existing Opus tracks when standardizing to the selected output codec.'},
    'convert_eac3':   {'label': 'EAC3 - Dolby Digital Plus', 'description': 'Less universally compatible than AC3; normally best left untouched unless standardization is desired.'},
    'convert_ac3':    {'label': 'AC3 - Dolby Digital', 'description': 'Widely compatible; normally no quality benefit from transcoding unless standardization is desired.'},
    'convert_aac':    {'label': 'AAC - Advanced Audio Coding', 'description': 'Converts existing AAC tracks when standardizing them or targeting a different bitrate.'},
}


class Settings(PluginSettings):
    settings = {
        "header_note":            "",
        "header_warning":         "",
        "force_transcode_all":    False,
        "convert_dts":            True,
        "convert_mp3":            True,
        "convert_flac":           True,
        "convert_ogg":            True,
        "convert_pcm":            True,
        "convert_wma":            True,
        "convert_vorbis":         True,
        "convert_opus":           False,
        "convert_eac3":           False,
        "convert_ac3":            False,
        "convert_aac":            False,
        "target_channels":        "le2",
        "downmix_formula":        "automatic",
        "downmix_center_db":      DEFAULT_DOWNMIX_CENTER_DB,
        "downmix_surround_db":    DEFAULT_DOWNMIX_SURROUND_DB,
        "downmix_lfe_db":         DEFAULT_DOWNMIX_LFE_DB,
        "downmix_51_formula":     DEFAULT_51_PAN_FORMULA,
        "downmix_71_formula":     DEFAULT_71_PAN_FORMULA,
        "output_codec":           "aac",
        "encode_ratecontrol_method": "VBR",
        "base_bitrate_per_channel": 64,
        "auto_reduce_bitrate":    True,
        "fail_on_incompatible_container": True,
        "assign_default_language": True,
        "default_stream_language": "eng",
        "default_stream_title":    "English",
        "advanced":               False,
        "max_muxing_queue_size":  4096,
        "main_options":           "",
        "advanced_options":       "",
        "custom_options_note":    "",
        "custom_options":         "",
    }

    def __init__(self, *args, **kwargs):
        super(Settings, self).__init__(*args, **kwargs)
        # 1. Capture the currently stored output_codec
        current_codec = self.get_setting('output_codec')

        self.form_settings = {
            "header_note":              self.__set_header_note_form_settings(),
            "header_warning":           self.__set_header_warning_form_settings(),
        }
        
        self.form_settings.update({
            # Channel selection intentionally comes before codec selection in the UI.
            "target_channels":          self.__set_target_channels_form_settings(),
            "downmix_formula":          self.__set_downmix_formula_form_settings(),
            "downmix_51_formula":       self.__set_downmix_formula_field_form_settings(
                                            "downmix_51_formula",
                                            "Custom 5.1 downmix formula",
                                            DEFAULT_51_PAN_FORMULA,
                                            "Used for 5.1 sources when Custom is selected. Expected to be a complete FFmpeg pan=stereo filter."),
            "downmix_71_formula":       self.__set_downmix_formula_field_form_settings(
                                            "downmix_71_formula",
                                            "Custom 7.1 downmix formula",
                                            DEFAULT_71_PAN_FORMULA,
                                            "Used for 7.1 sources when Custom is selected. Expected to be a complete FFmpeg pan=stereo filter."),
            "downmix_center_db":        self.__set_downmix_level_form_settings(
                                            "downmix_center_db",
                                            "Downmix center/dialogue level (dB)",
                                            DEFAULT_DOWNMIX_CENTER_DB,
                                            "Automatic mode only. Lower values reduce the center channel relative to L/R."),
            "downmix_surround_db":      self.__set_downmix_level_form_settings(
                                            "downmix_surround_db",
                                            "Downmix surround level (dB)",
                                            DEFAULT_DOWNMIX_SURROUND_DB,
                                            "Automatic mode only. Lower values keep rear/side channels from masking dialogue."),
            "downmix_lfe_db":           self.__set_downmix_level_form_settings(
                                            "downmix_lfe_db",
                                            "Downmix LFE/subwoofer level (dB)",
                                            DEFAULT_DOWNMIX_LFE_DB,
                                            "Automatic mode only. Use -32 dB to effectively omit LFE from the stereo mix."),
            "output_codec":             self.__set_output_codec_form_settings(),
            "encode_ratecontrol_method": self.__set_encode_ratecontrol_method_form_settings(current_codec),
        })
        
        # Add collapse option to force transcode anything to AAC including original AAC tracks
        self.form_settings.update({
            "force_transcode_all":      self.__set_force_transcode_all_form_settings(),
        })
        # Dynamically generate the per-codec checkbox form settings, so they all share
        # the same "hide me while force_transcode_all is on" behaviour.
        for setting_key, label in CODEC_CHECKBOX_LABELS.items():
            self.form_settings[setting_key] = self.__set_codec_checkbox_form_settings(label)

        self.form_settings.update({
            "base_bitrate_per_channel": self.__set_base_bitrate_per_channel_form_settings(current_codec),
            "auto_reduce_bitrate":      self.__set_auto_reduce_bitrate_form_settings(),
            "fail_on_incompatible_container": self.__set_fail_on_incompatible_container_form_settings(current_codec),
            "assign_default_language":  self.__set_assign_default_language_form_settings(),
            "default_stream_language":  self.__set_default_stream_language_form_settings(),
            "default_stream_title":     self.__set_default_stream_title_form_settings(),
            "advanced":                 {
                "label":      "Write your own FFmpeg params",
                "description":"Most of the parameters will be dynamically constructed at runtime, "
                              "the fileds below are simply appended to the worker command ",
            },
            "max_muxing_queue_size":    self.__set_max_muxing_queue_size_form_settings(),
            "main_options":             self.__set_main_options_form_settings(),
            "advanced_options":         self.__set_advanced_options_form_settings(),
            "custom_options_note":      self.__set_custom_options_note_form_settings(),
            "custom_options":           self.__set_custom_options_form_settings(),
        })
        # Pre-fill the advanced/custom FFmpeg fields with the same values this plugin
        # would otherwise generate automatically, the first time 'advanced' mode is
        # switched on. This gives the user a real starting point to edit from instead
        # of a blank textarea. Once a field holds any value (including this pre-filled
        # one), it is left alone from then on - the user's own edits are never
        # overwritten by this.
        self.__prefill_advanced_options_with_computed_defaults()

    def __set_target_channels_form_settings(self):
        values = {
            "label":          "Target source channels",
            "input_type":     "select",
            "select_options": CHANNEL_TARGET_OPTIONS,
            "description":    (
                "🔈🎧 is the default. "
                "📽️ processes surround tracks and downmixes them to stereo using the downmix controls below."
            ),
        }
        return values

    def __set_downmix_level_form_settings(self, setting_key, label, default_value, description):
        values = {
            "label":       label,
            "input_type":  "slider",
            "sub_setting": True,
            "slider_options": {
                "min":  -32,
                "max":  0,
                "step": 1,
            },
            "description": description,
        }

        if self.get_setting('target_channels') not in ['gt2', 'all'] or self.get_setting('downmix_formula') != 'automatic':
            values["display"] = 'hidden'

        return values

    def __set_downmix_formula_form_settings(self):
        values = {
            "label":          "Surround downmix formula",
            "input_type":     "select",
            "sub_setting":    True,
            "select_options": DOWNMIX_FORMULA_OPTIONS,
            "description":    (
                "🗣️ Dialogue-focused: center/dialogue is kept at 100%, other non-LFE channels at 30% "
            ),
        }

        if self.get_setting('target_channels') not in ['gt2', 'all']:
            values["display"] = 'hidden'

        return values

    def __set_downmix_formula_field_form_settings(self, setting_key, label, default_value, description):
        values = {
            "label":       label,
            "input_type":  "textarea",
            "sub_setting": True,
            "description": description,
        }
        if self.get_setting('target_channels') not in ['gt2', 'all'] or self.get_setting('downmix_formula') != 'custom':
            values["display"] = 'hidden'
        return values

    def __set_output_codec_form_settings(self):
        values = {
            "label":          "Output codec",
            "input_type":     "select",
            "select_options": CODEC_SETTING_OUTPUT_CHOICE,
        }
        return values

    def __set_encode_ratecontrol_method_form_settings(self, current_codec):
        current_codec = str(current_codec or CODEC_SETTING_OUTPUT_DEFAULT).lower()
        select_options = RATECONTROL_OPTIONS_BY_CODEC.get(
            current_codec,
            [{'value': 'CBR', 'label': 'CBR - Constant Bitrate'}]
        )

        values = {
            "label":          "Encode ratecontrol method",
            "input_type":     "select",
            "sub_setting":    True,
            "select_options": select_options,
            "description":    "CBR: Constant Bitrate<br /> "
                              "VBR: Variable Bitrate (Quality factor applied for AAC/MP3)<br /> "
                              "CVBR: Constrained Variable Bitrate, only by OPUS ",
        }

        # If an old/stale setting is no longer valid for the selected codec,
        # fall back to the first valid choice. This matters when changing the
        # output codec from Opus (CVBR) to a codec that has no CVBR mode.
        current_method = self.get_setting('encode_ratecontrol_method')
        valid_methods = [option['value'] for option in select_options]
        if current_method not in valid_methods:
            self.set_setting('encode_ratecontrol_method', select_options[0]['value'])

        return values

    def __set_force_transcode_all_form_settings(self):
        values = {
            "label":      "Force re-encode ALL mono/stereo streams",
            "description":"That includes streams already in the target codec",
        }
        return values

    def __set_codec_checkbox_form_settings(self, codec_info):
        # Unmanic expects label and description as separate fields.
        if isinstance(codec_info, dict):
            values = {
                "label": codec_info.get('label', ''),
                "description": codec_info.get('description', ''),
                "sub_setting": True,
            }
        else:
            values = {
                "label": codec_info,
                "sub_setting": True,
            }
        if self.get_setting('force_transcode_all'):
            values["display"] = 'hidden'
        return values

    def __set_base_bitrate_per_channel_form_settings(self, current_codec):
        # Format the variable to handle fallback string normalization
        if current_codec:
            current_codec = str(current_codec).lower()
        else:
            current_codec = CODEC_SETTING_OUTPUT_DEFAULT
        
        # 2. Set dynamic defaults or boundaries based on the codec
        if current_codec == "opus":
            default_min, default_max, step = 24, 240, 24
        elif current_codec == "ac3":
            default_min, default_max, step = 64, 106, 16
        elif current_codec == "eac3":
            default_min, default_max, step = 32, 170, 16
        elif current_codec == "mp3":
            default_min, default_max, step = 32, 320, 32
        else: # Default fallback AAC
            default_min, default_max, step = 32, 320, 32

        values = {
            "label":          "{} bitrate per channel (kBit/s)".format(current_codec.upper().translate(BOLD_MAP)),
            "input_type":     "slider",
            "sub_setting":    True,
            "slider_options": {
                "min":  default_min,
                "max":  default_max,
                "step": step,
            },
        }
        
        if self.get_setting('advanced'):
            values["display"] = 'hidden'
            
        return values

    def __set_auto_reduce_bitrate_form_settings(self):
        values = {
            "label":      "Automatically reduce target bitrate to match the source",
            "description":"When source doesn't warrant a higher bitrate, adjust target bitrate to max equivalent quality",
        }
        if self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values

    def __set_fail_on_incompatible_container_form_settings(self, current_codec):
        values = {
            "label":      "Fail the worker if the target container is incompatible with {}".format(current_codec.upper().translate(BOLD_MAP)),
            "description":"If unchecked, the file is left untouched and worker will PASS but no encoding will happen.",
        }
        return values

    def __set_assign_default_language_form_settings(self):
        values = {
            "label":      "Tag processed streams with a default language/title where needed",
            "description":"AVI files do NOT have lang/name for audio streams, and without that, "
                          " plugins like 'Re-order audio streams by language' will FAIL. Unckeck if using 'Detect audio stream language'",
        }
        return values

    def __set_default_stream_language_form_settings(self):
        values = {
            "label":       "Default language (ISO 639-2, e.g. eng, fre, ger)",
            "sub_setting": True,
        }
        if not self.get_setting('assign_default_language'):
            values["display"] = 'hidden'
        return values

    def __set_default_stream_title_form_settings(self):
        values = {
            "label":       "Default stream title",
            "sub_setting": True,
        }
        if not self.get_setting('assign_default_language'):
            values["display"] = 'hidden'
        return values

    def __set_max_muxing_queue_size_form_settings(self):
        values = {
            "label":          "Max input stream packet buffer",
            "input_type":     "slider",
            "slider_options": {
                "min": 1024,
                "max": 10240,
                "step": 512,
            },
        }
        if self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values

    def __set_main_options_form_settings(self):
        values = {
            "label":      "Write your own custom main options",
            "input_type": "textarea",
        }
        if not self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values

    def __set_advanced_options_form_settings(self):
        values = {
            "label":      "Write your own custom advanced options",
            "input_type": "textarea",
        }
        if not self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values

    def __set_custom_options_note_form_settings(self):
        values = {
            "label":       "Note",
            "input_type":  "section_admonition",
            "description": (
                "This plugin normally calculates bitrate per-stream (based on the setting "
                "above and the source), so there is no single fixed value to pre-fill here. "
                "The box below has been seeded with <code>-b:a 128k</code> (the stereo/"
                "2-channel case) as a starting point &mdash; change it to <code>-b:a 64k</code> "
                "if your source streams are mono."
            ),
        }
        if not self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values

    def __set_header_note_form_settings(self):
        values = {
            "label":       "Note",
            "input_type":  "section_admonition",
            "description": (
                "This plugin defaults to transcoding mono/stereo tracks only. "
                "It is best used for cleaning up old AVI movies collections, to pair with <code>MKV</code> remuxer<br /> "
                "Tired of lags and audio de-sync on your Roku TV? Don't let the past hold you behind and transcode like a pro! "
            ),
        }
        return values

    def __set_header_warning_form_settings(self):
        values = {
            "label":       "Warning",
            "input_type":  "section_admonition",
            "description": (
                "This plugin will {} if target container is not MKV/MP4/M4V<br /> ".format('FAIL'.translate(BOLD_MAP))
            ),
        }
        return values

    def __set_custom_options_form_settings(self):
        values = {
            "label":      "Write your own custom audio options",
            "input_type": "textarea",
        }
        if not self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values

    def __prefill_advanced_options_with_computed_defaults(self):
        """
        The first time 'advanced' mode is switched on, pre-fill the advanced/custom
        FFmpeg option fields with the same values this plugin would otherwise generate
        automatically:
          - ADVANCED OPTIONS (after the input file is specified) is where the muxing
            queue buffer size setting belongs, so seed it with the base FFmpeg defaults
            plus the currently configured buffer size.
          - MAIN OPTIONS (before the input file) - this plugin doesn't set anything here
            automatically, so there is nothing meaningful to pre-fill.
          - AUDIO OPTIONS (custom_options) - bitrate is normally computed per-stream from
            that stream's channel count (and optionally capped against the source), so
            there's no single fixed value; seed it with the stereo (2-channel) case at
            the configured per-channel rate as a starting point.

        Always recompute settings from the UI

        :return:
        """
        if not self.get_setting('advanced'):
            return

        # if not self.get_setting('advanced_options'):
        muxing_queue_size = self.get_setting('max_muxing_queue_size')
        self.set_setting('advanced_options', '-strict -2 -max_muxing_queue_size {}'.format(muxing_queue_size))

        # if not self.get_setting('custom_options'):
        stereo_bitrate = int(self.get_setting('base_bitrate_per_channel')) * 2
        self.set_setting('custom_options', '-b:a {}k'.format(stereo_bitrate))


class PluginStreamMapper(StreamMapper):
    def __init__(self):
        super(PluginStreamMapper, self).__init__(logger, ['audio'])
        self.codec = 'aac'
        self.encoder = 'aac'
        self.settings = None

    def set_default_values(self, settings, abspath, probe):
        """
        Configure the stream mapper with defaults

        :param settings:
        :param abspath:
        :param probe:
        :return:
        """
        self.abspath = abspath
        # Set the file probe data
        self.set_probe(probe)
        # Set the input file
        self.set_input_file(abspath)
        # Configure settings
        self.settings = settings

        output_codec = self.settings.get_setting('output_codec') or CODEC_SETTING_OUTPUT_DEFAULT
        self.codec = output_codec
        self.encoder = CODEC_SETTING_OUTPUT_MAP[output_codec]

        # Build default options of advanced mode
        if self.settings.get_setting('advanced'):
            # If any main options are provided, overwrite them
            main_options = settings.get_setting('main_options').split()
            if main_options:
                # Overwrite all main options
                self.main_options = main_options
            # If any advanced options are provided, overwrite them
            advanced_options = settings.get_setting('advanced_options').split()
            if advanced_options:
                # Overwrite all advanced options
                self.advanced_options = advanced_options
        else:
            # Apply the configured muxing queue buffer size. Without this, the
            # base StreamMapper's hardcoded default (4096) is always used instead,
            # regardless of what this setting's slider is set to.
            self.set_ffmpeg_advanced_options(**{
                '-max_muxing_queue_size': str(self.settings.get_setting('max_muxing_queue_size')),
            })

    def calculate_bitrate(self, stream_info: dict):
        output_codec = self.settings.get_setting('output_codec') or CODEC_SETTING_OUTPUT_DEFAULT
        source_channels = stream_info.get('channels', 2)
        try:
            source_channels = int(source_channels)
        except (TypeError, ValueError):
            source_channels = 2

        # Surround targets are downmixed to stereo, so bitrate is based on the
        # actual encoded output channel count rather than the source's 5.1/7.1
        # channel count.
        target_channels = str(self.settings.get_setting('target_channels') or 'le2').lower()
        channels = 2 if target_channels in ['gt2', 'all'] else min(source_channels, 6)

        base_bitrate_per_channel = int(self.settings.get_setting('base_bitrate_per_channel'))
        bitrate = int(channels) * base_bitrate_per_channel

        if self.settings.get_setting('auto_reduce_bitrate'):
            cap = self.get_source_equivalent_bitrate_cap(stream_info)
            if cap and cap < bitrate:
                logger.debug(
                    "Reducing {} bitrate from {}k to {}k - source codec/bitrate doesn't "
                    "warrant the higher rate.".format(output_codec, bitrate, cap))
                bitrate = cap

        return bitrate

    def get_source_equivalent_bitrate_cap(self, stream_info: dict):
        """
        Estimate a ceiling for the output bitrate based on the source stream's own bitrate,
        so a low-bitrate lossy source isn't needlessly re-encoded at a much higher bitrate
        that gains nothing. Returns None if there is nothing sensible to compare against
        (missing source bitrate, a lossless source codec, or an unrecognised codec).

        AAC_EQUIVALENT_BITRATE_FACTORS is calibrated relative to AAC-LC (see the comment
        above it). If the selected output format is instead Opus, the same source-codec
        factor is re-based against Opus's own AAC-equivalent factor, so e.g. a Vorbis
        source is still compared correctly whether the target is AAC or Opus. This stacks
        two separate heuristics on top of each other, so treat the result as a rough
        ballpark rather than a precise figure.

        :param stream_info:
        :return:
        """
        codec_name = (stream_info.get('codec_name') or '').lower()

        # Lossless codecs have no meaningful "equivalent quality" bitrate to cap against.
        if codec_name.startswith(LOSSLESS_CODEC_PREFIXES):
            return None

        source_bit_rate = stream_info.get('bit_rate')
        if not source_bit_rate:
            return None
        try:
            source_kbps = int(source_bit_rate) / 1000
        except (TypeError, ValueError):
            return None

        if codec_name.startswith('wma'):
            source_factor = AAC_EQUIVALENT_BITRATE_FACTORS.get('wma')
        else:
            source_factor = AAC_EQUIVALENT_BITRATE_FACTORS.get(codec_name)

        if not source_factor:
            return None

        output_codec = self.settings.get_setting('output_codec') or 'aac'
        output_baseline_factor = AAC_EQUIVALENT_BITRATE_FACTORS.get(output_codec, 1.0)
        factor = source_factor / output_baseline_factor

        return int(source_kbps * factor)

    def get_codec_setting_key(self, codec_name: str):
        """
        Given a codec_name reported by ffprobe, return the settings key that controls
        whether this plugin should convert it, or None if the codec is not one of the
        plugin's configurable targets.

        :param codec_name:
        :return:
        """
        codec_name = (codec_name or '').lower()

        # PCM variants (pcm_s16le, pcm_s24le, pcm_u8, ...)
        if codec_name.startswith('pcm'):
            return 'convert_pcm'

        # WMA variants (wmav1, wmav2, wmapro, wmalossless, ...)
        if codec_name.startswith('wma'):
            return 'convert_wma'

        for setting_key, codec_names in CODEC_SETTING_INPUT_MAP.items():
            if codec_name in codec_names:
                return setting_key

        return None

    def test_stream_needs_processing(self, stream_info: dict):
        """
        Only flag a stream for processing if it matches the selected channel target:
          - mono   -> exactly 1 channel
          - stereo -> exactly 2 channels
          - <=2    -> 1 or 2 channels (default/original behaviour)
          - >2     -> more than 2 channels; these are downmixed to stereo

        The selected channel target is independent of the codec conversion checkbox.
        Force mode still overrides the codec checkbox, but not the channel target.

        :param stream_info:
        :return:
        """
        codec_name = (stream_info.get('codec_name') or '').lower()

        # Determine channel count - default to stereo (2) if not reported
        channels = stream_info.get('channels', 2)
        try:
            channels = int(channels)
        except (TypeError, ValueError):
            channels = 2

        # Channel-target selection.
        target_channels = str(self.settings.get_setting('target_channels') or 'le2').lower()
        if target_channels == 'mono':
            channel_match = channels == 1
        elif target_channels == 'stereo':
            channel_match = channels == 2
        elif target_channels == 'gt2':
            channel_match = channels > 2
        elif target_channels == 'all':
            channel_match = True
        else:  # <=2.0, the historical/default behaviour
            channel_match = channels <= 2

        if not channel_match:
            logger.debug(
                "Ignoring stream with {} channels - channel target '{}' does not match.".format(
                    channels, target_channels))
            return False

        # Force mode: re-encode every stream matching the selected channel target
        # regardless of its codec.
        if self.settings.get_setting('force_transcode_all'):
            return True

        # Rule 2: Only handle known, configurable target codecs. Anything else (including
        # 'aac' and any codec ffprobe fails to identify) is passed over untouched.
        setting_key = self.get_codec_setting_key(codec_name)
        if setting_key is None:
            logger.debug("Ignoring stream with unrecognised/unsupported codec '{}'.".format(codec_name))
            return False

        # Rule 3: Respect the user's per-codec enable/disable choice
        if not self.settings.get_setting(setting_key):
            logger.debug("Ignoring stream with codec '{}' - conversion disabled in settings.".format(codec_name))
            return False

        return True

    def custom_stream_mapping(self, stream_info: dict, stream_id: int):
        stream_encoding = ['-c:a:{}'.format(stream_id), self.encoder]
        if self.settings.get_setting('advanced'):
            stream_encoding += self.settings.get_setting('custom_options').split()
        else:
            # Automatically detect bitrate for this stream.
            if stream_info.get('channels'):
                calculated_bitrate = self.calculate_bitrate(stream_info)
                source_channels = int(stream_info.get('channels'))
                if int(source_channels) > 6:
                    source_channels = 6

                target_channels = str(
                    self.settings.get_setting('target_channels') or 'le2'
                ).lower()

                # For the >2.0 target, downmix to stereo. Automatic mode uses
                # FFmpeg/libswresample's channel-layout-aware matrix. The dialogue
                # and custom modes use explicit pan formulas, with separate formulas
                # for 5.1 and 7.1 because those layouts have different channel counts.
                if target_channels in ['gt2', 'all']:
                    downmix_formula = str(
                        self.settings.get_setting('downmix_formula') or 'automatic'
                    ).lower()

                    if downmix_formula == 'dialogue':
                        if source_channels == 8:
                            pan_formula = DEFAULT_71_PAN_FORMULA
                        elif source_channels == 6:
                            pan_formula = DEFAULT_51_PAN_FORMULA
                        else:
                            # The preset formulas are specifically for 5.1/7.1.
                            # Let libswresample handle uncommon layouts safely.
                            downmix_formula = 'automatic'
                    elif downmix_formula == 'custom':
                        if source_channels == 8:
                            pan_formula = str(
                                self.settings.get_setting('downmix_71_formula') or DEFAULT_71_PAN_FORMULA
                            ).strip()
                        elif source_channels == 6:
                            pan_formula = str(
                                self.settings.get_setting('downmix_51_formula') or DEFAULT_51_PAN_FORMULA
                            ).strip()
                        else:
                            # Custom fields are intentionally limited to the two common
                            # movie layouts; don't apply a 5.1/7.1 matrix to another layout.
                            downmix_formula = 'automatic'
                        if downmix_formula == 'custom' and not pan_formula:
                            pan_formula = DEFAULT_71_PAN_FORMULA if source_channels == 8 else DEFAULT_51_PAN_FORMULA

                    if downmix_formula in ('dialogue', 'custom'):
                        stream_encoding += [
                            '-af:a:{}'.format(stream_id),
                            pan_formula,
                        ]
                    if downmix_formula == 'automatic':
                        center_db = int(self.settings.get_setting('downmix_center_db') or DEFAULT_DOWNMIX_CENTER_DB)
                        surround_db = int(self.settings.get_setting('downmix_surround_db') or DEFAULT_DOWNMIX_SURROUND_DB)
                        lfe_db = int(self.settings.get_setting('downmix_lfe_db') or DEFAULT_DOWNMIX_LFE_DB)
                        stream_encoding += [
                            '-af:a:{}'.format(stream_id),
                            'aresample=ochl=stereo:clev={}:slev={}:lfe_mix_level={}'.format(
                                center_db, surround_db, lfe_db)
                        ]
                    encoded_channels = 2
                else:
                    encoded_channels = source_channels

                ratecontrol = str(
                    self.settings.get_setting('encode_ratecontrol_method') or 'CBR'
                ).upper()

                # Opus/libopus exposes the exact VBR/CVBR/CBR controls used by
                # Unmanic's audio_transcoder plugin: -vbr on/constrained/off.
                # Keep the bitrate as the target/average bitrate in all three modes.
                if self.codec == 'opus':
                    if ratecontrol == 'CBR':
                        stream_encoding += ['-vbr', 'off']
                    elif ratecontrol == 'CVBR':
                        stream_encoding += ['-vbr', 'constrained']
                    else:
                        stream_encoding += ['-vbr', 'on']
                    stream_encoding += [
                        '-b:a:{}'.format(stream_id), '{}k'.format(calculated_bitrate)
                    ]

                # Native AAC exposes a VBR quality mode rather than Opus-style
                # constrained VBR. Keep the existing bitrate behaviour for CBR;
                # for VBR use a sensible native AAC quality level. The bitrate
                # slider remains the CBR target and source-bitrate cap.
                elif self.codec == 'aac' and ratecontrol == 'VBR':
                    stream_encoding += ['-vbr:a:{}'.format(stream_id), '3']

                # libmp3lame uses -q:a for VBR and -b:a for CBR. Quality 2 is
                # approximately the conventional high-quality VBR setting.
                elif self.codec == 'mp3' and ratecontrol == 'VBR':
                    stream_encoding += ['-q:a:{}'.format(stream_id), '2']

                else:
                    # AC3/EAC3 are CBR here, and this is also the fallback
                    # for any encoder without a dedicated VBR implementation.
                    stream_encoding += [
                        '-b:a:{}'.format(stream_id), '{}k'.format(calculated_bitrate)
                    ]

                stream_encoding += [
                    '-ac:a:{}'.format(stream_id), '{}'.format(encoded_channels)
                ]

        # Tag the stream with a default language/title if the source has none set (common
        # in old AVI rips, and needed by plugins such as "Re-order audio streams by
        # language" which can't handle a missing tag). Applied regardless of advanced mode,
        # since it's independent of the bitrate/encoder options above.
        if self.settings.get_setting('assign_default_language') and stream_language_is_missing(stream_info):
            default_language = self.settings.get_setting('default_stream_language') or 'eng'
            default_title = self.settings.get_setting('default_stream_title') or 'English'
            stream_encoding += [
                '-metadata:s:a:{}'.format(stream_id), 'language={}'.format(default_language),
                '-metadata:s:a:{}'.format(stream_id), 'title={}'.format(default_title),
            ]

        return {
            'stream_mapping':  ['-map', '0:a:{}'.format(stream_id)],
            'stream_encoding': stream_encoding,
        }


def on_library_management_file_test(data):
    """
    Runner function - enables additional actions during the library management file tests.

    The 'data' object argument includes:
        path                            - String containing the full path to the file being tested.
        issues                          - List of currently found issues for not processing the file.
        add_file_to_pending_tasks       - Boolean, is the file currently marked to be added to the queue for processing.

    :param data:
    :return:

    """
    # Get the path to the file
    abspath = data.get('path')

    # Get file probe
    probe = Probe(logger, allowed_mimetypes=['audio', 'video'])
    if not probe.file(abspath):
        # File probe failed, skip the rest of this test
        return data

    # Configure settings object (maintain compatibility with v1 plugins)
    if data.get('library_id'):
        settings = Settings(library_id=data.get('library_id'))
    else:
        settings = Settings()

    # Get stream mapper
    mapper = PluginStreamMapper()
    mapper.set_default_values(settings, abspath, probe)

    if mapper.streams_need_processing():
        # Advisory check only: at file-test time we only know the SOURCE file's own
        # container - we can't guess if remux or video transcoding happens after
        output_codec = settings.get_setting('output_codec') or CODEC_SETTING_OUTPUT_DEFAULT
        source_container_ext = get_file_extension(abspath)
        if not is_container_compatible(source_container_ext, output_codec):
            message = (
                "stereo_transcoder_ultra: source container '{}' does not support {} audio. "
                "A container remux (MKV or MP4) needs to run BEFORE this plugin in the "
                "processing flow, or this task will FAIL (unless you select to not fail) "
                "in settings.".format(
                    source_container_ext or '(none)', output_codec.upper())
            )
            logger.warning(message)
            data.setdefault('issues', []).append({
                'message': message,
                'abspath': abspath,
            })

        # Mark this file to be added to the pending tasks
        data['add_file_to_pending_tasks'] = True
        logger.debug("File '{}' should be added to task list. Probe found streams require processing.".format(abspath))
    else:
        logger.debug("File '{}' does not contain streams require processing.".format(abspath))

    return data


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

    :param data:
    :return:

    """
    # Default to no FFMPEG command required. This prevents the FFMPEG command from running if it is not required
    data['exec_command'] = []
    data['repeat'] = False

    # Get the path to the file
    abspath = data.get('file_in')

    # Get file probe
    probe = Probe(logger, allowed_mimetypes=['audio', 'video'])
    if not probe.file(abspath):
        # File probe failed, skip the rest of this test
        return data

    # Configure settings object (maintain compatibility with v1 plugins)
    settings = Settings(library_id=data.get('library_id'))

    # Get stream mapper
    mapper = PluginStreamMapper()
    mapper.set_default_values(settings, abspath, probe)

    if mapper.streams_need_processing():
        # Authoritative check: by now, file_out reflects whatever container any earlier
        # plugin in the worker flow (e.g. a remux/video transcoder) has already set it to.
        # This is the only point this plugin can know for certain what container ffmpeg
        # will actually mux into.
        output_codec = settings.get_setting('output_codec') or CODEC_SETTING_OUTPUT_DEFAULT
        file_out = data.get('file_out') or abspath
        out_container_ext = get_file_extension(file_out)

        if not is_container_compatible(out_container_ext, output_codec):
            message = (
                "stereo_transcoder_ultra: cannot mux {} audio into a '{}' container ('{}'). "
                "A container remux (e.g. to MKV or MP4) must run before this plugin in the "
                "processing flow.".format(output_codec.upper(), out_container_ext or '(none)', file_out)
            )
            if settings.get_setting('fail_on_incompatible_container'):
                logger.error(message)
                raise RuntimeError(message)
            else:
                logger.warning(message + " Skipping audio processing for this file this pass "
                                          "('Fail on incompatible container' is disabled).")
                return data

        # Set the input file
        mapper.set_input_file(abspath)

        # Set the output file
        mapper.set_output_file(data.get('file_out'))

        # Get generated ffmpeg args
        ffmpeg_args = mapper.get_ffmpeg_args()

        # Apply ffmpeg args to command
        data['exec_command'] = ['ffmpeg']
        data['exec_command'] += ffmpeg_args

        # Set the parser
        parser = Parser(logger)
        parser.set_probe(probe)
        data['command_progress_parser'] = parser.parse_progress
