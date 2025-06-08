import logging
import dill
import pandas as pd
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Maydonlar va variantlar
FIELDS = {
    "SeniorCitizen": [0, 1],  # int, max 1 bit, lekin manual kiritamiz
    "Partner": ["Yes", "No"],
    "Dependents": ["Yes", "No"],
    "PhoneService": ["Yes", "No"],
    "MultipleLines": ["Yes", "No", "No phone service"],
    "InternetService": ["Fiber optic", "DSL", "No"],
    "OnlineSecurity": ["Yes", "No", "No internet service"],
    "OnlineBackup": ["Yes", "No", "No internet service"],
    "DeviceProtection": ["Yes", "No", "No internet service"],
    "TechSupport": ["Yes", "No", "No internet service"],
    "StreamingTV": ["Yes", "No", "No internet service"],
    "StreamingMovies": ["Yes", "No", "No internet service"],
    "Contract": ["Month-to-month", "One year", "Two year"],
    "PaperlessBilling": ["Yes", "No"],
    "PaymentMethod": [
        "Electronic check",
        "Mailed check",
        "Bank transfer (automatic)",
        "Credit card (automatic)",
    ],
    "tenure": "int",  # Qo'lda kiritiladi
    "MonthlyCharges": "float",  # Qo'lda kiritiladi
    "TotalCharges": "float",  # Qo'lda kiritiladi
}

# Conversation holatlari (indexlarni hosil qilamiz)
FIELD_LIST = list(FIELDS.keys())
FIELD_STATES = {field: idx for idx, field in enumerate(FIELD_LIST)}
END = ConversationHandler.END


def create_keyboard(options):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(str(option), callback_data=str(option))] for option in options]
    )


def build_status_text(user_data):
    # Foydalanuvchi kiritgan javoblarni qatorlab chiqaramiz
    lines = ["Siz kiritgan ma'lumotlar:"]
    for key in FIELD_LIST:
        if key in user_data:
            lines.append(f"{key}: {user_data[key]}")
    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    first_field = FIELD_LIST[0]

    text = f"Assalomu alaykum! Churn bashorat botiga xush kelibsiz.\n\n"
    text += f"Iltimos, quyidagi savollarga javob bering.\n\n"
    text += build_status_text(context.user_data)
    text += f"\n\n{first_field} uchun javob tanlang:"

    # Agar tanlovli maydon bo'lsa, tugmalar chiqaramiz
    if isinstance(FIELDS[first_field], list):
        await update.message.reply_text(text, reply_markup=create_keyboard(FIELDS[first_field]))
    else:
        # Qo'lda kiritish so'raladi
        await update.message.reply_text(text)
    return FIELD_STATES[first_field]


async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE, field: str, next_state: int) -> int:
    query = update.callback_query
    await query.answer()

    selection = query.data
    context.user_data[field] = selection

    # Keyingi maydonni so'rash
    if next_state == END:
        return await process_data(update, context)

    next_field = FIELD_LIST[next_state]

    text = build_status_text(context.user_data) + f"\n\n{next_field} uchun javob tanlang:"

    if isinstance(FIELDS[next_field], list):
        # Tanlov uchun tugmalar
        await query.message.edit_text(text, reply_markup=create_keyboard(FIELDS[next_field]))
    else:
        # Qo'lda kiritish uchun faqat matn, tugmalar yo'q
        await query.message.edit_text(text, reply_markup=None)

    return next_state


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Qo'lda kiritiladigan maydonlar uchun handler
    user_text = update.message.text
    user_data = context.user_data

    # Qaysi maydonda hozir turganimizni aniqlaymiz:
    current_field = None
    for field in FIELD_LIST:
        if field not in user_data:
            current_field = field
            break

    if current_field is None:
        # Barchasi to'ldirilgan, yakunlash kerak
        await update.message.reply_text("Barcha ma'lumotlar to'ldirildi. Natija hisoblanmoqda...")
        return await process_data(update, context)

    # Kiritilgan qiymatni tekshirish: int yoki float bo'lsa
    field_type = FIELDS[current_field]
    if field_type == "int":
        try:
            val = int(user_text)
            if val < 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text(f"Iltimos, {current_field} uchun musbat butun son kiriting.")
            return FIELD_STATES[current_field]
        context.user_data[current_field] = val

    elif field_type == "float":
        try:
            val = float(user_text)
            if val < 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text(f"Iltimos, {current_field} uchun musbat son kiriting.")
            return FIELD_STATES[current_field]
        context.user_data[current_field] = val
    else:
        # Bu joyga kelmasligi kerak, lekin agar kelib qolsa:
        context.user_data[current_field] = user_text

    # Keyingi maydonni so'rash
    next_index = FIELD_STATES[current_field] + 1
    if next_index == len(FIELD_LIST):
        # Hammasi to'ldirildi
        await update.message.reply_text("Barcha ma'lumotlar to'ldirildi. Natija hisoblanmoqda...")
        return await process_data(update, context)

    next_field = FIELD_LIST[next_index]

    text = build_status_text(context.user_data) + f"\n\n{next_field} uchun javob tanlang:"

    if isinstance(FIELDS[next_field], list):
        # Variantlar bilan tugmalar
        await update.message.reply_text(text, reply_markup=create_keyboard(FIELDS[next_field]))
    else:
        # Qo'lda kiritish uchun faqat matn
        await update.message.reply_text(text, reply_markup=None)

    return next_index


async def process_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Natijani hisoblab, foydalanuvchiga qaytaradi."""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        chat_id = query.message.chat_id
    else:
        chat_id = update.message.chat_id

    data = context.user_data

    # DataFrame yaratish va to'g'ri turga o'tkazish
    df_data = {}
    for key in FIELD_LIST:
        val = data.get(key)
        if val is None:
            # Agar malumot yo'q bo'lsa, default qiymat
            if key in ["tenure"]:
                val = 0
            elif key in ["MonthlyCharges", "TotalCharges"]:
                val = 0.0
            elif key == "SeniorCitizen":
                val = 0
            else:
                val = "No"
        df_data[key] = val

    df = pd.DataFrame([df_data])

    # Modelni yuklash
    try:
        with open("best_model_pipeline.dill", "rb") as f:
            model = dill.load(f)
    except Exception as e:
        logger.error(f"Modelni yuklashda xato: {e}")
        text = "Kechirasiz, modelni yuklashda xato yuz berdi. Keyinroq qayta urinib ko‘ring."
        if update.callback_query:
            await update.callback_query.message.edit_text(text)
        else:
            await update.message.reply_text(text)
        return END

    try:
        prob = model.predict_proba(df)[:, 1][0] * 100
        # Natija: 0 ga yaqin => qoladi, 100 ga yaqin => ketadi
        if prob >= 50:
            result_text = f"Sizning hisobingiz: KETADI, ehtimoli {prob:.1f}%"
        else:
            result_text = f"Sizning hisobingiz: QOLADI, ehtimoli {100 - prob:.1f}%"
    except Exception as e:
        logger.error(f"Taxmin qilishda xato: {e}")
        result_text = "Ma'lumotlarni qayta ishlashda xato yuz berdi. Iltimos, qaytadan urinib ko‘ring."

    if update.callback_query:
        await update.callback_query.message.edit_text(result_text)
    else:
        await update.message.reply_text(result_text)

    context.user_data.clear()
    return END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Jarayon bekor qilindi. /start bilan qayta boshlashingiz mumkin.")
    return ConversationHandler.END


def make_choice_handler(field, next_state):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await handle_choice(update, context, field, next_state)
    return handler


def main():
    application = Application.builder().token("7928709650:AAHUtwRJtlnhJNUKqg0hk094Mqur5EESxl4").build()

    # States uchun handlerlar (tanlovli maydonlar uchun CallbackQueryHandler, qo'lda kiritish uchun MessageHandler)
    states = {}

    for idx, field in enumerate(FIELD_LIST):
        next_state = idx + 1 if idx + 1 < len(FIELD_LIST) else END

        if isinstance(FIELDS[field], list):
            # Variantli maydonlar uchun CallbackQueryHandler
            states[idx] = [CallbackQueryHandler(make_choice_handler(field, next_state))]
        else:
            # Qo'lda kiritiladigan maydonlar uchun MessageHandler
            states[idx] = [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input)]

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states=states,
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    application.add_handler(conv_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
