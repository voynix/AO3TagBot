import argparse
import logging
from typing import Dict, List, Optional

from bs4 import BeautifulSoup
import requests
from telegram import Chat, ParseMode, Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater,
)


# AO3 story URLS look like https://archiveofourown.org/works/WORK_ID[/chapters/CHAPTER_ID]
AO3_STORY_URL_STARTS = [
    "https://archiveofourown.org/works",
    "archiveofourown.org/works",
]

# seconds to wait for responses from AO3
REQUEST_TIMEOUT = 15

# maximum message length allowed by the telegram API
MAXIMUM_MESSAGE_LENGTH = 4096


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


def get_tags_from_list(soup: BeautifulSoup, tag_list_class: str) -> Optional[str]:
    tag_list_node = soup.find("dd", class_=tag_list_class)
    if not tag_list_node:
        return None
    tags = []
    for tag_node in tag_list_node.find_all("a"):
        tags.append(tag_node.string)
    return ", ".join(tags)


def get_tags_for_story_url(url: str) -> Optional[Dict[str, str]]:
    logging.debug(f"Retrieving and extracting tags from {url}")
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    if response.status_code != 200:
        logging.debug(f"Got non-200 status code {response.status_code} for URL {url}")
        return None
    soup = BeautifulSoup(response.text, "html.parser")

    # this is where the fun begins!
    tag_info = {}
    title_node = soup.find("h2", class_="title")
    if title_node:
        tag_info["title"] = title_node.string
    tag_info["rating"] = get_tags_from_list(soup, "rating")
    tag_info["warnings"] = get_tags_from_list(soup, "warning")
    tag_info["categories"] = get_tags_from_list(soup, "category")
    tag_info["fandoms"] = get_tags_from_list(soup, "fandom")
    tag_info["relationships"] = get_tags_from_list(soup, "relationship")
    tag_info["characters"] = get_tags_from_list(soup, "characters")
    tag_info["tags"] = get_tags_from_list(soup, "freeform")

    # filter tags we failed to find out of tag_info
    tag_info = {k: v for k, v in tag_info.items() if v is not None}

    return tag_info


def get_messages_for_story(url: str, tag_info: Dict[str, str]) -> List[str]:
    """
    Construct the message text for the given tag_info, splitting the message text into multiple
    messages if it exceeds the MAXIMUM_MESSAGE_LENGTH
    """
    message_text = ""
    if "title" in tag_info:
        message_text += f"\n<b>{tag_info['title']}</b>"
    for key in [
        "rating",
        "warnings",
        "categories",
        "fandoms",
        "relationships",
        "characters",
        "tags",
    ]:
        if key in tag_info:
            message_text += f"\n<b>{key.capitalize()}:</b> {tag_info[key]}"
    if not message_text:
        message_text = f"Could not extract tags for {url}; is the story locked?"

    if len(message_text) > MAXIMUM_MESSAGE_LENGTH:
        logging.debug(
            f"Message for {url} exceeds maximum length {MAXIMUM_MESSAGE_LENGTH}; splitting into chunks"
        )
    return [
        message_text[i : i + MAXIMUM_MESSAGE_LENGTH]
        for i in range(0, len(message_text), MAXIMUM_MESSAGE_LENGTH)
    ]


def get_chat_name(chat: Chat) -> Optional[str]:
    if chat.full_name is not None:  # DMs
        return f"DMs with '{chat.full_name}'"
    if chat.title is not None:  # channel or (super)group
        return f"channel or group '{chat.title}'"
    return None


def start_command(update: Update, context: CallbackContext) -> None:
    """Respond to /start with a greeting and the /help message"""
    logging.info(f"Responding to /start in chat {get_chat_name(update.effective_chat)}")
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
        logging.info(
            f"Responding to /help in chat {get_chat_name(update.effective_chat)}"
        )
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="I respond to messages containing AO3 links with the tags of the linked story",
    )


def message_reply(update: Update, context: CallbackContext) -> None:
    logging.debug(f"Received message in chat {get_chat_name(update.effective_chat)}")

    urls = find_ao3_story_urls(update.message.text)
    if urls:
        logging.debug(f"Found AO3 URLs {urls} in message")
        for url in urls:
            # TODO: error handling
            # TODO: wrap in a try/except that does something generic but sane
            tag_info = get_tags_for_story_url(url)
            if tag_info is None:
                message_texts = [
                    f"Could not extract tags for {url}; does the story exist?"
                ]
            else:
                message_texts = get_messages_for_story(url, tag_info)

            for message_text in message_texts:
                logging.info(
                    f"Sending message to {get_chat_name(update.effective_chat)} for URL {url}"
                )
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message_text,
                    parse_mode=ParseMode.HTML,
                )


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
