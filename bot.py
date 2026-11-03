import os
import logging
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes, ConversationHandler, MessageHandler, filters
)
from database import init_db, User, get_session
from onboarding import start_onboarding, handle_onboarding_buttons, ONBOARDING, ASK_BANK
from sqlalchemy import select

# Configuração de logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 8080))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL") # O Render preenche isso automaticamente

def get_banks_keyboard():
    # Aqui você pode listar os bancos principais e um botão de "Outros"
    keyboard = [
        [InlineKeyboardButton("Nubank", callback_data="bank_nubank"), InlineKeyboardButton("Itaú", callback_data="bank_itau")],
        [InlineKeyboardButton("Bradesco", callback_data="bank_bradesco"), InlineKeyboardButton("C6 Bank", callback_data="bank_c6")],
        [InlineKeyboardButton("🔍 Outro Banco", callback_data="bank_outro")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Verifica no banco se o usuário já existe
    async for session in get_session():
        result = await session.execute(select(User).where(User.id == user_id))
        db_user = result.scalar_one_or_none()
        
        if db_user and db_user.onboarding_step > 0:
            # Usuário antigo, manda pro menu principal
            await update.message.reply_text("Bem-vindo de volta! O que deseja fazer hoje?")
            # Aqui vai chamar o menu principal depois
            return ConversationHandler.END
        else:
            # Usuário novo, cria no banco e inicia onboarding
            if not db_user:
                new_user = User(id=user_id, name=update.effective_user.first_name)
                session.add(new_user)
                await session.commit()
            
            return await start_onboarding(update, context)

async def webhook(application: Application):
    await application.bot.set_webhook(url=f"{RENDER_EXTERNAL_URL}/{TOKEN}")

async def main():
    # Inicializa o banco de dados
    await init_db()
    
    # Cria a aplicação do bot
    application = Application.builder().token(TOKEN).build()
    
    # Configura o ConversationHandler para o Onboarding
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ONBOARDING: [
                CallbackQueryHandler(handle_onboarding_buttons, pattern="^(next_|prev_|skip_)")
            ],
            ASK_BANK: [
                # Aqui você tratará a resposta do usuário sobre o banco
            ]
        },
        fallbacks=[CommandHandler("cancelar", start)]
    )
    
    application.add_handler(conv_handler)
    
    # Configura Webhook para o Render
    if RENDER_EXTERNAL_URL:
        # Usa aiohttp para criar um mini servidor web que o Render exige
        app = web.Application()
        
        async def handle_webhook(request):
            data = await request.json()
            update = Update.de_json(data, application.bot)
            await application.update_queue.put(update)
            return web.Response(text="OK")
        
        app.router.add_post(f"/{TOKEN}", handle_webhook)
        
        # Inicia o servidor web e o bot juntos
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()
        
        await webhook(application)
        logging.info(f"Bot rodando via Webhook na porta {PORT}")
        
        await application.initialize()
        await application.start()
        await application.updater.start_polling() # Mantém a fila rodando
    else:
        # Para testes locais (Polling)
        logging.info("Bot rodando localmente via Polling")
        await application.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
