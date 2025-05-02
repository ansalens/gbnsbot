import logging
from os import getenv
from telegram.ext import (ApplicationBuilder, filters,
                          CommandHandler, ConversationHandler, MessageHandler,)
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from dotenv import load_dotenv
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

load_dotenv()
TOKEN = getenv('BOT_TOKEN')
CHOOSE, SET_VALUE = range(2)
indexed = lib_scraper.indexed


async def show_options(update, context):
    options = [["Naslov", "Autor", "Biblioteka", "Pretrazi"]]
    markup_options = ReplyKeyboardMarkup(options, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text('Izaberi opciju za podesavanje ⬇️', reply_markup=markup_options)
    return CHOOSE


async def start(update, context):
    return await show_options(update, context)


async def make_choice(update, context):
    user_data = context.user_data
    text = update.message.text.lower()
    user_data['choice'] = text
    
    if text == 'autor':
        await update.message.reply_text("Upisi autora knjige.")
    elif text == 'naslov':
        await update.message.reply_text("Upisi naslov knjige.")
    elif text == 'biblioteka':
        library = [["1", "2"]]
        markup = ReplyKeyboardMarkup(library, resize_keyboard=True, one_time_keyboard=True)        
        msg = "Biblioteke u ponudi\n"
        for index, lib in indexed.items():
            msg += f"{index}) {lib[0]}\n▫ {lib[1]}\n▫ {lib[2]}\n"

        await update.message.reply_text(msg, reply_markup=markup)
    elif text == 'pretrazi':
        if user_data.get('naslov') and user_data.get('biblioteka'):
            return await search(update, context)
        
        await update.message.reply_text("Potrebno uneti ime knjige i izabrati biblioteku ⚠")
        return CHOOSE
        
    return SET_VALUE

async def record_data(update, context):
    user_data = context.user_data
    if not user_data.get('choice'):
        return await show_options(update, context)

    text = update.message.text
    data = user_data['choice']
    user_data[data] = text
    del user_data['choice']
    
    return await show_options(update, context)

async def search(update, context):
    user_data = context.user_data
    _ = user_data['biblioteka']
    library_name = indexed[_][0]
    library = lib_scraper.libraries[library_name]
    title = user_data['naslov']
    msg = f"Pretrazujem 🔎\n🔸 {title} 📕\n🔸 {library_name} 🏫"

    if user_data.get('autor'):
        author = user_data['autor']
        msg += f"\n🔸 {author} ✒"
    else:
        author = ''

    await update.message.reply_text(msg)

    results = lib_scraper.telegram(title, author, library)
    
    if results:
        await update.message.reply_text(results, reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text(f"{title} | {indexed[_][0]} - NEDOSTUPNA")

    user_data.clear()
    
    return ConversationHandler.END

async def cancel(update, context):
    await update.message.reply_text("Pretraga zaustavljena ⚠", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    bot = ApplicationBuilder().token(TOKEN).build()    
    flow_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start)],
            states = {
                CHOOSE: [MessageHandler(filters.Regex("^(Naslov|Autor|Biblioteka|Pretrazi)"), make_choice)],
                SET_VALUE: [MessageHandler(filters.TEXT, record_data)]
            },
            fallbacks = [CommandHandler("cancel", cancel)],
    )

    bot.add_handler(flow_handler)
    bot.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
