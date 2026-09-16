# Unmanic Plugins by AudioscavengeR

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
[ ] where does gitmodules.txt come from and should I host it
[ ] how do i submit my repo
[ ] submit my repo


<!-- 
---------- create master
git checkout -b master
git push -u origin master

---------- github: switch to master default
---------- delete local examples
git branch -d examples
git push origin --delete examples

---------- first commit
git add .
git commit -m "Initial commit of unmanic repository"
git push origin master


------------- repo is actually a branch
git push origin --delete repo
git checkout --orphan repo
git rm -rf .
cp -rp repo/*.* ./ 2>/dev/null || touch .gitkeep
git add .
git commit -m "Initial commit for repo root branch"
git push -u origin repo

------------- repo->master
git checkout master
cp -rp backup/*.cmd ./
------------- master->repo
E:\GPT\miniconda3\python.exe E:\Gitea\unmanic-plugins\scripts\generate_repository.py
E:/GPT/miniconda3/python.exe E:/Gitea/unmanic-plugins/scripts/generate_repository.py
git checkout repo
cp -rp backup/*.cmd ./
git add .
git commit -m "1.0.1"
git push

-->