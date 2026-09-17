
**<span style="color:#56adda">1.0.2</span>**
- Updated copyright

**<span style="color:#56adda">1.0.1</span>**
- Updated description, copyright, paths, etc
- verified working as it is

**<span style="color:#56adda">1.0.0</span>**
- Changed name of project to stereo_transcoder_ultra
- Published under audioscavenger/unmanic-plugins

**<span style="color:#56adda">0.1.0</span>**
- Added channels condition selector
- Changed plugin icon

**<span style="color:#56adda">0.0.9</span>**
- Added encode ratecontrol method: VBR/CVBR/CBR where it applies
- Added icons in the select dropdowns / inputs for each codec

**<span style="color:#56adda">0.0.8</span>**
- Added default lang to assign to audio tracks from AVI files, otherwise plugin "Re-order audio streams by language" fails miserably
- Added option to pass or fail when container is incompatbile: otherwise, no remuxer or transcoding to MKV/MP4 will fail avi audio transcoding
- Throws a message in the worker log to indicate when container is incompatible
- Reset bitrate slider to the base rate best for each codec when user switches
- Always rebuild advanced parameter fields based of UI options

**<span style="color:#56adda">0.0.7</span>**
- Added output format as a codec select between AAC and OPUS. Both use same AAC bitrate rules.
- Added BOLD_MAP to easily show bold fonts

**<span style="color:#56adda">0.0.6</span>**
- Enabled codecs section collapse when force encode anything
- Added AAC as a codec
- Added Info section on top of the page

**<span style="color:#56adda">0.0.5</span>**
- Advanced sections pre-fill with current ui settings does not seem to work, I don't really care
- 64k base bitrate per AAC channel is now a slider in 35k increments
- Auto-reduce bitrate to the max that makes sense based off the original track: added mechanic and checkbox
- Added ac3/eac3 as codec options
- Added force encode anything

**<span style="color:#56adda">0.0.4</span>**
- Enable advanced sections pre-fill with current ui settings

**<span style="color:#56adda">0.0.3</span>**
- Expand list of codecs to 'dts', 'ogg', 'vorbis', 'opus', 'flac', 'mp3', 'pcm_s16le', 'wmav2'
- Defaults PCM and FLAC to default AAC bitrate as they are lossless

**<span style="color:#56adda">0.0.2</span>**
- Condition plugin.py to only apply to mono and stereo streams found
- Also only apply to these codecs: DTS, MP3, FLAC, OGG, PCM, OPUS, VORBIS and ignore when audio is ac3/eac3/aac
- Build proper settings menu: list of input codecs to select
- Build CODEC_SETTING_MAP and other mechanics for the ui

**<span style="color:#56adda">0.0.1</span>**
- initial version, hard-fork from encoder_audio_aac by Josh.5 <jsunnex@gmail.com>
