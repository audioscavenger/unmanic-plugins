
---

##### Links:

- [Unmanic Support](https://unmanic.app/discord)
- [Issues/Feature Requests](https://github.com/audioscavenger/plugin.stereo_transcoder_ultra/issues)
- [Pull Requests](https://github.com/audioscavenger/plugin.stereo_transcoder_ultra/pulls)

---

##### Description:

This Plugin is intended for transcoding of old AVI files with problematic **mono and stereo** audio streams.

This Plugin requires a target MKV/MP4/M4V container.

It can target transcode specific number of channels:
* mono
* stereo
* *<=stereo* (default)
* >stereo (downmix 5.1 and 7.1)

Within that mono/stereo scope, it only converts the codecs you enable below (or anything ffmpeg can handle if you choose so):
- DTS
- MP3
- FLAC
- OGG
- PCM
- WMA
- VORBIS
- OPUS
- AAC
- AC3/EAC3

  Streams already encoded as **AAC, OPUS, AC3, or EAC3** should be skipped by default, since these are considered safe delivery codecs (transcoding can be forced).

Target codecs you can choose from:
- AAC (LC)
- OPUS
- AC3
- EAC3
- MP3

The plugin can auto-manages the bitrate for you if you don't want to over-shoot the original quality.

➡️ This plugin will FAIL if target container is not MKV/MP4/M4V ⬅️

##### Notes:

What should be modified to achive the same rults, is *Transcode Audio* (`audio_transcoder`) by the same author. That would make one-of-a-kind audio transcoder that can handle anything. 

But I'm not forcing his hand or pulling requests that would be denied, I've done that too many times, thank you. I decided to leave people's pet projects alone.

---

##### Specifics:

When channels >2.0 is selected, three additional controls appear:

| Setting             |    Default | Purpose                              |
| ------------------- | ---------: | ------------------------------------ |
| **Center/dialogue** |  **-3 dB** | Controls center-channel contribution |
| **Surround**        |  **-6 dB** | Reduces rear/side contribution       |
| **LFE/subwoofer**   | **-32 dB** | Effectively excludes LFE by default  |

The important one for downmixing is Surround = -6 dB. The center channel gets a stronger relative contribution, which should make dialogue substantially safer than simply treating all surround material equally.

These are real FFmpeg/libswresample downmix parameters rather than arbitrary volume filters. FFmpeg exposes center_mix_level, surround_mix_level, and lfe_mix_level specifically for this purpose.

The formula for 5.1 is `pan=stereo|c0=c2+0.30*c0+0.30*c4|c1=c2+0.30*c1+0.30*c5` and for 7.1: ``.

---

##### Documentation:

For information on the available encoder settings:
- [FFmpeg - AAC Encoder](https://trac.ffmpeg.org/wiki/Encode/AAC)
- [FFmpeg - OPUS Encoder](https://ffmpeg.org/ffmpeg-codecs.html#libopus-1)

--- 

### Config description:

#### <span style="color:blue">Convert DTS / Convert MP3 / Convert FLAC / Convert OGG / Convert PCM / Convert OPUS / Convert VORBIS / Convert WMA</span>
Individually enable or disable which mono/stereo codecs this plugin should transcode to AAC. Unchecking a codec leaves matching streams completely untouched.

#### <span style="color:blue">Max input stream packet buffer</span>
When transcoding audio and/or video streams, ffmpeg will not begin writing into the output until it has one packet for each such stream. 
While waiting for that to happen, packets for other streams are buffered. 
This option sets the size of this buffer, in packets, for the matching output stream.

FFmpeg docs refer to this value as '-max_muxing_queue_size'


#### <span style="color:blue">Write your own FFmpeg params</span>
This free text input allows you to write any FFmpeg params that you want. 
This is for more advanced use cases where you need finer control over the file transcode.

:::note
These params are added in three different places:
1. **MAIN OPTIONS** - After the default generic options.
   ([Main Options Docs](https://ffmpeg.org/ffmpeg.html#Main-options))
1. **ADVANCED OPTIONS** - After the input file has been specified.
   ([Advanced Options Docs](https://ffmpeg.org/ffmpeg.html#Advanced-options))
1. **AUDIO OPTIONS** - After the audio stream is mapped and the encoder is selected.
   ([Audio Options Docs](https://ffmpeg.org/ffmpeg.html#Audio-Options))
   ([Advanced Audio Options Docs](https://ffmpeg.org/ffmpeg.html#Advanced-Audio-options))

```
ffmpeg \
    -hide_banner \
    -loglevel info \
    <CUSTOM MAIN OPTIONS HERE> \
    -i /path/to/input/video.mkv \
    <CUSTOM ADVANCED OPTIONS HERE> \
    -map 0:0 -map 0:1 \
    -c:v:0 copy \
    -c:a:0 aac \
    <CUSTOM AUDIO OPTIONS HERE> \
    -y /path/to/output/video.mkv 
```
:::

