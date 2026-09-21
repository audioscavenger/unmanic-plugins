
---

##### Links:

- [Unmanic Support](https://unmanic.app/discord)
- [Issues](https://github.com/audioscavenger/unmanic-plugins/issues)
- [Discussions/Requests](https://github.com/audioscavenger/unmanic-plugins/discussions)
- [Pull Requests](https://github.com/audioscavenger/unmanic-plugins/pulls)

Don't contact me with issues. Most plugin maintainers code their own to fit their specific needs. If my plugins help you, great.

If you find a blatant bug or have a specific scenario, simply fix it yourself and submit a pull request.

---

##### Description:

This Plugin is intended for filtering out any of the 6 `codec_type` recognized by FFmpeg: 
- video
- audio
- subtitle
- attachment  (can be TTF/OTF fonts for instance)
- data
- unknown

It does not care what the stream is. If you need to remove images stored as video streams, use Josh.5's `strip_image_streams` plugin instead.

Data or attachment streams are not automatically selected and can only be included using -map. 

---

##### Notes:

The 'unknown' additional_stream_specifier is not defined, as seen at https://ffmpeg.org/ffmpeg.html#Stream-specifiers-1 . 
There are only 5 stream_type_idents: v,a,s,d and t. not 'u'. Therefore, StreamMapper class cannot handle it. 

Also at https://ffmpeg.org/ffmpeg.html#Automatic-stream-selection it's clear that Data or attachment streams are not automatically selected and can only be included using -map. 
'unknown' streams cannot be mapped and ffmpeg simply takes an extra parameter for unknown streams as defined in https://ffmpeg.org/ffmpeg.html#Advanced-options: `-ignore_unknown` or `-copy_unknown`. 

Therefore, it's not something StreamMapper should handle since there is no expected transformation mapping at all.

Conclusion, plan: we simply add a parameter in the advanced_options, to copy or remove unknown codec_type streams.

---

##### Documentation:

For information on the available encoder settings:
- [FFmpeg Stream-specifiers](https://ffmpeg.org/ffmpeg.html#Stream-specifiers-1)
- [FFmpeg Stream Selection](https://ffmpeg.org/ffmpeg.html#Automatic-stream-selection)
- [FFmpeg Advanced-options](https://ffmpeg.org/ffmpeg.html#Advanced-options)

--- 

### Config description:

#### <span style="color:blue">Keep video/audio/subtitle</span>
It's likely what you want at all times.

#### <span style="color:blue">Keep attachment/data</span>
Data or attachment streams are not automatically selected and can only be included using -map. 

#### <span style="color:blue">Keep unknown</span>
God knows what 'unknown' stream can contain. 

