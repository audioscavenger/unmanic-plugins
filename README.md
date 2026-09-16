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
[ ] registration process: Open an Issue or Pull Request on Unmanic
  1. Update About section: gear icon
    1. Topics: unmanic unmanic-plugin plugin-repository
  2. go to https://github.com/unmanic/unmanic
  3. Open a new Issue
  4. Provide them with your specific repository information:
    1. Name: AudioscavengeR Repo: Ultra Processors
    2. GitHub Page: https://github.com/audioscavenger/unmanic-plugins
    3. Raw repo.json URL: https://raw.githubusercontent.com/audioscavenger/unmanic-plugins/repo/repo.json
  
  

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
git add . && git stash
git checkout master
git stash pop
cp -rp backup/*.cmd ./
git commit -a -m "1.0.2"
git push

------------- master->repo
E:\GPT\miniconda3\python.exe E:\Gitea\unmanic-plugins\scripts\generate_repository.py
E:/GPT/miniconda3/python.exe E:/Gitea/unmanic-plugins/scripts/generate_repository.py
git add . && git stash
git checkout repo
git stash pop
cp -rp repo/*.* ./
git add .
git commit -a -m "1.0.1"
git push

-->