# AO3TagBot

A [Telegram](https://telegram.org) bot that responds to messages with links to [AO3](https://archiveofourown.org) stories with a summary of the
tags for that story.

## Quickstart

You will need a [Telegram bot token](https://core.telegram.org/bots#3-how-do-i-create-a-bot).

```
pip install -r requirements.txt
python3 main.py --help
…
python3 main.py TOKEN
```

## Running under systemd

To run AO3TagBot in a more durable manner, an example systemd [unit file](ao3tagbot.example.service) is provided.

## Caveats

AO3TagBot needs access to all group messages, not just messages mentioning it, to function. You will need to disable
[privacy mode](https://core.telegram.org/bots#privacy-mode) for AO3TagBot and make AO3TagBot a mod in each group it's
added to in order to allow this.
