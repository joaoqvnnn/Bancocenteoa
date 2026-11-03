from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes, ConversationHandler

# Vamos usar estados para o ConversationHandler
(ONBOARDING, ASK_BANK, ASK_CARD) = range(3)

# Aqui você coloca os links das imagens que você me mandou (hospede no Imgur ou no próprio GitHub)
# Exemplo de como deve ser a estrutura:
PASSOS = [
    {
        "image": "https://i.imgur.com/SEU_LINK_AQUI.png", # Imagem 1
        "text": "Olá {name}! Boa noite.\n\nEm poucos passos seu dinheiro vai estar organizado como nunca."
    },
    {
        "image": "https://i.imgur.com/SEU_LINK_AQUI.png", # Imagem 2
        "text": "Aqui você pode acompanhar seus gastos por categoria e ver para onde seu dinheiro está indo."
    },
    {
        "image": "https://i.imgur.com/SEU_LINK_AQUI.png", # Imagem 3
        "text": "Defina metas e limites para realizar seus sonhos sem sair do orçamento."
    }
]

def get_onboarding_keyboard(step: int, total: int):
    keyboard = []
    row = []
    if step > 0:
        row.append(InlineKeyboardButton("◀️ Anterior", callback_data=f"prev_{step}"))
    if step < total - 1:
        row.append(InlineKeyboardButton("Próximo ▶️", callback_data=f"next_{step}"))
    
    keyboard.append(row)
    keyboard.append([InlineKeyboardButton("Pular introdução ⏭️", callback_data="skip_onboarding")])
    return InlineKeyboardMarkup(keyboard)

async def start_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Pega a hora para dizer Bom dia/Boa tarde/Boa noite
    hora = 19 # Aqui você usaria datetime.now().hour para pegar a hora real
    saudacao = "Boa noite" if hora >= 18 else "Bom dia" if hora < 12 else "Boa tarde"
    
    context.user_data['name'] = user.first_name
    
    text = PASSOS[0]["text"].format(name=user.first_name)
    text = text.replace("Boa noite", saudacao) # Substitui a saudação
    
    await update.message.reply_photo(
        photo=PASSOS[0]["image"],
        caption=text,
        reply_markup=get_onboarding_keyboard(0, len(PASSOS))
    )
    return ONBOARDING

async def handle_onboarding_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "skip_onboarding":
        await query.edit_message_caption(
            caption="Tudo bem! Vamos direto ao que importa.\n\nQual banco você usa?",
            reply_markup=get_banks_keyboard()
        )
        return ASK_BANK
    
    action, step_str = data.split("_")
    step = int(step_str)
    
    if action == "next":
        new_step = step + 1
    elif action == "prev":
        new_step = step - 1
    else:
        return ONBOARDING

    # Atualiza o texto e a imagem NA MESMA MENSAGEM
    text = PASSOS[new_step]["text"].format(name=context.user_data.get('name', 'Usuário'))
    # Aqui você pode adicionar a lógica de saudação novamente se quiser
    
    media = InputMediaPhoto(
        media=PASSOS[new_step]["image"],
        caption=text
    )
    
    await query.edit_message_media(
        media=media,
        reply_markup=get_onboarding_keyboard(new_step, len(PASSOS))
    )
    return ONBOARDING
