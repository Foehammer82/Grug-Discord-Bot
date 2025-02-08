# Contributing

We welcome contributions to this project. This CONTRIBUTING.md is currently a work in progress, more details to come. In
the meantime, feel free to fork and submit a pull request or post an issue if you have any questions or suggestions.

## Git Commit Guidelines

We are following
the [AngularJS Git Commit Guidelines](https://github.com/angular/angular.js/blob/master/DEVELOPERS.md#-git-commit-guidelines)
for this project, which is what drives versioning and changelog generation. Please read the guidelines before
submitting a pull request.

### Quick Reference

Git commit prefix must be one of the following:

- Patch Releases:
    - `fix:` A bug fix
    - `docs:` Documentation only changes
    - `style:` Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc)
    - `refactor:` A code change that neither fixes a bug nor adds a feature
    - `chore:` Changes to the build process or auxiliary tools and libraries such as documentation generation
    - `test:` Adding missing or correcting existing tests
- Minor Release:
    - `feat:` A new feature
- Major Release:
    - `perf:` A code change that improves performance
    - `BREAKING CHANGE:` A commit that has a breaking change

If no commit message contains any information, then default_bump will be used.
