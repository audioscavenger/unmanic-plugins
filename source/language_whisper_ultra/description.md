
---

##### Links:

- [Unmanic Support](https://unmanic.app/discord)
- [Forked from](https://github.com/yajrendrag/plugin.detect_audio_language)
- [Issues/Feature Requests](https://github.com/audioscavenger/plugin.language_whisper_ultra/issues)
- [Pull Requests](https://github.com/audioscavenger/plugin.language_whisper_ultra/pulls)

---

##### Description:

This plugin detects streams audio language and adds a language tag with conditions: force rescan, ignore existing, etc.

Elect and labels the stream with the most frequently observed language among 1 to 6 30-seconds audio samples.

Uses OpenAI's Whisper Speech Recognition, will switch to Whisper-faster very soon.

https://github.com/openai/whisper
https://openai.com/index/whisper/

##### Configuration

#### <span style="color:blue">force_cpu</span>
The plugin defaults to using GPU, but if this option is checked it will bypass the GPU test and use the CPU for detection. CPU fallback is done after a load test of the model chosen and re-test all the smaller models it, in that order:

- turbo: 84% accuracy, 1.6GB FASTEST BESTEST",
- small: 73% accuracy, 470MB",
- base: 55% accuracy, 142 MB",
- tiny: 50% accuracy, 75 MB",

'medium' is purposefully excluded as it's garbage compared to large-v3-turbo which is 6x faster and same size anyways.

The plugin is checking 6 randomly selected, 30 second audio samples, so this
doesn't place a huge burden on the CPU and still executes very fast.  it should be selected if you do not have an nvidia GPU or if your GPU is low on memory.  There are known issues with Whisper not releasing
GPU memory until the calling process (unmanic) terminates.  this will avoid this issue.

#### <span style="color:blue">model_name</span>
'small' model is the default and gives 100% accuracy for 99.99% of use cases. Only use a larger model when you have exotic languages to identify.

#### <span style="color:blue">force_rescan</span>
Force reprocess all audio tracks

#### <span style="color:blue">force_samples</span>
Enable you to choose how many 30-seconds samples to randomely pull from the audio.

#### <span style="color:blue">samples</span>
Use only odd numbers: the logic is to elect a winner when multiple languages are detected.

#### <span style="color:blue">tag_style</span>
There is zero reason in 2026 to choose 2 characters for lang tag over 3 letters. This option will be removed in future releases.

Video files (like MKV and MP4) and media players (like Plex, Jellyfin, and VLC) strictly rely on a global broadcasting standard known as ISO 639-2 (or its modern successor, ISO 639-3).

3-Letter Codes Are for Media, Databases, & History (ISO 639-2 / ISO 639-3)Because 2 letters max out quickly, international library and media organizations realized they couldn't tag thousands of regional languages, historical languages, or distinct dialects.

Why movies need it: A movie might feature an audio track in a rare regional dialect, an ancient language, or a distinct variation that a 2-letter code physically cannot represent. For example:
- eng vs en (English)
- fre / fra vs fr (French)
- sco (Scots) - Has no 2-letter code
- tlh (Klingon) - An actual registered 3-letter media tag used for sci-fi movies, which is impossible in a 2-letter system


:::important
This plugin is installed using the init.d system script, and whisper is pip installed as part of the the plugin installation.

This means that at the time the plugin is installed, whisper is not necessarily operational, so Unmanic should be restarted after this plugin is installed.

Also you may need to force install dependencies yourself and purge the cache:
1. `~/.unmanic/plugins/language_whisper_ultra/init.d/install_deps.sh`
2. `pip cache purge`
3. restart Unmanic

:::
