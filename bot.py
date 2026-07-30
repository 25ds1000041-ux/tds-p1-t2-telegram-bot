import json
import re
import os
import requests
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# 1. Configure Gemini API Key & Telegram Token
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8827024838:AAHSQDomicTZ3DPu6041tD2mLlT80GOCV-0")
LOG_URL = os.getenv("LOG_URL", "https://your-domain.com/run.jsonl")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# 2. Main handler for incoming Telegram messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    
    # If multi-turn message (separated by newlines or paragraphs), focus on the last instruction
    messages = [m.strip() for m in user_text.split('\n\n') if m.strip()]
    latest_query = messages[-1] if messages else user_text

    # Prompt Gemini to answer data analysis questions and output JSON strictly in requested format
    prompt = f"""You are a data analysis agent.
Analyze the following request carefully:
"{latest_query}"

Perform any necessary calculation or data lookup based on public datasets (like MOSPI) or provided inline text.
Return ONLY the raw answer object requested by the question prompt.
Do not wrap it in markdown block quotes if possible, or give any conversational text.
"""
    
    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        # Clean markdown codeblocks if model returned ```json ... ```
        cleaned = re.sub(r'^```(json)?\s*', '', raw_text, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s*```$', '', cleaned).strip()

        # Attempt to parse the answer payload
        try:
            parsed_answer = json.loads(cleaned)
        except json.JSONDecodeError:
            parsed_answer = cleaned

        # Final structured reply required by grading specification
        final_response = {
            "answer": parsed_answer,
            "log_url": LOG_URL
        }

        await update.message.reply_text(json.dumps(final_response))

    except Exception as e:
        error_response = {
            "answer": {"error": str(e)},
            "log_url": LOG_URL
        }
        await update.message.reply_text(json.dumps(error_response))

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running...")
    app.run_polling()
