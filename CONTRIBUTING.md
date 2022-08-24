# Contributing
Please note we have a code of conduct, please follow it in all your interactions with the project.

Table of Contents
=================
- [Contributing](#contributing)
- [Table of Contents](#table-of-contents)
  - [Coding Standard for Conventional Commits on Git](#coding-standard-for-conventional-commits-on-git)
    - [Follow prefix of a type](#follow-prefix-of-a-type)
    - [Examples](#examples)
  - [Pull Request](#pull-request)
  - [Branch](#branch)
  - [Continuous Integration](#continuous-integration)
    - [Adopt Jenkins](#adopt-jenkins)
    - [How To Trigger CI?](#how-to-trigger-ci)

## Coding Standard for Conventional Commits on Git
- [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)
- [Enhance your git log with conventional commits](https://dev.to/maxpou/enhance-your-git-log-with-conventional-commits-3ea4)
### Follow prefix of a type
  
| Type | Title | Description |
| -------- | -------- | -------- |
| feat | Feature | Add a new feature (not a new feature for build script) |
| fix | Bug Fix | Fix a bug (not a fix to a build script) |
| docs | Documentation | Edit the documentation |
| style | Style | Change the code (white-space, formatting, missing semi-colons, etc) that do not affect the meaning of the code |
| refactor | Refactor Code | Refactor code that neither fixes a bug nor adds a feature |
| perf | Improve Performance | Change code to improve performance |
| test | Test | Add missing tests or correcting existing tests |
| build | Build | Make changes that affect the build system or external dependencies (example scopes:npm) |
| ci | Continuous Integration | Change CI configuration files and scripts (example scopes: Jenkins) |
| cd | Continuous Deployment | Change CD configuration files and scripts(example:deployment.yaml)
| chore | Chore | Make other changes that don't modify src or test files |
| revert | Revert | Revert a previous commit |
| vendor | Vendor | Update version for dependencies, packages.

### Examples
  
| Good | Bad | 
| :-------- | :-------- |
| 06faab4d revert: feat: add disabled property <br>186cce90 feat: add disabled property <br>5b998d9a test: add scenario for readonly property <br>263288a5 fix: fix css when hover <br>c3fb85af feat: add button component | daccff1f test should pass <br>3fff19f6 test should pass <br>5b998d9a add disabled property for button <br>06faab4d fix lint <br>186cce90 refactor button <br>4b99d91a fix spinner component <br>5b998d9a fix css <br>263288a5 test should pass <br>c3fb85af Create Button component <br> |

- It's hard to understand the Component's history. We might repeat errors already fixed.
- There are unnecessary commits which pollute logs and make history hard to read. Also, functionalities like git blame become irrelevant.
- It seems that a feature was added by a few commits. Which commit should I include if I want to revert this operation?

## Pull Request
- Must assign at least one reviewer
- Must `rebase` on `master` branch before merge
- Must use a meaningful pull request name
- Must full-fill description and summary

## Branch
- Must use the meaningful branch name
- Must using feature/ as feature branch name prefix

## Continuous Integration
### Adopt Jenkins 
- Run [Jenkinsfile]() build spec file in repository
### How To Trigger CI?
- Trigger manually in [Jenkins]() and select your build parameter

