# AudioscavengeR Repo: Ultra Processors

## Instructions

### Repo URL:
```
https://raw.githubusercontent.com/audioscavenger/unmanic-plugins/repo/repo.json
```


Follow the Unmanic Documentation for:
 - [Adding this repo to your Unmanic installation](http://docs.unmanic.app/docs/plugins/adding_a_custom_plugin_repo/)
 - [Creating your own repository to host plugins for Unmanic](https://docs.unmanic.app/docs/development/plugin_repos/creating_your_own_repo)
 - [Developing Plugins for Unmanic](https://docs.unmanic.app/docs/development/developing_plugins)


## Links

- [Unmanic Documentation](https://docs.unmanic.app/docs/)
- [License](/LICENSE)

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) to learn how to contribute to Unmanic's Plugins.

## PLUGINS HOW TO

1. Make sure you add a link to ffmpeg tools in a `lib` folder:
```bash
mkdir lib
cd lib
git rm -r ffmpeg
git submodule add https://github.com/Josh5/unmanic.plugin.helpers.ffmpeg ./ffmpeg
```

2. `ffmpeg/stream_mapper.py` does build the ffmpeg options in that order:
  1. generic_options: before input
  `-hide_banner -loglevel info -fflags +genpts`
  
  2. main_options: no idea what that is
  
  3. advanced_options: default cache and experimental code banned (strict 2 = strict, goes all to way to -2 = anything possible)
  `-strict 2 -max_muxing_queue_size 4096`

### -strict 2

In FFmpeg, the flag -strict 2 (which can also be written as -strict experimental) allows FFmpeg to use experimental encoders and decoders that are not yet considered fully stable or safe by the FFmpeg development team.
FFmpeg enforces a strict compliance scale. By default, it will block you from using experimental codecs to prevent accidental audio/video corruption or unexpected crashes. Setting -strict 2 lowers that safety guardrail.

The -strict flag accepts numeric values or text aliases. Here is how they rank from safest to most experimental:

| Value | Alias | What it does |
|---|---|---|
| 2 | very | Strictly conforms to all older, ultra-stable standards. |
| 1 | strict | Strictly conforms to standard specifications. |
| 0 | normal | Default. Allows normal, stable operations. |
| -1 | unofficial | Allows unofficial experimental extensions. |
| -2 | experimental | Allows experimental code (same as passing -strict 2 or -strict -2). |

### -max_muxing_queue_size 4096

The flag -max_muxing_queue_size 4096 allocates more memory to buffer audio and video data right before it is written into the final video file.

By default, FFmpeg uses a small queue size (often 128 packets). Increasing it to 4096 gives FFmpeg a massive safety cushion to prevent a common crash known as the "Too many packets buffered for output stream" error.


## TODO
[x] where does gitmodules.txt come from and should I host it: comes from Unmanic official sources, can be ignored
[x] how do I list my repo to Community Repositories: repository index file must be registered into Unmanic's central database tracker
[x] registration process: https://docs.unmanic.app/docs/development/plugin_repos/creating_your_own_repo/


<!-- 
---------- create main
git checkout -b main
git push -u origin main

---------- github: switch to main default
---------- delete local examples
git branch -d examples
git push origin --delete examples

---------- first commit
git add .
git commit -m "Initial commit of unmanic repository"
git push origin main


------------- repo is actually a branch
git push origin --delete repo
git checkout --orphan repo
git rm -rf .
cp -rp repo/*.* ./ 2>/dev/null || touch .gitkeep
git add .
git commit -m "Initial commit for repo root branch"
git push -u origin repo

------------- lib reference
cd lib
git rm -r ffmpeg
git submodule add https://github.com/Josh5/unmanic.plugin.helpers.ffmpeg ./ffmpeg

for folder in source/*; do cd $folder/lib/ffmpeg; git pull; cd -; done

------------- repo->main
git add . && git stash
git checkout main
git stash pop
cp -rp backup/*.cmd ./
git add .
git commit -a -m "1.0.4"
git push

------------- main->repo
E:\GPT\miniconda3\python.exe E:\Gitea\unmanic-plugins\scripts\generate_repository.py
E:/GPT/miniconda3/python.exe E:/Gitea/unmanic-plugins/scripts/generate_repository.py
git add . && git stash
git checkout repo
git stash pop
cp -rp repo/*.* ./
cp -rp repo/* ./
git add .
git commit -a -m "1.0.4"
git push

-->