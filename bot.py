import os
import json
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters, ContextTypes
)
from storage import PortfolioStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation states
(MAIN_MENU, ADD_PROJECT_NAME, ADD_PROJECT_DESC, ADD_PROJECT_SKILLS,
 ADD_PROJECT_LINKS, ADD_PROJECT_PHOTO, ADD_SKILL, EDIT_SELECT,
 EDIT_FIELD, VIEW_PROJECT) = range(10)

storage = PortfolioStorage()


# ─── Keyboards ────────────────────────────────────────────────────────────────

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Добавить проект", callback_data="add_project")],
        [InlineKeyboardButton("📂 Мои проекты", callback_data="list_projects"),
         InlineKeyboardButton("🛠 Навыки", callback_data="list_skills")],
        [InlineKeyboardButton("🔗 Поделиться портфолио", callback_data="share")],
        [InlineKeyboardButton("➕ Добавить навык", callback_data="add_skill")],
    ])


def skip_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⏭ Пропустить", callback_data="skip")]])


def cancel_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="cancel")]])


def project_keyboard(project_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_{project_id}"),
         InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{project_id}")],
        [InlineKeyboardButton("◀️ Назад", callback_data="list_projects")],
    ])


def edit_field_keyboard(project_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Название", callback_data=f"editfield_name_{project_id}"),
         InlineKeyboardButton("📄 Описание", callback_data=f"editfield_desc_{project_id}")],
        [InlineKeyboardButton("🛠 Навыки", callback_data=f"editfield_skills_{project_id}"),
         InlineKeyboardButton("🔗 Ссылки", callback_data=f"editfield_links_{project_id}")],
        [InlineKeyboardButton("🖼 Фото", callback_data=f"editfield_photo_{project_id}")],
        [InlineKeyboardButton("◀️ Назад", callback_data=f"view_{project_id}")],
    ])


# ─── Helpers ──────────────────────────────────────────────────────────────────

def format_project(p, index=None):
    prefix = f"*{index}. " if index else "*"
    skills = ", ".join(p.get("skills", [])) or "—"
    links = "\n".join(p.get("links", [])) or "—"
    date = p.get("date", "")
    text = (
        f"{prefix}{p['name']}*\n\n"
        f"📄 {p.get('description', '—')}\n\n"
        f"🛠 Навыки: `{skills}`\n"
        f"🔗 Ссылки:\n{links}\n"
        f"📅 Добавлен: {date}"
    )
    return text


# ─── Handlers ─────────────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Привет, *{user.first_name}*!\n\n"
        f"Это твой личный бот-портфолио. Здесь можно хранить проекты, навыки и ссылки — и делиться ими одной кнопкой.\n\n"
        f"Выбери действие:",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )
    return MAIN_MENU


async def menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📋 *Главное меню*\n\nВыбери действие:",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )
    return MAIN_MENU


# ── ADD PROJECT ──

async def add_project_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ctx.user_data["new_project"] = {}
    await query.edit_message_text(
        "➕ *Новый проект*\n\n✏️ Введи название проекта:",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard()
    )
    return ADD_PROJECT_NAME


async def add_project_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["new_project"]["name"] = update.message.text.strip()
    await update.message.reply_text(
        "📄 Теперь напиши описание проекта:",
        reply_markup=skip_keyboard()
    )
    return ADD_PROJECT_DESC


async def add_project_desc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        ctx.user_data["new_project"]["description"] = ""
        msg = update.callback_query.message
        await msg.reply_text("🛠 Укажи навыки/технологии через запятую (напр: Python, React, SQL):", reply_markup=skip_keyboard())
    else:
        ctx.user_data["new_project"]["description"] = update.message.text.strip()
        await update.message.reply_text("🛠 Укажи навыки/технологии через запятую (напр: Python, React, SQL):", reply_markup=skip_keyboard())
    return ADD_PROJECT_SKILLS


async def add_project_skills(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        ctx.user_data["new_project"]["skills"] = []
        msg = update.callback_query.message
        await msg.reply_text("🔗 Добавь ссылки (каждая с новой строки — GitHub, demo и т.д.):", reply_markup=skip_keyboard())
    else:
        raw = update.message.text.strip()
        ctx.user_data["new_project"]["skills"] = [s.strip() for s in raw.split(",") if s.strip()]
        await update.message.reply_text("🔗 Добавь ссылки (каждая с новой строки — GitHub, demo и т.д.):", reply_markup=skip_keyboard())
    return ADD_PROJECT_LINKS


async def add_project_links(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        ctx.user_data["new_project"]["links"] = []
        msg = update.callback_query.message
        await msg.reply_text("🖼 Отправь фото/скриншот проекта:", reply_markup=skip_keyboard())
    else:
        raw = update.message.text.strip()
        ctx.user_data["new_project"]["links"] = [l.strip() for l in raw.splitlines() if l.strip()]
        await update.message.reply_text("🖼 Отправь фото/скриншот проекта:", reply_markup=skip_keyboard())
    return ADD_PROJECT_PHOTO


async def add_project_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    project = ctx.user_data["new_project"]
    project["date"] = datetime.now().strftime("%d.%m.%Y")

    if update.callback_query:
        await update.callback_query.answer()
        project["photo_id"] = None
    elif update.message.photo:
        project["photo_id"] = update.message.photo[-1].file_id
    else:
        project["photo_id"] = None

    user_id = str(update.effective_user.id)
    storage.add_project(user_id, project)

    text = f"✅ *Проект сохранён!*\n\n{format_project(project)}"
    kb = main_menu_keyboard()

    if update.callback_query:
        await update.callback_query.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)
    return MAIN_MENU


# ── LIST PROJECTS ──

async def list_projects(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    projects = storage.get_projects(user_id)

    if not projects:
        await query.edit_message_text(
            "📂 У тебя пока нет проектов.\n\nДобавь первый!",
            reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    buttons = []
    for i, p in enumerate(projects):
        buttons.append([InlineKeyboardButton(f"📁 {p['name']}", callback_data=f"view_{p['id']}")])
    buttons.append([InlineKeyboardButton("◀️ Меню", callback_data="menu")])

    await query.edit_message_text(
        f"📂 *Твои проекты* ({len(projects)} шт):",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return MAIN_MENU


async def view_project(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    project_id = query.data.replace("view_", "")
    user_id = str(update.effective_user.id)
    project = storage.get_project(user_id, project_id)

    if not project:
        await query.edit_message_text("❌ Проект не найден.", reply_markup=main_menu_keyboard())
        return MAIN_MENU

    text = format_project(project)
    kb = project_keyboard(project_id)

    if project.get("photo_id"):
        await query.message.reply_photo(
            photo=project["photo_id"],
            caption=text,
            parse_mode="Markdown",
            reply_markup=kb
        )
        await query.message.delete()
    else:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    return MAIN_MENU


async def delete_project(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    project_id = query.data.replace("delete_", "")
    user_id = str(update.effective_user.id)
    storage.delete_project(user_id, project_id)
    await query.edit_message_text("🗑 Проект удалён.", reply_markup=main_menu_keyboard())
    return MAIN_MENU


# ── EDIT PROJECT ──

async def edit_project(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    project_id = query.data.replace("edit_", "")
    await query.edit_message_text(
        "✏️ *Что редактируем?*",
        parse_mode="Markdown",
        reply_markup=edit_field_keyboard(project_id)
    )
    return EDIT_FIELD


async def edit_field_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, field, project_id = query.data.split("_", 2)
    ctx.user_data["edit_project_id"] = project_id
    ctx.user_data["edit_field"] = field

    prompts = {
        "name": "✏️ Введи новое название:",
        "desc": "📄 Введи новое описание:",
        "skills": "🛠 Введи навыки через запятую:",
        "links": "🔗 Введи ссылки (каждая с новой строки):",
        "photo": "🖼 Отправь новое фото:",
    }
    await query.edit_message_text(prompts[field], reply_markup=cancel_keyboard())
    return EDIT_SELECT


async def edit_field_save(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    field = ctx.user_data.get("edit_field")
    project_id = ctx.user_data.get("edit_project_id")
    user_id = str(update.effective_user.id)

    if field == "photo" and update.message.photo:
        value = update.message.photo[-1].file_id
    elif field == "skills":
        value = [s.strip() for s in update.message.text.split(",") if s.strip()]
    elif field == "links":
        value = [l.strip() for l in update.message.text.splitlines() if l.strip()]
    else:
        value = update.message.text.strip()

    field_map = {"name": "name", "desc": "description", "skills": "skills", "links": "links", "photo": "photo_id"}
    storage.update_project(user_id, project_id, {field_map[field]: value})

    await update.message.reply_text("✅ Обновлено!", reply_markup=main_menu_keyboard())
    return MAIN_MENU


# ── SKILLS ──

async def list_skills(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    skills = storage.get_skills(user_id)

    if not skills:
        text = "🛠 Навыки не добавлены."
    else:
        text = "🛠 *Твои навыки:*\n\n" + " • ".join(skills)

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())
    return MAIN_MENU


async def add_skill_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🛠 Введи навыки через запятую (напр: Docker, PostgreSQL, Figma):",
        reply_markup=cancel_keyboard()
    )
    return ADD_SKILL


async def add_skill_save(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    raw = update.message.text.strip()
    new_skills = [s.strip() for s in raw.split(",") if s.strip()]
    storage.add_skills(user_id, new_skills)
    await update.message.reply_text(
        f"✅ Добавлено навыков: {len(new_skills)}",
        reply_markup=main_menu_keyboard()
    )
    return MAIN_MENU


# ── SHARE ──

async def share_portfolio(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    projects = storage.get_projects(user_id)
    skills = storage.get_skills(user_id)

    if not projects and not skills:
        await query.edit_message_text(
            "📭 Портфолио пустое. Сначала добавь проекты или навыки!",
            reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    lines = ["🗂 *Моё портфолио*\n"]
    if skills:
        lines.append(f"🛠 *Навыки:* {', '.join(skills)}\n")
    if projects:
        lines.append(f"📂 *Проекты ({len(projects)}):*")
        for i, p in enumerate(projects, 1):
            lines.append(f"\n*{i}. {p['name']}*")
            if p.get("description"):
                lines.append(f"   {p['description']}")
            if p.get("skills"):
                lines.append(f"   🛠 {', '.join(p['skills'])}")
            if p.get("links"):
                for link in p["links"]:
                    lines.append(f"   🔗 {link}")

    text = "\n".join(lines)
    await query.edit_message_text(
        f"{text}\n\n💡 _Скопируй и отправь этот текст куда нужно!_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Меню", callback_data="menu")]])
    )
    return MAIN_MENU


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("❌ Отменено.", reply_markup=main_menu_keyboard())
    else:
        await update.message.reply_text("❌ Отменено.", reply_markup=main_menu_keyboard())
    return MAIN_MENU


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN env variable not set!")

    app = Application.builder().token(token).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(add_project_start, pattern="^add_project$"),
                CallbackQueryHandler(list_projects, pattern="^list_projects$"),
                CallbackQueryHandler(view_project, pattern="^view_"),
                CallbackQueryHandler(delete_project, pattern="^delete_"),
                CallbackQueryHandler(edit_project, pattern="^edit_[^f]"),
                CallbackQueryHandler(list_skills, pattern="^list_skills$"),
                CallbackQueryHandler(add_skill_start, pattern="^add_skill$"),
                CallbackQueryHandler(share_portfolio, pattern="^share$"),
                CallbackQueryHandler(menu, pattern="^menu$"),
            ],
            ADD_PROJECT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_project_name),
                CallbackQueryHandler(cancel, pattern="^cancel$"),
            ],
            ADD_PROJECT_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_project_desc),
                CallbackQueryHandler(add_project_desc, pattern="^skip$"),
                CallbackQueryHandler(cancel, pattern="^cancel$"),
            ],
            ADD_PROJECT_SKILLS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_project_skills),
                CallbackQueryHandler(add_project_skills, pattern="^skip$"),
                CallbackQueryHandler(cancel, pattern="^cancel$"),
            ],
            ADD_PROJECT_LINKS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_project_links),
                CallbackQueryHandler(add_project_links, pattern="^skip$"),
                CallbackQueryHandler(cancel, pattern="^cancel$"),
            ],
            ADD_PROJECT_PHOTO: [
                MessageHandler(filters.PHOTO, add_project_photo),
                CallbackQueryHandler(add_project_photo, pattern="^skip$"),
                CallbackQueryHandler(cancel, pattern="^cancel$"),
            ],
            ADD_SKILL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_skill_save),
                CallbackQueryHandler(cancel, pattern="^cancel$"),
            ],
            EDIT_FIELD: [
                CallbackQueryHandler(edit_field_start, pattern="^editfield_"),
                CallbackQueryHandler(view_project, pattern="^view_"),
            ],
            EDIT_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_field_save),
                MessageHandler(filters.PHOTO, edit_field_save),
                CallbackQueryHandler(cancel, pattern="^cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CallbackQueryHandler(cancel, pattern="^cancel$"),
        ],
    )

    app.add_handler(conv)
    logger.info("Bot started!")
    app.run_polling()


if __name__ == "__main__":
    main()
