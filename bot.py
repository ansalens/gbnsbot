import logging
from os import getenv
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, ConversationHandler, MessageHandler, filters
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
import lib_scraper

"""TO-DO:
1. Automatski prelazak na library funkciju bez /library
2. Ispisivanje greski na ekran umesto ubijanje programa
3. Automatizuj na svakih pola sata izvrsavanje
"""

load_dotenv()
TOKEN = getenv('BOT_TOKEN')
PICK_LIBRARY, SEARCH = range(2)
keyboard = [["1", "2"]]
indexed = lib_scraper.indexed
markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING
)

async def start(update, context):
    if len(context.args) < 1:
        await update.message.reply_text(
            "/start <NASLOV>, <AUTOR>\n"
            "/start <NASLOV>", reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    args = " ".join(context.args).split(',')
    user_data = context.user_data
    user_data['title'] = args[0]
    
    if len(args) == 2:
        user_data['author'] = args[1]
    else:
        user_data['author'] = ''
    
    return PICK_LIBRARY


async def get_library(update, context):
    """Take user input for library of choice, return subdict of libraries."""
    msg = "Biblioteke:\n"
    for index, lib in indexed.items():
        msg += f"{index}) {lib[0]}\n-> {lib[1]}\n-> {lib[2]}\n"

    await update.message.reply_text(msg, reply_markup=markup)

    return SEARCH


async def search(update, context):
    choice = update.message.text
    user_data = context.user_data

    library = lib_scraper.libraries[indexed[choice][0]]
    title = user_data['title']
    author = user_data['author']

    msg = lib_scraper.telegram(title, author, library)
    if msg:
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text(f"{user_data['title']} | {indexed[choice][0]} - NEDOSTUPNA")

    return ConversationHandler.END


def main():
    bot = ApplicationBuilder().token(TOKEN).build()
    
    flow_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start)],
            states = {
                PICK_LIBRARY: [CommandHandler("library", get_library)],
                SEARCH: [MessageHandler(filters.Regex("^(1|2)$"), search)]
            },
            fallbacks = [CommandHandler("start", start)],
    )

    bot.add_handler(flow_handler)
    bot.run_polling(allowed_updates=Update.ALL_TYPES)


main()