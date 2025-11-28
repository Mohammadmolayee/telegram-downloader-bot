import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from database import init_db, user_exists, create_user, login, get_user, set_language
from keyboards import guest_keyboard, member_keyboard, language_inline
from messages import t
from downloader import download_media

logging.basicConfig(level=logging.INFO)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)
    lang = user["language"] if user else "fa"

    if user:
        await update.message.reply_text(t("start_member", lang),
                                        reply_markup=member_keyboard(lang))
    else:
        await update.message.reply_text(t("start_guest", lang),
                                        reply_markup=guest_keyboard(lang))


async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    user = get_user(uid)
    lang = user["language"] if user else "fa"

    if text in ["🌐 زبان", "Language", "🌐 Language"]:
        await update.message.reply_text(t("choose_lang", lang),
                                        reply_markup=language_inline())
        return

    if text in ["👤 ساخت حساب", "Create Account"]:
        ok = create_user(uid, "User", f"user{uid}", "1234")
        if ok:
            await update.message.reply_text(t("account_created", lang),
                                            reply_markup=member_keyboard(lang))
        return

    if text.startswith("http"):
        await download_media(text, update, lang)
        return

    await update.message.reply_text("...")


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    uid = update.effective_user.id

    if data.startswith("lang_"):
        lang = data.split("_")[1]
        set_language(uid, lang)
        await update.callback_query.edit_message_text(t("lang_changed", lang))
        return


async def main():
    init_db()

    app = Application.builder().token("TOKEN").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_msg))
    app.add_handler(CallbackQueryHandler(callback))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("Bot is running...")


if __name__ == "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
