<p align="center">
  <a href="./"><img src="./assets/grug.png" alt="Grug" width="200"></a>
</p>

# Grug Discord Agent

Grug is a self-hostable tabletop-RPG GenAI Agent designed to enhance your RPG experience by providing useful tools
and capabilities through intelligent responses and interactions.

## Features

> TODO: this is just a quick brain dump, need to clean this up and write out more thorough descriptions of the features.

- respond to messages in chat and direct-messages
- can listen and respond in voice chat (and can talk though speach is still in development)
- scheduling and reminders
- can be COMPLETELY customized for your server (when you self-host)
    - can name the agent whatever you want (does not need to be grug, and will respond to the name given)
    - can customize the agents persona, we have an example of how we defined Grug, you can override that to give your
      agent whatever personality and baseline instructions you want
- currently is tightly coupled with OpenAI, but we are working on expanding this to other common AI services, including
  self-hosted ones
- Grugs tools he can use during responses and interactions:
    - dice roller
    - rules lookup (currently tightly coupled to pathfinder, but we have plans to expand this and enable users to
      provide their own rulebooks and upload them to the agent for RAG)

> TODO: add a whole section of the docs showing example uses of grug and how to interact with him

## Potential Future Features

- grugs jukebox companion bot (for playing music in voice chat)
    - idea here is to be able to set background sound for your party or to play music for ambiance
- Grug DM
    - still working through how best to do this, but we'd like to be able to let grug be able to DM campaigns and
      one-shots, though maybe with some human hand-holding and group tooling to avoid common pitfalls of AI generated
      content.
    - auto generate dungeons, encounters, and maps
    - auto generate NPCs
    - auto generate loot
    - be able to understand character sheets and help players level up and manage their characters

> TODO:note to force build... delete me
