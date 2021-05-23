import argparse
import logging
from typing import List

from telegram import Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater,
)


# AO3 story URLS look like https://archiveofourown.org/works/WORK_ID/chapters/CHAPTER_ID
AO3_STORY_URL_STARTS = [
    "https://archiveofourown.org/works",
    "archiveofourown.org/works",
]


def normalize_url(url: str) -> str:
    """Add explicit HTTPS schema to schema-less links"""
    if not url.startswith("https://"):
        return f"https://{url}"
    return url


def find_ao3_story_urls(text: str) -> List[str]:
    """
    Return a list of all AO3 story URLs in `text`

    URLs are normalized with `normalize_url()`
    """
    links = []
    # AO3 URLS
    for word in text.split():
        for link_start in AO3_STORY_URL_STARTS:
            if word.startswith(link_start):
                links.append(normalize_url(word))
                break

    logging.debug(f"Found AO3 links {links}")
    return links


def start_command(update: Update, context: CallbackContext) -> None:
    """Respond to /start with a greeting and the /help message"""
    logging.info(f"Responding to /start in chat {update.effective_chat.full_name}")
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Hello! I'm the AO3 Tag Bot",
    )
    help_command(update, context, quiet=True)


def help_command(
    update: Update, context: CallbackContext, *, quiet: bool = False
) -> None:
    """Respond to /help with an explanation of the bot"""
    if not quiet:
        logging.info(f"Responding to /help in chat {update.effective_chat.full_name}")
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="I respond to messages containing AO3 links with the tags of the linked story",
    )


def message_reply(update: Update, context: CallbackContext) -> None:
    logging.debug(f"Received message in chat {update.effective_chat.full_name}")

    urls = find_ao3_story_urls(update.message.text)
    if urls:
        logging.debug(f"Found AO3 URLs {urls} in message")
        for url in urls:
            context.bot.send_message(chat_id=update.effective_chat.id, text=url)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="A Telegram bot that responds to AO3 links with the tags of the linked story"
    )
    parser.add_argument("token", help="Telegram Bot API token")
    parser.set_defaults(log_level=logging.INFO)
    log_options = parser.add_mutually_exclusive_group()
    log_options.add_argument(
        "-v",
        "--verbose",
        dest="log_level",
        action="store_const",
        const=logging.DEBUG,
        help="Increase log verbosity",
    )
    log_options.add_argument(
        "-q",
        "--quiet",
        dest="log_level",
        action="store_const",
        const=logging.WARNING,
        help="Reduce log verbosity",
    )

    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=args.log_level,
    )
    updater = Updater(token=args.token)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(CommandHandler("help", help_command))

    dispatcher.add_handler(
        MessageHandler(Filters.text & ~Filters.command, message_reply)
    )

    updater.start_polling()

    # exit on Ctrl-C
    updater.idle()


if __name__ == "__main__":
    main()
