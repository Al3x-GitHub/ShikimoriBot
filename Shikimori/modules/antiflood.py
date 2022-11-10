import html
import re
from typing import Optional

from telegram import Chat, ChatPermissions, Message, Update, User
from telegram.error import BadRequest
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    run_async,
)
from telegram.utils.helpers import mention_html

from Shikimori import TIGERS, WOLVES, dispatcher
from Shikimori.modules.connection import connected
from Shikimori.modules.helper_funcs.alternate import send_message
from Shikimori.modules.helper_funcs.chat_status import (
    bot_admin,
    is_user_admin,
    user_admin,
    user_admin_no_reply,
)
from Shikimori.modules.helper_funcs.string_handling import extract_time
from Shikimori.modules.log_channel import loggable
from Shikimori.modules.sql import antiflood_sql as sql
from Shikimori.modules.sql.approve_sql import is_approved

FLOOD_GROUP = 3


@run_async
@loggable
def check_flood(update, context) -> str:
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]
    if not user:  # ignore channels
        return ""

    # ignore admins and whitelists
    if is_user_admin(chat, user.id) or user.id in WOLVES or user.id in TIGERS:
        sql.update_flood(chat.id, None)
        return ""
    # ignore approved users
    if is_approved(chat.id, user.id):
        sql.update_flood(chat.id, None)
        return
    should_ban = sql.update_flood(chat.id, user.id)
    if not should_ban:
        return ""

    try:
        getmode, getvalue = sql.get_flood_setting(chat.id)
        if getmode == 1:
            chat.kick_member(user.id)
            execstrings = "Banned"
            tag = "BANNED"
        elif getmode == 2:
            chat.kick_member(user.id)
            chat.unban_member(user.id)
            execstrings = "Kicked"
            tag = "KICKED"
        elif getmode == 3:
            context.bot.restrict_chat_member(
                chat.id, user.id, permissions=ChatPermissions(can_send_messages=False)
            )
            execstrings = "Muted"
            tag = "MUTED"
        elif getmode == 4:
            bantime = extract_time(msg, getvalue)
            chat.kick_member(user.id, until_date=bantime)
            execstrings = "Banned For {}".format(getvalue)
            tag = "TBAN"
        elif getmode == 5:
            mutetime = extract_time(msg, getvalue)
            context.bot.restrict_chat_member(
                chat.id,
                user.id,
                until_date=mutetime,
                permissions=ChatPermissions(can_send_messages=False),
            )
            execstrings = "Muted For {}".format(getvalue)
            tag = "TMUTE"
        send_message(
            update.effective_message, "Beep Boop! Boop Beep!\n{}!".format(execstrings)
        )

        return (
            "<b>{}:</b>"
            "\n#{}"
            "\n<b>User:</b> {}"
            "\nFlooded The Group.".format(
                tag,
                html.escape(chat.title),
                mention_html(user.id, html.escape(user.first_name)),
            )
        )

    except BadRequest:
        msg.reply_text(
            "I Can't Restrict People Here, Give Me Permissions First! Until Then, I'll Disable Anti-flood."
        )
        sql.set_flood(chat.id, 0)
        return (
            "<b>{}:</b>"
            "\n#Info"
            "\nDon't Have Enough Permission To Restrict Users So Automatically Disabled Anti-flood".format(
                chat.title
            )
        )


@run_async
@user_admin_no_reply
@bot_admin
def flood_button(update: Update, context: CallbackContext):
    bot = context.bot
    query = update.callback_query
    user = update.effective_user
    match = re.match(r"unmute_flooder\((.+?)\)", query.data)
    if match:
        user_id = match.group(1)
        chat = update.effective_chat.id
        try:
            bot.restrict_chat_member(
                chat,
                int(user_id),
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                ),
            )
            update.effective_message.edit_text(
                f"Unmuted By {mention_html(user.id, html.escape(user.first_name))}.",
                parse_mode="HTML",
            )
        except:
            pass


@run_async
@user_admin
@loggable
def set_flood(update, context) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    args = context.args

    conn = connected(context.bot, update, chat, user.id, need_admin=True)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(
                update.effective_message,
                "This Command Is Meant To Use In Group Not In PM",
            )
            return ""
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if len(args) >= 1:
        val = args[0].lower()
        if val in ["off", "no", "0"]:
            sql.set_flood(chat_id, 0)
            if conn:
                text = message.reply_text(
                    "Antiflood Has Been Disabled In {}.".format(chat_name)
                )
            else:
                text = message.reply_text("Antiflood Has Been Disabled.")

        elif val.isdigit():
            amount = int(val)
            if amount <= 0:
                sql.set_flood(chat_id, 0)
                if conn:
                    text = message.reply_text(
                        "Antiflood Has Been Disabled In {}.".format(chat_name)
                    )
                else:
                    text = message.reply_text("Antiflood Has Been Disabled.")
                return (
                    "<b>{}:</b>"
                    "\n#Setflood"
                    "\n<b>Admin:</b> {}"
                    "\nDisable Antiflood.".format(
                        html.escape(chat_name),
                        mention_html(user.id, html.escape(user.first_name)),
                    )
                )

            elif amount <= 3:
                send_message(
                    update.effective_message,
                    "Antiflood Must Be Either 0 (disabled) Or Number Greater Than 3!",
                )
                return ""

            else:
                sql.set_flood(chat_id, amount)
                if conn:
                    text = message.reply_text(
                        "Anti-flood Has Been Set To {} In Chat: {}".format(
                            amount, chat_name
                        )
                    )
                else:
                    text = message.reply_text(
                        "Successfully Updated Anti-flood Limit To {}!".format(amount)
                    )
                return (
                    "<b>{}:</b>"
                    "\n#Setflood"
                    "\n<b>Admin:</b> {}"
                    "\nSet Antiflood To <code>{}</code>.".format(
                        html.escape(chat_name),
                        mention_html(user.id, html.escape(user.first_name)),
                        amount,
                    )
                )

        else:
            message.reply_text("Invalid Argument Please Use A Number, 'off' or 'no'")
    else:
        message.reply_text(
            (
                "Use `/setflood number` To Enable Anti-flood.\nOr Use `/setflood off` To Disable Antiflood!."
            ),
            parse_mode="markdown",
        )
    return ""


@run_async
def flood(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message

    conn = connected(context.bot, update, chat, user.id, need_admin=False)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(
                update.effective_message,
                "This Command Is Meant To Use In Group Not In PM",
            )
            return
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        if conn:
            text = msg.reply_text(
                "I'm Not Enforcing Any Flood Control In {}!".format(chat_name)
            )
        else:
            text = msg.reply_text("I'm Not Enforcing Any Flood Control Here!")
    else:
        if conn:
            text = msg.reply_text(
                "I'm Currently Restricting Members After {} Consecutive Messages In {}.".format(
                    limit, chat_name
                )
            )
        else:
            text = msg.reply_text(
                "I'm Currently Restricting Members After {} Consecutive Messages.".format(
                    limit
                )
            )


@run_async
@user_admin
def set_flood_mode(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = context.args

    conn = connected(context.bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(
                update.effective_message,
                "This Command Is Meant To Use In Group Not In PM",
            )
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if args:
        if args[0].lower() == "ban":
            settypeflood = "ban"
            sql.set_flood_strength(chat_id, 1, "0")
        elif args[0].lower() == "kick":
            settypeflood = "kick"
            sql.set_flood_strength(chat_id, 2, "0")
        elif args[0].lower() == "mute":
            settypeflood = "mute"
            sql.set_flood_strength(chat_id, 3, "0")
        elif args[0].lower() == "tban":
            if len(args) == 1:
                teks = """It Looks Like You Tried To Set Time Value For Antiflood But You Didn't Specified Time; Try, `/setfloodmode tban <timevalue>`.
Examples Of Time Value: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks."""
                send_message(update.effective_message, teks, parse_mode="markdown")
                return
            settypeflood = "tban for {}".format(args[1])
            sql.set_flood_strength(chat_id, 4, str(args[1]))
        elif args[0].lower() == "tmute":
            if len(args) == 1:
                teks = (
                    update.effective_message,
                    """It looks like you tried to set time value for antiflood but you didn't specified time; Try, `/setfloodmode tmute <timevalue>`.
Examples of time value: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks.""",
                )
                send_message(update.effective_message, teks, parse_mode="markdown")
                return
            settypeflood = "tmute for {}".format(args[1])
            sql.set_flood_strength(chat_id, 5, str(args[1]))
        else:
            send_message(
                update.effective_message, "I Only Understand ban/kick/mute/tban/tmute!"
            )
            return
        if conn:
            text = msg.reply_text(
                "Exceeding Consecutive Flood Limit Will Result In {} In {}!".format(
                    settypeflood, chat_name
                )
            )
        else:
            text = msg.reply_text(
                "Exceeding Consecutive Flood Limit Will Result In {}!".format(
                    settypeflood
                )
            )
        return (
            "<b>{}:</b>\n"
            "<b>Admin:</b> {}\n"
            "Has Changed Antiflood Mode. User Will {}.".format(
                settypeflood,
                html.escape(chat.title),
                mention_html(user.id, html.escape(user.first_name)),
            )
        )
    else:
        getmode, getvalue = sql.get_flood_setting(chat.id)
        if getmode == 1:
            settypeflood = "ban"
        elif getmode == 2:
            settypeflood = "kick"
        elif getmode == 3:
            settypeflood = "mute"
        elif getmode == 4:
            settypeflood = "tban for {}".format(getvalue)
        elif getmode == 5:
            settypeflood = "tmute for {}".format(getvalue)
        if conn:
            text = msg.reply_text(
                "Sending More Messages Than Flood Limit Will Result In {} In {}.".format(
                    settypeflood, chat_name
                )
            )
        else:
            text = msg.reply_text(
                "Sending More Message Than Flood Limit Will Result In {}.".format(
                    settypeflood
                )
            )
    return ""


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        return "Not Enforcing To Flood Control."
    else:
        return "Antiflood Has Been Set To`{}`.".format(limit)


__help__ = """
𝗔𝗻𝘁𝗶-𝗙𝗹𝗼𝗼𝗱 allows you to take action on users that send more than x messages in a row. Exceeding the set flood \
will result in restricting that user.
 This will mute users if they send more than 10 messages in a row, bots are ignored.

 ❍ /flood*:* Get the current flood control setting
• *Admins only:*
 ❍ /setflood <int/'no'/'off'>*:* enables or disables flood control
 *Example:* `/setflood 10`
 ❍ /setfloodmode <ban/kick/mute/tban/tmute> <value>*:* Action to perform when user have exceeded flood limit. ban/kick/mute/tmute/tban
• *Note:*
 • Value must be filled for tban and tmute!!
 It can be:
 `5m` = 5 minutes
 `6h` = 6 hours
 `3d` = 3 days
 `1w` = 1 week

❏ 𝗣𝗼𝘄𝗲𝗿𝗲𝗱 𝗕𝘆
┗ @MaximXRobot
 """

__mod_name__ = "Aɴᴛɪ-Fʟᴏᴏᴅ"

FLOOD_BAN_HANDLER = MessageHandler(
    Filters.all & ~Filters.status_update & Filters.group, check_flood
)
SET_FLOOD_HANDLER = CommandHandler("setflood", set_flood, filters=Filters.group)
SET_FLOOD_MODE_HANDLER = CommandHandler(
    "setfloodmode", set_flood_mode, pass_args=True
)  # , filters=Filters.group)
FLOOD_QUERY_HANDLER = CallbackQueryHandler(flood_button, pattern=r"unmute_flooder")
FLOOD_HANDLER = CommandHandler("flood", flood, filters=Filters.group)

dispatcher.add_handler(FLOOD_BAN_HANDLER, FLOOD_GROUP)
dispatcher.add_handler(FLOOD_QUERY_HANDLER)
dispatcher.add_handler(SET_FLOOD_HANDLER)
dispatcher.add_handler(SET_FLOOD_MODE_HANDLER)
dispatcher.add_handler(FLOOD_HANDLER)

__handlers__ = [
    (FLOOD_BAN_HANDLER, FLOOD_GROUP),
    SET_FLOOD_HANDLER,
    FLOOD_HANDLER,
    SET_FLOOD_MODE_HANDLER,
]
