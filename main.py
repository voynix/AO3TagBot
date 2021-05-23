import argparse
import logging

from telegram import Update
from telegram.ext import CallbackContext, CommandHandler, Updater


def start_command(update: Update, context: CallbackContext) -> None:
    logging.info(f"Responding to /start in chat {update.effective_chat.full_name}")
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Hello! AO3 Tag Bot responds to messages containing AO3 links with the tags of the linked story",
    )


def help_command(update: Update, context: CallbackContext) -> None:
    logging.info(f"Responding to /help in chat {update.effective_chat.full_name}")
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="AO3 Tag Bot responds to messages containing AO3 links with the tags of the linked story",
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

    updater.start_polling()

    # exit on Ctrl-C
    updater.idle()


if __name__ == "__main__":
    main()
