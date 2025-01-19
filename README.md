# Grug

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![mypy](https://img.shields.io/badge/mypy-checked-blue)](https://github.com/python/mypy)

A self-hostable tabletop-RPG GenAI bot

## Planned Features

- [ ] add github actions to build and deploy the image to the repo
- [ ] add docs for self hosting
- [ ] add docs for general usage and features of Grug
- [ ] add docs for roadmap and planned features
- [ ] create a way to enable others to use grug in their own server if they want
    - this would need to handle cost and be able to scale so that users can subscribe and then have the ability to
      invite Grug to their server.
- [ ] Initiative tracker
- [ ] Character creation / player sheet integration and tools
- [ ] Random encounter generator
- [ ] Random loot generator
- [ ] Random NPC generator
- [ ] Random dungeon generator
- [ ] rules lookup
    - users must upload their own rulebooks and content as that is typically closed source
    - some tools will be provided out of the box, such as AoN for Pathfinder, and
    - onlines resources that are open for use:
        - https://media.wizards.com/2018/dnd/downloads/DnD_BasicRules_2018.pdf
        - AoN for Pathfinder
- [x] dice roller
- [ ] music player
    - youtube search code: https://github.com/joetats/youtube_search/blob/master/youtube_search/__init__.py
    - youtube downloader: https://github.com/yt-dlp/yt-dlp
    - can use the above two to find and obtain music and then can create an agent to stream it into a voice channel
- [ ] session notes (by listening to the play session)
- [ ] scheduling and reminders
    - [ ] ability to send reminder for the upcoming session
    - [ ] food tracking feature (for in-person sessions where there is a rotation of who brings food)
    - [ ] ability to send reminder for who is bringing food
    - [ ] scheduling feature for when the next session will be, and who is available (find a time that works best for
      everyone)
- [ ] general chatbot functionality with a defined name and personality
