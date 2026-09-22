
---

#### Links:

- [Unmanic Support](https://unmanic.app/discord)
- [Issues](https://github.com/audioscavenger/unmanic-plugins/issues)
- [Discussions/Requests](https://github.com/audioscavenger/unmanic-plugins/discussions)
- [Pull Requests](https://github.com/audioscavenger/unmanic-plugins/pulls)

Don't contact me with issues. Most plugin maintainers code their own to fit their specific needs. If my plugins help you, great.

If you find a blatant bug or have a specific scenario, simply fix it yourself and submit a pull request.

---

#### Description:

This plugin uses faster-whisper to listen and transcode audio streams into SRT subtitles.

Creates SRT files with detected languages, and has an option to also includes foreign languages songs when detected (adds up to processing time).

Original container or target container **MUST** be MKV/MP4/MOV if you want the subtitles to be embedded.

:::important
You **must** restart Unmanic/reboot the container to get Whisper dependencies installed (unless you already use _language_whisper_ultra_).
:::

Uses **faster-whisper** Speech Recognition: eats up only 500MB (excluding models) versus 10GB for OpenAI's Whisper.

https://github.com/SYSTRAN/faster-whisper

---

#### Configuration

##### <span style="color:blue">force_cpu</span>

Force CPU processing when you know that you don't have a GPU.

CPU fallback is automatic after a GPU load test of the model chosen. If the reason is Out of Memory, it will re-test all the smaller models in that order:

- turbo: 84% accuracy, 1.6GB FASTEST BESTEST",
- small: 73% accuracy, 470MB",
- base: 55% accuracy, 142 MB",
- tiny: 50% accuracy, 75 MB",

'medium' is purposefully excluded as it's garbage compared to large-v3-turbo, which is 6x faster, same size and same accuracy.

#### <span style="color:blue">model_name</span>

'small' model is the default and gives 73% accuracy for all languages, and 100% for Western languages.

:::important
Ensure that your container has 2.2GB of free space for `large-v3-turbo` (500MB + 1.6GB), otherwise refer to the model sizes above.
:::

#### <span style="color:blue">embed_subtitles</span>

Embeds the SRT generated in the container when possible. Otherwise, only generates SRT files like `movie name.XX.srt`.

Jellyfin and Radarr require language code in the SRT file names to be 2-letters.


#### <span style="color:blue">force_overwrite</span>

Generate SRT even when they already exist.

#### <span style="color:blue">multilingual</span>

By default the whole audio stream is transcribed assuming a single detected language. 
Enable this to detect the language independently for each spoken segment, so passages in a different language (e.g. a Japanese song in an English dub) are transcribed correctly too. 

This runs language detection many more times and **noticeably increases processing time**.


:::important
This plugin is installed using the init.d system script, and whisper is installed by pip/venv as part of the the plugin installation **at boot time only**.

This means that at the time the plugin is installed, you **must** restart Unmanic (or reboot the container) to use this plugin.

Also you may need to force install dependencies yourself and purge the cache:
1. `~/.unmanic/plugins/subtitle_from_audio_ultra/init.d/install_deps.sh`
2. `pip cache purge`
3. restart Unmanic
:::
