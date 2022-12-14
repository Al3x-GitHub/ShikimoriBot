from telegram import Update
from telegram.ext import CallbackContext, CommandHandler
from TruthDarePy import TD

from Shikimori import dispatcher

love = TD()


def truth(update: Update, context: CallbackContext):
    message = update.effective_message
    message.reply_text(love.truth(lang="en"))


def dare(update: Update, context: CallbackContext):
    message = update.effective_message
    message.reply_text(love.dare(lang="en"))


TRUTH_HANDLER = CommandHandler("truth", truth)
DARE_HANDLER = CommandHandler("dare", dare)

dispatcher.add_handler(TRUTH_HANDLER)
dispatcher.add_handler(DARE_HANDLER)

__help__ = """
*Truth & Dare*
 β /truth *:* Sends a random truth string.
 β /dare *:* Sends a random dare string.
 
β π£πΌππ²πΏπ²π± ππ
β @MaximXRobot
"""
__mod_name__ = "TΚα΄α΄Κ-Dα΄Κα΄"
