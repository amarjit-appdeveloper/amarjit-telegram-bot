import os
import time
import html
import math
import re
import datetime

import telebot
from telebot import types
from deep_translator import GoogleTranslator, MyMemoryTranslator

from flask import Flask
from threading import Thread


# ==========================================
# 🔐 BOT CONFIGURATION
# ==========================================

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("TOKEN environment variable is not set!")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")


# ==========================================
# 🌐 FLASK SERVER FOR RENDER
# ==========================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Telegram Bot is running! 🤖"


@app.route("/health")
def health():
    return "OK"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# ==========================================
# 🌐 TRANSLATION ENGINE
# ==========================================

def translate_to_hindi(text):
    if not text or not text.strip():
        return ""

    text = text.strip()

    # Attempt 1: GoogleTranslator English -> Hindi
    try:
        translated = GoogleTranslator(
            source="en",
            target="hi"
        ).translate(text)

        if translated and not (
            "Error" in translated and "500" in translated
        ):
            return translated

    except Exception:
        pass

    # Attempt 2: Auto detect -> Hindi
    try:
        translated = GoogleTranslator(
            source="auto",
            target="hi"
        ).translate(text)

        if translated and not (
            "Error" in translated and "500" in translated
        ):
            return translated

    except Exception:
        pass

    # Attempt 3: MyMemory fallback
    try:
        translated = MyMemoryTranslator(
            source="en-GB",
            target="hi-IN"
        ).translate(text)

        if translated and not translated.startswith("MYMEMORY"):
            return translated

    except Exception:
        pass

    return "अनुवाद नहीं मिल सका ❌"


# ==========================================
# 🧮 ADVANCED MATH CALCULATOR
# ==========================================

MATH_KEYWORDS = {
    "sin", "cos", "tan",
    "asin", "acos", "atan",
    "sqrt", "cbrt",
    "log", "log10", "log2", "ln",
    "exp", "abs", "round",
    "floor", "ceil",
    "factorial", "fact",
    "gcd", "lcm",
    "pi", "e", "pow"
}


def calculate_expression(expr):
    s = expr.strip()

    # Normalize operators
    s = (
        s.replace("×", "*")
        .replace("÷", "/")
        .replace("−", "-")
        .replace("^", "**")
        .replace("π", "pi")
        .replace("X", "*")
    )

    # 1000 + 18% / 1000 - 18%
    s = re.sub(
        r"(\d+(?:\.\d+)?)\s*([+-])\s*(\d+(?:\.\d+)?)%",
        r"(\1 \2 (\1 * \3 / 100))",
        s
    )

    # 15% of 200
    s = re.sub(
        r"(\d+(?:\.\d+)?)%\s*(?:of|\*)\s*(\d+(?:\.\d+)?)",
        r"(\1/100)*\2",
        s,
        flags=re.IGNORECASE
    )

    # Standalone percentage
    s = re.sub(
        r"(\d+(?:\.\d+)?)%",
        r"(\1/100)",
        s
    )

    # Factorial
    s = re.sub(
        r"(\d+)!",
        r"factorial(\1)",
        s
    )

    safe_env = {
        "sin": lambda x: round(math.sin(math.radians(x)), 8),
        "cos": lambda x: round(math.cos(math.radians(x)), 8),
        "tan": lambda x: round(math.tan(math.radians(x)), 8),

        "asin": lambda x: round(math.degrees(math.asin(x)), 8),
        "acos": lambda x: round(math.degrees(math.acos(x)), 8),
        "atan": lambda x: round(math.degrees(math.atan(x)), 8),

        "sqrt": math.sqrt,

        "cbrt": (
            math.cbrt
            if hasattr(math, "cbrt")
            else lambda x: x ** (1 / 3)
        ),

        "log": math.log10,
        "log10": math.log10,
        "log2": math.log2,
        "ln": math.log,
        "exp": math.exp,

        "abs": abs,
        "round": round,
        "floor": math.floor,
        "ceil": math.ceil,

        "factorial": math.factorial,
        "fact": math.factorial,

        "gcd": math.gcd,

        "lcm": (
            math.lcm
            if hasattr(math, "lcm")
            else lambda a, b: abs(a * b) // math.gcd(a, b)
        ),

        "pi": math.pi,
        "e": math.e,
        "pow": pow,
    }

    allowed_pattern = r"^[0-9a-zA-Z_+\-*/%^().,\s]+$"

    if not re.match(allowed_pattern, s):
        raise ValueError("Invalid characters in expression")

    result = eval(
        s,
        {"__builtins__": None},
        safe_env
    )

    if isinstance(result, float) and result.is_integer():
        return int(result)

    if isinstance(result, float):
        return round(result, 6)

    return result


def is_math_expression(text):
    text = text.strip()

    has_digit = any(c.isdigit() for c in text)

    has_math_op = any(
        c in "+-*/^%=÷×−√"
        for c in text
    )

    words = set(
        re.findall(
            r"[a-zA-Z]+",
            text.lower()
        )
    )

    has_math_kw = bool(
        words & MATH_KEYWORDS
    )

    has_pct = bool(
        re.search(
            r"\d+\s*%\s*(?:of|\*|\+|-)?\s*\d+",
            text,
            re.I
        )
    )

    return (
        (has_digit and has_math_op)
        or
        (has_digit and has_math_kw)
        or
        has_pct
    )


# ==========================================
# 🖩 INTERACTIVE CALCULATOR KEYBOARD
# ==========================================

def get_calc_keyboard(mode="basic"):

    markup = types.InlineKeyboardMarkup(row_width=4)

    if mode == "basic":

        r1 = [
            types.InlineKeyboardButton(
                "C",
                callback_data="c_act:clear"
            ),
            types.InlineKeyboardButton(
                "⌫",
                callback_data="c_act:del"
            ),
            types.InlineKeyboardButton(
                "(",
                callback_data="c_btn:("
            ),
            types.InlineKeyboardButton(
                ")",
                callback_data="c_btn:)"
            )
        ]

        r2 = [
            types.InlineKeyboardButton(
                "√",
                callback_data="c_btn:sqrt("
            ),
            types.InlineKeyboardButton(
                "^",
                callback_data="c_btn:^"
            ),
            types.InlineKeyboardButton(
                "%",
                callback_data="c_btn:%"
            ),
            types.InlineKeyboardButton(
                "÷",
                callback_data="c_btn:/"
            )
        ]

        r3 = [
            types.InlineKeyboardButton(
                "7",
                callback_data="c_btn:7"
            ),
            types.InlineKeyboardButton(
                "8",
                callback_data="c_btn:8"
            ),
            types.InlineKeyboardButton(
                "9",
                callback_data="c_btn:9"
            ),
            types.InlineKeyboardButton(
                "×",
                callback_data="c_btn:*"
            )
        ]

        r4 = [
            types.InlineKeyboardButton(
                "4",
                callback_data="c_btn:4"
            ),
            types.InlineKeyboardButton(
                "5",
                callback_data="c_btn:5"
            ),
            types.InlineKeyboardButton(
                "6",
                callback_data="c_btn:6"
            ),
            types.InlineKeyboardButton(
                "−",
                callback_data="c_btn:-"
            )
        ]

        r5 = [
            types.InlineKeyboardButton(
                "1",
                callback_data="c_btn:1"
            ),
            types.InlineKeyboardButton(
                "2",
                callback_data="c_btn:2"
            ),
            types.InlineKeyboardButton(
                "3",
                callback_data="c_btn:3"
            ),
            types.InlineKeyboardButton(
                "+",
                callback_data="c_btn:+"
            )
        ]

        r6 = [
            types.InlineKeyboardButton(
                "0",
                callback_data="c_btn:0"
            ),
            types.InlineKeyboardButton(
                ".",
                callback_data="c_btn:."
            ),
            types.InlineKeyboardButton(
                "00",
                callback_data="c_btn:00"
            ),
            types.InlineKeyboardButton(
                "=",
                callback_data="c_act:equal"
            )
        ]

        r7 = [
            types.InlineKeyboardButton(
                "📐 Scientific Mode",
                callback_data="c_act:mode_sci"
            ),
            types.InlineKeyboardButton(
                "❌ Close",
                callback_data="c_act:close"
            )
        ]

        for row in [r1, r2, r3, r4, r5, r6, r7]:
            markup.row(*row)

    else:

        r1 = [
            types.InlineKeyboardButton(
                "C",
                callback_data="c_act:clear"
            ),
            types.InlineKeyboardButton(
                "⌫",
                callback_data="c_act:del"
            ),
            types.InlineKeyboardButton(
                "(",
                callback_data="c_btn:("
            ),
            types.InlineKeyboardButton(
                ")",
                callback_data="c_btn:)"
            )
        ]

        r2 = [
            types.InlineKeyboardButton(
                "sin",
                callback_data="c_btn:sin("
            ),
            types.InlineKeyboardButton(
                "cos",
                callback_data="c_btn:cos("
            ),
            types.InlineKeyboardButton(
                "tan",
                callback_data="c_btn:tan("
            ),
            types.InlineKeyboardButton(
                "√",
                callback_data="c_btn:sqrt("
            )
        ]

        r3 = [
            types.InlineKeyboardButton(
                "log",
                callback_data="c_btn:log("
            ),
            types.InlineKeyboardButton(
                "ln",
                callback_data="c_btn:ln("
            ),
            types.InlineKeyboardButton(
                "x!",
                callback_data="c_btn:!"
            ),
            types.InlineKeyboardButton(
                "^",
                callback_data="c_btn:^"
            )
        ]

        r4 = [
            types.InlineKeyboardButton(
                "7",
                callback_data="c_btn:7"
            ),
            types.InlineKeyboardButton(
                "8",
                callback_data="c_btn:8"
            ),
            types.InlineKeyboardButton(
                "9",
                callback_data="c_btn:9"
            ),
            types.InlineKeyboardButton(
                "÷",
                callback_data="c_btn:/"
            )
        ]

        r5 = [
            types.InlineKeyboardButton(
                "4",
                callback_data="c_btn:4"
            ),
            types.InlineKeyboardButton(
                "5",
                callback_data="c_btn:5"
            ),
            types.InlineKeyboardButton(
                "6",
                callback_data="c_btn:6"
            ),
            types.InlineKeyboardButton(
                "×",
                callback_data="c_btn:*"
            )
        ]

        r6 = [
            types.InlineKeyboardButton(
                "1",
                callback_data="c_btn:1"
            ),
            types.InlineKeyboardButton(
                "2",
                callback_data="c_btn:2"
            ),
            types.InlineKeyboardButton(
                "3",
                callback_data="c_btn:3"
            ),
            types.InlineKeyboardButton(
                "−",
                callback_data="c_btn:-"
            )
        ]

        r7 = [
            types.InlineKeyboardButton(
                "0",
                callback_data="c_btn:0"
            ),
            types.InlineKeyboardButton(
                ".",
                callback_data="c_btn:."
            ),
            types.InlineKeyboardButton(
                "π",
                callback_data="c_btn:pi"
            ),
            types.InlineKeyboardButton(
                "+",
                callback_data="c_btn:+"
            )
        ]

        r8 = [
            types.InlineKeyboardButton(
                "e",
                callback_data="c_btn:e"
            ),
            types.InlineKeyboardButton(
                "%",
                callback_data="c_btn:%"
            ),
            types.InlineKeyboardButton(
                "🔢 Basic Mode",
                callback_data="c_act:mode_basic"
            ),
            types.InlineKeyboardButton(
                "=",
                callback_data="c_act:equal"
            )
        ]

        r9 = [
            types.InlineKeyboardButton(
                "❌ Close",
                callback_data="c_act:close"
            )
        ]

        for row in [
            r1, r2, r3, r4,
            r5, r6, r7, r8, r9
        ]:
            markup.row(*row)

    return markup


def build_calc_message(expression="0", result=None):

    if result is not None:

        return (
            "🧮 <b>Interactive Calculator</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 <b>Formula:</b> "
            f"<code>{html.escape(str(expression))}</code>\n"
            f"🎯 <b>Result:</b> "
            f"<code>{html.escape(str(result))}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<i>💡 Niche buttons use karein "
            "ya naya calculation karein.</i>"
        )

    return (
        "🧮 <b>Interactive Calculator</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📟 <b>Display:</b> "
        f"<code>{html.escape(str(expression))}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<i>💡 Niche buttons use karein "
        "ya chat me formula type karein!</i>"
    )


def extract_expression_from_text(msg_text):

    if not msg_text:
        return "0"

    m_disp = re.search(
        r"Display:\s*([^<\n\r]+)",
        msg_text
    )

    if m_disp:
        return m_disp.group(1).strip()

    m_res = re.search(
        r"Result:\s*([^<\n\r]+)",
        msg_text
    )

    if m_res:
        return m_res.group(1).strip()

    m_form = re.search(
        r"Formula:\s*([^<\n\r]+)",
        msg_text
    )

    if m_form:
        return m_form.group(1).strip()

    return "0"


# ==========================================
# 🚀 COMMAND HANDLERS
# ==========================================

@bot.message_handler(commands=["start"])
def start(message):

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    markup.add(
        "📖 About",
        "🤖 Help"
    )

    markup.add(
        "📂 Services",
        "🧮 Calculator"
    )

    markup.add(
        "🔗 Join Channel",
        "📞 Contact Me"
    )

    bot.send_message(
        message.chat.id,
        "🤖 <b>Bot is running successfully!</b>\n\n"
        "Niche diye gaye Menu se choose karein 👇",
        reply_markup=markup
    )


@bot.message_handler(commands=["calc", "calculator"])
def open_calculator(message):

    bot.send_message(
        message.chat.id,
        build_calc_message("0"),
        reply_markup=get_calc_keyboard("basic")
    )


@bot.message_handler(
    func=lambda m: m.text == "🧮 Calculator"
)
def calculator_button(m):

    bot.send_message(
        m.chat.id,
        build_calc_message("0"),
        reply_markup=get_calc_keyboard("basic")
    )


# ==========================================
# 📞 CONTACT
# ==========================================

@bot.message_handler(
    func=lambda m: m.text == "📞 Contact Me"
)
def contact(m):

    markup = types.InlineKeyboardMarkup()

    whatsapp_btn = types.InlineKeyboardButton(
        "📱 Chat on WhatsApp",
        url="https://wa.me/918920657286"
    )

    insta_btn = types.InlineKeyboardButton(
        "📷 Instagram Profile",
        url="https://instagram.com/anshuu_ydv1"
    )

    markup.add(whatsapp_btn)
    markup.add(insta_btn)

    bot.send_message(
        m.chat.id,
        "📞 <b>Contact Me</b>\n\n"
        "Click button below 👇",
        reply_markup=markup
    )


# ==========================================
# 📖 ABOUT
# ==========================================

@bot.message_handler(
    func=lambda m: m.text == "📖 About"
)
def about(m):

    bot.reply_to(
        m,
        "📖 <b>About Bot</b>\n\n"
        "Yeh bot <b>Advanced Scientific Calculator</b> "
        "aur <b>Instant English ➔ Hindi Translator</b> "
        "provide karta hai! 🧮🌐"
    )


# ==========================================
# 🤖 HELP
# ==========================================

@bot.message_handler(
    func=lambda m:
        m.text == "🤖 Help"
        or (
            m.text is not None
            and m.text.startswith("/help")
        )
)
def help_cmd(m):

    bot.reply_to(
        m,
        "🤖 <b>Help & Features Guide</b>\n\n"

        "🧮 <b>Calculator Features:</b>\n"
        "• <b>Interactive Keypad:</b> "
        "<code>🧮 Calculator</code> button dabayein\n"
        "• <b>Basic Math:</b> "
        "<code>120 + 45 * 2</code>\n"
        "• <b>Percentage:</b> "
        "<code>15% of 800</code>\n"
        "• <b>GST / Discount:</b> "
        "<code>1000 + 18%</code> "
        "ya <code>1500 - 20%</code>\n"
        "• <b>Powers & Roots:</b> "
        "<code>2^8</code>, <code>sqrt(144)</code>\n"
        "• <b>Trigonometry:</b> "
        "<code>sin(90)</code>, "
        "<code>cos(0)</code>, "
        "<code>tan(45)</code>\n"
        "• <b>Log & Factorial:</b> "
        "<code>log(1000)</code>, "
        "<code>5!</code>\n\n"

        "📊 <b>Special Calculators:</b>\n"
        "• <b>Age:</b> "
        "<code>/age 15-08-2000</code>\n"
        "• <b>BMI:</b> "
        "<code>/bmi 65 170</code>\n"
        "• <b>GST:</b> "
        "<code>/gst 5000 18</code>\n"
        "• <b>EMI:</b> "
        "<code>/emi 100000 10.5 12</code>\n\n"

        "🌐 <b>Translator:</b>\n"
        "• Koi bhi English word ya sentence "
        "type karein Hindi meaning ke liye."
    )


# ==========================================
# 📂 SERVICES
# ==========================================

@bot.message_handler(
    func=lambda m: m.text == "📂 Services"
)
def services(m):

    bot.reply_to(
        m,
        "📂 <b>Services & Features</b>\n\n"
        "✔ Interactive Screen Calculator\n"
        "✔ Scientific Math & Trigonometry\n"
        "✔ Age, BMI, GST & EMI Calculators\n"
        "✔ English → Hindi Translation\n"
        "✔ Telegram Bot Development & Python Automation"
    )


# ==========================================
# 🔗 JOIN CHANNEL
# ==========================================

@bot.message_handler(
    func=lambda m: m.text == "🔗 Join Channel"
)
def join_channel(m):

    bot.reply_to(
        m,
        "🔗 Join our channel:\n"
        "👉 https://t.me/Amarop841313"
    )


# ==========================================
# 🎂 AGE CALCULATOR
# ==========================================

@bot.message_handler(commands=["age"])
def age_calculator(message):

    args = message.text.replace(
        "/age",
        ""
    ).strip()

    if not args:

        bot.reply_to(
            message,
            "ℹ️ <b>Usage:</b> "
            "<code>/age DD-MM-YYYY</code>\n"
            "Example: "
            "<code>/age 15-08-2000</code>"
        )

        return

    try:

        parts = [
            int(p)
            for p in re.split(
                r"[-/.\s]",
                args
            )
            if p
        ]

        if len(parts) != 3:
            raise ValueError()

        day, month, year = parts

        dob = datetime.date(
            year,
            month,
            day
        )

        today = datetime.date.today()

        if dob > today:

            bot.reply_to(
                message,
                "❌ Date of Birth future me nahi ho sakti."
            )

            return

        years = today.year - dob.year
        months = today.month - dob.month
        days = today.day - dob.day

        if days < 0:

            months -= 1

            prev_month = today.month - 1 or 12
            prev_year = (
                today.year
                if today.month > 1
                else today.year - 1
            )

            days_in_prev = (
                datetime.date(
                    today.year,
                    today.month,
                    1
                )
                -
                datetime.date(
                    prev_year,
                    prev_month,
                    1
                )
            ).days

            days += days_in_prev

        if months < 0:

            years -= 1
            months += 12

        total_days = (
            today - dob
        ).days

        total_weeks = total_days // 7

        bot.reply_to(
            message,
            f"🎂 <b>Age Details:</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 <b>DOB:</b> "
            f"{day:02d}-{month:02d}-{year}\n"
            f"⏳ <b>Age:</b> "
            f"<b>{years}</b> Years, "
            f"<b>{months}</b> Months, "
            f"<b>{days}</b> Days\n"
            f"📆 <b>Total Weeks:</b> "
            f"{total_weeks:,} weeks\n"
            f"🗓️ <b>Total Days:</b> "
            f"{total_days:,} days\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )

    except Exception:

        bot.reply_to(
            message,
            "❌ Invalid date format!\n"
            "Please use: "
            "<code>/age DD-MM-YYYY</code>\n"
            "Example: "
            "<code>/age 15-08-2000</code>"
        )


# ==========================================
# ⚖️ BMI CALCULATOR
# ==========================================

@bot.message_handler(commands=["bmi"])
def bmi_calculator(message):

    args = (
        message.text
        .replace("/bmi", "")
        .strip()
        .split()
    )

    if len(args) != 2:

        bot.reply_to(
            message,
            "ℹ️ <b>Usage:</b> "
            "<code>/bmi weight height</code>\n"
            "Example: "
            "<code>/bmi 68 172</code>"
        )

        return

    try:

        weight = float(args[0])
        height_cm = float(args[1])

        height_m = height_cm / 100

        bmi = round(
            weight / (height_m ** 2),
            2
        )

        if bmi < 18.5:
            category = "Underweight 🟡"
        elif bmi < 24.9:
            category = "Normal 🟢"
        elif bmi < 29.9:
            category = "Overweight 🟠"
        else:
            category = "Obese 🔴"

        bot.reply_to(
            message,
            f"⚖️ <b>BMI Calculator Result</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚖️ <b>Weight:</b> {weight} kg\n"
            f"📏 <b>Height:</b> {height_cm} cm\n"
            f"📊 <b>BMI Score:</b> <b>{bmi}</b>\n"
            f"🏷️ <b>Category:</b> {category}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )

    except Exception:

        bot.reply_to(
            message,
            "❌ Invalid values.\n"
            "Example: "
            "<code>/bmi 70 175</code>"
        )


# ==========================================
# 🧾 GST CALCULATOR
# ==========================================

@bot.message_handler(commands=["gst"])
def gst_calculator(message):

    args = (
        message.text
        .replace("/gst", "")
        .strip()
        .split()
    )

    if not args:

        bot.reply_to(
            message,
            "ℹ️ <b>Usage:</b> "
            "<code>/gst amount rate%</code>\n"
            "Example: "
            "<code>/gst 5000 18</code>"
        )

        return

    try:

        amount = float(args[0])

        rate = (
            float(args[1])
            if len(args) > 1
            else 18.0
        )

        gst_amount = round(
            (amount * rate) / 100,
            2
        )

        total = round(
            amount + gst_amount,
            2
        )

        cgst = round(
            gst_amount / 2,
            2
        )

        sgst = round(
            gst_amount / 2,
            2
        )

        bot.reply_to(
            message,
            f"🧾 <b>GST Calculator Result</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 <b>Base Amount:</b> "
            f"₹{amount:,.2f}\n"
            f"📊 <b>GST Rate:</b> {rate}%\n"
            f"🏛️ <b>CGST ({rate / 2}%):</b> "
            f"₹{cgst:,.2f}\n"
            f"🏛️ <b>SGST ({rate / 2}%):</b> "
            f"₹{sgst:,.2f}\n"
            f"💰 <b>Total GST:</b> "
            f"₹{gst_amount:,.2f}\n"
            f"💳 <b>Total Payable:</b> "
            f"<b>₹{total:,.2f}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )

    except Exception:

        bot.reply_to(
            message,
            "❌ Invalid values.\n"
            "Example: "
            "<code>/gst 1000 18</code>"
        )


# ==========================================
# 🏦 EMI CALCULATOR
# ==========================================

@bot.message_handler(commands=["emi"])
def emi_calculator(message):

    args = (
        message.text
        .replace("/emi", "")
        .strip()
        .split()
    )

    if len(args) != 3:

        bot.reply_to(
            message,
            "ℹ️ <b>Usage:</b> "
            "<code>/emi loan rate months</code>\n"
            "Example: "
            "<code>/emi 100000 10.5 12</code>"
        )

        return

    try:

        principal = float(args[0])
        annual_rate = float(args[1])
        months = int(args[2])

        monthly_rate = (
            annual_rate / 12
        ) / 100

        if monthly_rate == 0:

            emi = principal / months

        else:

            emi = (
                principal
                * monthly_rate
                * ((1 + monthly_rate) ** months)
                /
                (((1 + monthly_rate) ** months) - 1)
            )

        total_payment = emi * months
        total_interest = total_payment - principal

        bot.reply_to(
            message,
            f"🏦 <b>Loan EMI Calculator</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Loan Amount:</b> "
            f"₹{principal:,.2f}\n"
            f"📈 <b>Interest Rate:</b> "
            f"{annual_rate}% p.a.\n"
            f"⏳ <b>Tenure:</b> "
            f"{months} Months\n"
            f"💳 <b>Monthly EMI:</b> "
            f"<b>₹{emi:,.2f}</b>\n"
            f"💸 <b>Total Interest:</b> "
            f"₹{total_interest:,.2f}\n"
            f"💵 <b>Total Payable:</b> "
            f"<b>₹{total_payment:,.2f}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )

    except Exception:

        bot.reply_to(
            message,
            "❌ Invalid input.\n"
            "Example: "
            "<code>/emi 100000 10.5 12</code>"
        )


# ==========================================
# 🖱️ CALCULATOR CALLBACKS
# ==========================================

@bot.callback_query_handler(
    func=lambda call:
        call.data.startswith(
            ("c_btn:", "c_act:")
        )
)
def handle_calc_callback(call):

    data = call.data

    curr = extract_expression_from_text(
        call.message.text
    )

    mode = "basic"

    if call.message.reply_markup:

        for row in getattr(
            call.message.reply_markup,
            "keyboard",
            []
        ):

            for btn in row:

                if "Basic Mode" in getattr(
                    btn,
                    "text",
                    ""
                ):

                    mode = "scientific"
                    break

    new_result = None

    if data == "c_act:close":

        try:

            bot.delete_message(
                call.message.chat.id,
                call.message.message_id
            )

        except Exception:
            pass

        return

    elif data == "c_act:clear":

        curr = "0"

    elif data == "c_act:del":

        functions = [
            "sqrt(",
            "cbrt(",
            "sin(",
            "cos(",
            "tan(",
            "asin(",
            "acos(",
            "atan(",
            "log(",
            "ln("
        ]

        for fn in functions:

            if curr.endswith(fn):

                curr = curr[:-len(fn)]
                break

        else:

            if (
                len(curr) <= 1
                or curr == "Error"
            ):

                curr = "0"

            else:

                curr = curr[:-1]

        if not curr:
            curr = "0"

    elif data == "c_act:mode_sci":

        mode = "scientific"

    elif data == "c_act:mode_basic":

        mode = "basic"

    elif data == "c_act:equal":

        try:

            result = calculate_expression(curr)

            new_result = result

            bot.answer_callback_query(
                call.id,
                f"🎯 Answer: {result}"
            )

        except Exception:

            bot.answer_callback_query(
                call.id,
                "❌ Invalid Math Expression!",
                show_alert=True
            )

            return

    elif data.startswith("c_btn:"):

        value = data.split(
            "c_btn:",
            1
        )[1]

        if curr in ["0", "Error"]:

            if value == ".":

                curr = "0."

            elif value in "+-*/^%!":

                curr = "0" + value

            elif value == "00":

                curr = "0"

            else:

                curr = value

        else:

            curr += value

    if new_result is not None:

        new_text = build_calc_message(
            curr,
            result=new_result
        )

    else:

        new_text = build_calc_message(
            curr
        )

    new_markup = get_calc_keyboard(mode)

    try:

        bot.edit_message_text(
            new_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=new_markup
        )

    except Exception:
        pass

    try:

        bot.answer_callback_query(
            call.id
        )

    except Exception:
        pass


# ==========================================
# 🔢 CHAT HANDLER
# ==========================================

@bot.message_handler(
    func=lambda m: True
)
def handle_message(m):

    text = (
        m.text.strip()
        if m.text
        else ""
    )

    if not text:
        return

    # Math
    if is_math_expression(text):

        try:

            result = calculate_expression(text)

            bot.reply_to(
                m,
                f"🧮 <b>Calculation Result</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📝 <b>Expression:</b> "
                f"<code>{html.escape(text)}</code>\n"
                f"🎯 <b>Result:</b> "
                f"<b><code>{html.escape(str(result))}</code></b>\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )

            return

        except Exception:
            pass

    # Translation
    hindi = translate_to_hindi(text)

    bot.reply_to(
        m,
        f"🌐 Hindi meaning: "
        f"<b>{html.escape(hindi)}</b>"
    )


# ==========================================
# 🔄 START BOT
# ==========================================

def start_bot():

    print("🤖 Telegram bot is starting...")

    try:

        bot.delete_webhook(
            drop_pending_updates=True
        )

    except Exception:
        pass

    while True:

        try:

            bot.infinity_polling(
                timeout=20,
                long_polling_timeout=10,
                skip_pending=True
            )

        except Exception as e:

            print("Bot Error:", e)

            time.sleep(5)


# ==========================================
# 🚀 MAIN
# ==========================================

if __name__ == "__main__":

    print("🚀 Starting web server...")

    web_thread = Thread(
        target=run_web,
        daemon=True
    )

    web_thread.start()

    start_bot()
