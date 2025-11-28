# bot.py
import asyncio
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

from translator import tr
from messages import msg
from database import (
    init_db, user_exists, create_user,
    login, get_user, set_language
)
from keyboards import (
    start_guest_kb, member_panel_kb, language_inline,
    capabilities_kb, back_btn
)
from downloader import download_media


user_state = {}
temp = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if not user_exists(uid):
        lang = "fa"
        await update.message.reply_text(tr(msg("start_guest"), lang),
                                        reply_markup=start_guest_kb(lang))
    else:
        user = get_user(uid)
        lang = user["language"]
        await update.message.reply_text(tr(msg("start_member"), lang),
                                        reply_markup=member_panel_kb(lang))


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = update.message.text

    user = get_user(uid)
    lang = "fa" if not user else user["language"]

    # دکمه برگشت
    if txt == tr("🔙 برگشت", lang):
        if not user:
            await update.message.reply_text(tr(msg("start_guest"), lang),
                                            reply_markup=start_guest_kb(lang))
        else:
            await update.message.reply_text(tr(msg("start_member"), lang),
                                            reply_markup=member_panel_kb(lang))
        return

    # دکمه‌ها
    if txt == tr("📖 راهنما", lang):
        key = "help_guest" if not user else "help_member"
        await update.message.reply_text(tr(msg(key), lang), reply_markup=back_btn(lang))
        return

    if txt == tr("📜 قوانین", lang):
        await update.message.reply_text(tr(msg("rules"), lang), reply_markup=back_btn(lang))
        return

    if txt == tr("ℹ درباره ما", lang):
        await update.message.reply_text(tr(msg("about"), lang), reply_markup=back_btn(lang))
        return

    if txt == tr("🌐 زبان", lang):
        await update.message.reply_text(tr(msg("choose_language"), lang),
                                        reply_markup=language_inline())
        return

    if txt == tr("📥 قابلیت‌ها", lang):
        await update.message.reply_text(tr("لیست قابلیت‌ها:", lang),
                                        reply_markup=capabilities_kb(lang))
        return

    if txt == tr("👤 ساخت حساب", lang):
        user_state[uid] = "name"
        await update.message.reply_text(tr(msg("ask_name"), lang),
                                        reply_markup=back_btn(lang))
        return

    # مراحل ثبت‌نام
    if user_state.get(uid) == "name":
        temp[uid] = {"name": txt}
        user_state[uid] = "username"
        await update.message.reply_text(tr(msg("ask_username"), lang))
        return

    if user_state.get(uid) == "username":
        temp[uid]["username"] = txt
        user_state[uid] = "password"
        await update.message.reply_text(tr(msg("ask_password"), lang))
        return

    if user_state.get(uid) == "password":
        info = temp[uid]
        ok = create_user(uid, info["name"], info["username"], txt)
        if ok:
            user_state.pop(uid)
            temp.pop(uid)
            await update.message.reply_text(tr(msg("reg_done"), lang),
                                            reply_markup=member_panel_kb(lang))
        else:
            await update.message.reply_text(tr(msg("reg_fail"), lang))
        return

    # دانلود
    if txt.startswith("http"):
        if not user:
            await update.message.reply_text(tr(msg("guest_block"), lang))
            return
        
        await update.message.reply_text(tr(msg("downloading"), lang))
        await download_media(txt, context.bot, uid, lang)
        return

    await update.message.reply_text(tr(msg("unknown"), lang))

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    uid = update.effective_user.id

    if data.startswith("lang_"):
        lang = data.split("_")[1]
        set_language(uid, lang)
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(tr(msg("lang_changed"), lang))

        await update.callback_query.message.reply_text(
            tr(msg("start_member") if user_exists(uid) else msg("start_guest"), lang),
            reply_markup=member_panel_kb(lang) if user_exists(uid) else start_guest_kb(lang)
        )


async def main():
    db.init_db()
    token = os.getenv("TOKEN") or os.getenv("BOT_TOKEN")
    if not token:
        logger.error("TOKEN env var missing")
        return
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot starting...")
    app.run_polling()
    logger.info("Bot stopped.")

if __name__ == "__main__":
    main()
