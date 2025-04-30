import logging
from os import getenv
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, ConversationHandler, MessageHandler, filters
from telegram.ext.filters import MessageFilter
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
import lib_scraper


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)


"""TO-DO:
*. Automatski prelazak na library funkciju bez /library
*. Ispisivanje greski na ekran umesto ubijanje programa
3. Automatizuj na svakih pola sata izvrsavanje
"""

class RequiredDataFilled(MessageFilter):
    def filter(self, context):
        user_data = context.user_data
        if user_data.get('naslov') and user_data.get('biblioteka'):
            return True
        return False


load_dotenv()
TOKEN = getenv('BOT_TOKEN')
CHOOSE, SET_VALUE, SEARCH = range(3)
indexed = lib_scraper.indexed


async def showOptions(update, context):
    options = [["Naslov", "Autor", "Biblioteka", "Pretrazi"]]
    markup_options = ReplyKeyboardMarkup(options, one_time_keyboard=True)
    await update.message.reply_text('Izaberi opciju:', reply_markup=markup_options)


async def start(update, context):
    await showOptions(update, context)
    return CHOOSE


async def makeChoice(update, context):
    user_data = context.user_data
    text = update.message.text.lower()
    user_data['choice'] = text
    
    if text == 'autor':
        await update.message.reply_text("Unesi autora knjige.")
    elif text == 'naslov':
        await update.message.reply_text("Unesi naslov knjige.")
    elif text == 'biblioteka':
        library = [["1", "2"]]
        markup = ReplyKeyboardMarkup(library, one_time_keyboard=True)
        msg = "Biblioteke:\n"
        for index, lib in indexed.items():
            msg += f"{index}) {lib[0]}\n-> {lib[1]}\n-> {lib[2]}\n"

        await update.message.reply_text(msg, reply_markup=markup)
    elif text == 'pretrazi':
        if user_data.get('naslov') and user_data.get('biblioteka'):
            await update.message.reply_text("Pretrazujem...")
            await search(update, context)
        else:
            await update.message.reply_text("Potrebno uneti ime knjige i izabrati biblioteku!")
    
    return SET_VALUE


async def recordData(update, context):
    text = update.message.text
    user_data = context.user_data
    data = user_data['choice']
    user_data[data] = text
    del user_data['choice']
    
    msg = "UPISANO:\n"
    for key, value in user_data.items():
        msg += f"{key} -> {value}\n"
    
    await update.message.reply_text(msg)
    await showOptions(update, context)
    
    return CHOOSE


async def search(update, context):
    user_data = context.user_data

    _ = user_data['biblioteka']
    library = lib_scraper.libraries[indexed[_][0]]
    title = user_data['naslov']
    
    if user_data.get('autor'):
        author = user_data['autor']
    else:
        author = ''

    msg = lib_scraper.telegram(title, author, library)
    if msg:
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text(f"{title} | {indexed[_][0]} - NEDOSTUPNA")

    user_data.clear()
    return ConversationHandler.END


async def cancel(update, context):
    await update.message.reply_text("Pretraga zaustavljena", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main():
    bot = ApplicationBuilder().token(TOKEN).build()
    
    flow_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start)],
            states = {
                CHOOSE: [MessageHandler(filters.Regex("^(Naslov|Autor|Biblioteka|Pretrazi)"), makeChoice)],
                SET_VALUE: [MessageHandler(filters.TEXT, recordData)]
            },
            fallbacks = [CommandHandler("cancel", cancel)],
    )

    bot.add_handler(flow_handler)
    bot.run_polling(allowed_updates=Update.ALL_TYPES)


main()
