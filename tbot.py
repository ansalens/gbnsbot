import logging
from os import getenv
from telegram.ext import (ApplicationBuilder, filters,
                          CommandHandler, ConversationHandler, MessageHandler)
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from dotenv import load_dotenv
import lib_scraper

# from random import randint

logging.basicConfig(
    filename='bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

load_dotenv()
TOKEN = getenv('BOT_TOKEN')
REMIND_DURATION = 1800
CHOOSE, SET_VALUE = range(2)
indexed = {'1': ('Danilo Kis', 'Narodnog Fronta 47', 'Pon-Pet 07:30-20:00'),
           '2': ('Djura Danicic', 'Dunavska 1', 'Pon-Pet 07:30-20:00\nSub 08:00-14:00')}
searching = {}


async def show_options(update, _):
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
        await update.message.reply_text("Unesi ime autora.")
    elif text == 'naslov':
        await update.message.reply_text("Unesi naslov knjige.")
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
    if text == '/cancel':
        return await cancel(update, context)

    data = user_data['choice']
    user_data[data] = text
    del user_data['choice']
    
    return await show_options(update, context)


async def search(update, context):
    user_data = context.user_data
    title = user_data['naslov']
    lib_number = user_data['biblioteka']
    library_name = indexed[lib_number][0]
    library = lib_scraper.libraries[library_name]
    msg = f"Pretrazujem 🔎\n🔸 {title} 📕\n🔸 {library_name} 🏫"

    author = ''
    if user_data.get('autor'):
        author = user_data['autor']
        msg += f"\n🔸 {author} ✒"

    await update.message.reply_text(msg)
    results = lib_scraper.telegram_search(title, author, library)
    user_data['available'] = False

    if results:
        await update.message.reply_text(results, reply_markup=ReplyKeyboardRemove())
        user_data['available'] = True
    else:
        await update.message.reply_text(f"{title} | {library_name} - NEDOSTUPNA")

    #user_data.clear()
    
    return ConversationHandler.END


async def reminder(context):
    user_data = context.job.data
    lib = user_data['biblioteka']
    library_name = indexed[lib][0]
    library = lib_scraper.libraries[library_name]
    title = user_data['naslov']
    author = ''
    
    if user_data.get('autor'):
        author = user_data['autor']
    
    results = lib_scraper.telegram_search(title, author, library)

    if results:
        user_data['available'] = True
        context.job.schedule_removal()
        msg = f"{title} 📕\n{library_name} 🏫\n{results}"
        await context.bot.send_message(context.job.chat_id, msg)

    """
    randomly = randint(0, 1)
    if randomly > 0:
        user_data['available'] = True
        context.job.schedule_removal()
        msg = f"{title} | {library_name} - DOSTUPNA!"
        await context.bot.send_message(context.job.chat_id, msg)
    """


async def callback_reminder(update, context):
    global searching
    searching = context.user_data.copy()
    chat_id = update.effective_message.chat_id
    title = searching.get('naslov')
    lib = searching.get('biblioteka')
    
    if not title or not lib:
        await update.message.reply_text("Potrebno uneti ime knjige i izabrati biblioteku ⚠")
    elif not searching.get('available'):
        context.job_queue.run_repeating(reminder, interval=REMIND_DURATION, chat_id=chat_id, data=searching)
        await update.message.reply_text(f"Proveravam ponovo svakih {int(REMIND_DURATION / 60)} minuta.")
    else:
        await update.message.reply_text(f"Knjiga \"{title}\" je vec dostupna u biblioteci {indexed[lib][0]}.")


async def cancel(update, _):
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
    bot.add_handler(CommandHandler('remind', callback_reminder))
    bot.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
