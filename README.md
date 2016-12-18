# err-github-merger

This plugin allows you to merge your projects' branches on GitHub using [Errbot](http://errbot.io/en/latest/).

Reasons why you might use this plugin:
* provide a consistent way of merging branches, using whatever flags you find most appropriate
* make it easy for non-technical users on your team to use your given merge style
* allow your Errbot server to [sign all merges](https://github.com/blog/2144-gpg-signature-verification) with its GPG key
* make it possible to do merges from your team's chat platform (Slack, HipChat, IRC, or any other backend supported by Errbot)
* reduce the number of users with write access to your repos

## Features

* supports merging to multiple repositories
* signs merges using GPG key
* merge commits include comprehensive authorship data:
    * the bot user as the committer
    * author of the branch as the author of the giver commit as the author
    * full name of the invoking user (the user who issues the command) as part of the commit message
* blacklist certain branches from being merged
* deletes branches after merging

## Installation

### Requirements:

* configure the plugin according to the template:
```
{
    'REPOS_ROOT': '/home/web/repos/',
    'forbidden_branches': ['master', 'develop'],  # Can't merge these
    'projects': {
        # Name of the project in GitHub
        'some-project': 'git@github.com:netquity/some-project.git',
    },
}
```
* git version 2.11.0 or greater must be installed on the server
* your server must have access to the repositories you want to merge into
    * [machine user](https://developer.github.com/guides/managing-deploy-keys/#machine-users): can have access to multiple repositories

### Required only if you want to sign your commits:

* your GPG key must be
    * imported on your server
    * configured for your machine user's GitHub account
* set the authorship information in your server's `.gitconfig` to match your machine user:
```
[user]
        email = <the email used with your GPG key>
        signingkey = <your GPG fingerprint>
[commit]
        gpgsign = true
```

## Use

* For your `Foo` project, merge branch `bar` to `develop`:

```
!merge --branch-name bar --project-name foo
```

### Caveats

* Only supports merging to `develop` at this time
* The merge strategy is not configurable yet; if you want a different strategy, fork the repo

## Related Plugins

* [err-github-jira-release](https://github.com/netquity/err-github-jira-release)
    * Perform version releases between JIRA and GitHub
* [err-fabric](https://github.com/netquity/err-fabric)
    * Invoke Fabric commands using Errbot to handle tasks like deployments, status checks, etc.
