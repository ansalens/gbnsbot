"""Logic behind the telegram bot.

Constants
---------
    TOKEN - Your telegram bot token, loaded from .env.
    REMIND_DURATION - Number of seconds to wait before checking again on the book.
    CHOOSE, SET_VALUE - Integer numbers that signal the state of conversation with the bot.
    indexed - Some basic information about libraries (name, address, work hours).
    searching - Used for storing info about the book that user wants to be reminded of.
"""
import logging
from os import getenv
from telegram.ext import (ApplicationBuilder, filters,
                          CommandHandler, ConversationHandler, MessageHandler)
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from dotenv import load_dotenv
import lib_scraper

indexed = {"1": ("Danilo Kis", "Narodnog Fronta 47", "Pon-Pet 07:30-20:00"),
           "2": ("Djura Danicic", "Dunavska 1", "Pon-Pet 07:30-20:00"),
           "3": ("Petefi Sandor", "Jozefa Atile 16", "Pon-Pet 07:30-20:00")
          }
CHOOSE, SET_VALUE = range(2)
REMIND_DURATION = 1800
searching = {}
load_dotenv()
TOKEN = getenv("BOT_TOKEN")

logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.DEBUG)

async def show_options(update, _):
    """Show options to the user for populating info and for initializing search.
    
    This function gets called each time `/start` is typed, and also each time
    after the user has filled one of information (title, author or library).
    It displays button options for the user to pick from.

    Arguments
    ---------
        update - For sending options in the message to the user.
        _ (context) - Not used in this case.

    Returns
    -------
        CHOOSE - State in which user is supposed to pick an option.
    """
    options = [["Naslov", "Autor", "Biblioteke", "Pretrazi"]]
    markup_options = ReplyKeyboardMarkup(options, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Izaberi opciju za podesavanje ili pokreni pretragu ⬇️", reply_markup=markup_options)
    return CHOOSE


async def make_choice(update, context):
    """Save user choice and prompt the user to enter data or start the search.
    
    Save user choice in `user_data` for further use, and depending on that
    choice prompt the user to enter information.
    If the choice was `biblioteke`, display button options for picking the library.
    If the choice was `pretrazi`, begin the actual search. It doesn't perform
    the search if the user hasn't yet filled in title or library.
    
    Arguments
    ---------
        update - Used for sending the message to the user.
        context - Used for saving data in `user_data` dictionary.

    Returns
    -------
        SET_VALUE - State in which data is saved for future search.
        CHOOSE - State in which user is supposed to pick an option.
    """
    user_data = context.user_data
    text = update.message.text.lower()
    user_data["choice"] = text

    if text == "autor":
        await update.message.reply_text("Unesi ime autora.")
    elif text == "naslov":
        await update.message.reply_text("Unesi naslov knjige.")
    elif text == "biblioteke":
        library = [["1", "2", "3"]]
        markup = ReplyKeyboardMarkup(library, resize_keyboard=True, one_time_keyboard=True)        
        msg = "Biblioteke u ponudi\n"
        for index, lib in indexed.items():
            msg += f"{index}) {lib[0]}\n▫ {lib[1]}\n▫ {lib[2]}\n"

        await update.message.reply_text(msg, reply_markup=markup)
    elif text == "pretrazi":
        if user_data.get("naslov") and user_data.get("biblioteke"):
            return await search(update, context)
        
        await update.message.reply_text("Potrebno uneti ime knjige i izabrati biblioteku ⚠")
        return CHOOSE
        
    return SET_VALUE


async def record_data(update, context):
    """Save user supplied data and show options again.
    
    User data will be saved in `user_data`. Because this function is called
    whenever user sends the bot any text, `choice` key is necessary for
    figuring out what option user has picked and saving data for that option.
    
    Arguments
    ---------
        update - For receiving user textual message
        context - For saving that message in `user_data`
    
    Returns
    -------
        CHOOSE - Returned from show_options function.
    """
    user_data = context.user_data
    if not user_data.get("choice"):
        return await show_options(update, context)
    
    text = update.message.text
    if text.lower() in ("/cancel", "cancel"):
        return await cancel(update, context)

    data = user_data["choice"]
    user_data[data] = text
    del user_data["choice"]
    
    return await show_options(update, context)


async def search(update, context):
    """Perform the search for a book in selected library.

    Book's title and user selected library is mandatory for the search to be run.
    Author's name is optional, but can help narrow down the search to correct book.
    Function `telegram_search` does the heavy lifting, and returns non-empty string
    if the book is available. According to that, message is sent to the user.
    `available` flag is used later in `callback_reminder` function.
    
    Arguments
    ---------
        update - Used for sending a message to the user.
        context - Used for accessing `user_data`.

    Returns
    -------
        ConversationHandler.END - State in which conversation is over.
    """
    user_data = context.user_data
    title = user_data["naslov"]
    selected_lib = user_data["biblioteke"]
    library_name = indexed[selected_lib][0]
    library = lib_scraper.libraries[library_name]
    msg = f"Pretrazujem 🔎\n🔸 {title} 📕\n🔸 {library_name} 🏫"

    author = ""
    if user_data.get("autor"):
        author = user_data["autor"]
        msg += f"\n🔸 {author} ✒"

    await update.message.reply_text(msg)
    results = lib_scraper.telegram_search(title, author, library)
    user_data["available"] = False

    if results:
        await update.message.reply_text(results, reply_markup=ReplyKeyboardRemove())
        user_data["available"] = True
    else:
        await update.message.reply_text(f"{title} | {library_name} - NEDOSTUPNA")

    if user_data.get("autor"):
        del user_data["autor"]

    return ConversationHandler.END


async def reminder(context):
    """Send message when a book becomes available and remove the job from background queue.
    
    Arguments
    ---------
        context - For job queue and sending a message to the user.
    """
    user_data = context.job.data
    lib = user_data["biblioteke"]
    library_name = indexed[lib][0]
    library = lib_scraper.libraries[library_name]
    title = user_data["naslov"]
    author = ""
    
    if user_data.get("autor"):
        author = user_data["autor"]
    
    results = lib_scraper.telegram_search(title, author, library)

    if results:
        user_data["available"] = True
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
    """Start search job in the background or inform the user.
    
    Actual `reminder` function gets only called if the book is already borrowed.
    If that's the case, every REMIND_DURATION seconds, `reminder` will be called,
    passing it data about the book to search for. Otherwise, if a book is already
    available or the user hasn't supplied enough information, it will send
    appropriate message to the user.
    
    Arguments
    ---------
        update - For sending a message to the user and passing user's chat id.
        context - For running job queue and copying user's data into `searching`.

    """
    global searching
    searching = context.user_data.copy()
    chat_id = update.effective_message.chat_id
    title = searching.get("naslov")
    lib = searching.get("biblioteke")
    
    if not title or not lib:
        await update.message.reply_text("Potrebno uneti ime knjige i izabrati biblioteku ⚠")
    elif not searching.get("available"):
        context.job_queue.run_repeating(reminder, interval=REMIND_DURATION, chat_id=chat_id, data=searching)
        await update.message.reply_text(f"Proveravam ponovo svakih {int(REMIND_DURATION / 60)} minuta.")
    else:
        await update.message.reply_text(f"Knjiga \"{title}\" je vec dostupna u biblioteci {indexed[lib][0]}.")


async def cancel(update, _):
    """Cancel the search and send informational message to the user."""
    await update.message.reply_text("Pretraga zaustavljena ⚠", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main():
    """Connect with bot API, define conversation handler and command handler and run the bot.
    
    As long as the bot is running and communicating with the user, it will be
    either in conversation state (filling the information) or searching the book.
    User sets an automated reminder with `/remind`, but in a nutshell it just uses
    `telegram_search` to search the library every REMIND_DURATION seconds.
    At any point user can `/cancel` and end the conversation without searching.
    
    Raises
    ------
        SystemExit - If token is missing from .env file
    """
    if not TOKEN:
        raise SystemExit('BOT_TOKEN entry not found in .env file!')
    bot = ApplicationBuilder().token(TOKEN).build()
    flow_handler = ConversationHandler(
            entry_points=[CommandHandler("start", show_options)],
            states = {
                CHOOSE: [MessageHandler(filters.Regex("^(Naslov|Autor|Biblioteke|Pretrazi)"), make_choice)],
                SET_VALUE: [MessageHandler(filters.TEXT, record_data)]
            },
            fallbacks = [CommandHandler("cancel", cancel)],
    )
    bot.add_handler(flow_handler)
    bot.add_handler(CommandHandler("remind", callback_reminder))
    bot.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
