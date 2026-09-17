
---

#### Links:

- [Unmanic Support](https://unmanic.app/discord)
- [Issues](https://github.com/audioscavenger/unmanic-plugins/issues)
- [Discussions/Requests](https://github.com/audioscavenger/unmanic-plugins/discussions)
- [Pull Requests](https://github.com/audioscavenger/unmanic-plugins/pulls)

Don't contact me with issues, I don't care. Most plugin maintainers code their own to fit their specific needs. If my plugins help you, great.

If you find a blatant bug or have a specific scenario, simply fix it yourself and submit a pull request like I do.

I will not ignore or deny pull requests, unlike most of the plugin maintainers I know. Yes I'm rude, you're welcome :)

---

#### Description:

##### Configuration Options

- Enter a comma delimited list of audio language codes and a comma delimited list of subtitle language codes to search for during library scans and new file event triggers - only streams matching these langauges are kept - all other streams are removed.
- You can enter * for the language code in one of the two stream types and it will keep all langauges for that stream type.  This is useful, for example, if you want to keep a given audio language and keep all subtitles (or vice versa)
- Discard Commentary - cecking this will remove commentary streams regardless of language, if any
- keep undefined will keep all undefined or untagged language code streams
- fail safe - if checked, this option will prevent the unitentional removal of all audio streams if the languages to remove does not intersect with any languages in the file.  If the fail safe is checked and the the check shows the
intersection of configured languages and actual stream languages to be null, the file will be skipped.  If you check the fail safe, it's also recommended to check the keep undefined option too.
- reorder_kept - if checked, this will reorder the kept audio streams by making the first stream(s) in the file, those streams that match the first audio language listed above; audio stream 0 will also have default disposition set.
- Set Multichannel or 2 channel - this option is only visible if reordering kept streams.  Specify if you prefer 2 channel or multichannel to be the default audio when the file has more than one stream that matches the first language tag in the list of audio languages
- keep_original_audio - this option, if enabled, will keep the original language even if you don't specify it in the list of languages.  however, you cannot leave the configured list of audio languages empty. this option will cause the next 2 options to display and you will need to configure the plugin with (free) TMDB API credentials. 
- tmdb_api_key - your tmdb API key
- tmdb_api_read_access_token - your tmdb read access token

:::note
Plugin now uses Python's langcodes module to check for valid language codes.  langcodes uses BCP 47 (IETF RFC 5646) to identify language codes - this subsumes ISO 639, which the plugin used prior to langcodes.  langcodes has a 
larger set of language  codes recognized by IETF.  You do not need to list both 2 letter and 3 letter versions of the code - if you specify `en`, and the actual code in the file is `eng`, it will still match and vice versa.
:::

---

##### Examples:

###### <span style="color:magenta">Keep English Audio and all Subtitles, remove all commentary streams, keep any untagged language streams, don't delete all audio streams, and reorder audio streams to put English audio first. If there are more than one english audio streams, prefer the multi-channel over stereo; do not do a lookup to find original audio:</span>

- `eng`
- `*`
- [x] Keep streams with no/undefined language tags
- [x] Discard commentary audio streams regardless of language
- [x] Fail-safe to prevent deletion of all audio streams
- [x] Reorder kept audio languages
- `set Multi-channel as default`
- [ ] Keep Original Audio Language


##### TMDB:

For information on the The Movie Database (tmdb):
- [The Movie Database (tmdb)](https://www.themoviedb.org/)

