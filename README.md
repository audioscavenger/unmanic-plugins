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