import os
import sqlite3
import random
import logging
from datetime import datetime, timedelta, timezone
from html import escape

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ============================================================
# WORLD WAR V4
# Telegram Grand Strategy Game
# Railway Friendly
# Persian UI
# 4 MAIN BUTTONS + SUBMENUS
# ============================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("world-war-v4")

DB_NAME = os.getenv("DB_NAME", "world_war.db")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

# ============================================================
# OPTIONAL OPENAI
# ============================================================

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

AI = (
    AsyncOpenAI(api_key=OPENAI_API_KEY)
    if AsyncOpenAI and OPENAI_API_KEY
    else None
)

# ============================================================
# MAIN MENU
# EXACTLY 4 BUTTONS
# ============================================================

MAIN_BUTTONS = [
    ["⚔️ جنگ و عملیات", "🏭 کشور و اقتصاد"],
    ["🪖 ارتش و تجهیزات", "👤 پروفایل و تنظیمات"],
]

# ============================================================
# SUB MENUS
# ============================================================

WAR_MENU = [
    ["🎯 حمله به کشور", "🛡 دفاع"],
    ["🕵️ جاسوسی", "🤝 دیپلماسی"],
    ["🛰️ دفاع و ماهواره", "💣 اتاق هسته‌ای"],
    ["🔙 بازگشت به منوی اصلی"],
]

ECONOMY_MENU = [
    ["🌍 وضعیت کشور", "🗺️ نقشه جهان"],
    ["🏭 کارخانه", "🌐 بازار جهانی"],
    ["🧬 فناوری", "🏛️ سیاست داخلی"],
    ["📰 خبرگزاری جهان", "🏆 لیگ و رتبه‌بندی"],
    ["🔙 بازگشت به منوی اصلی"],
]

ARMY_MENU = [
    ["📊 وضعیت ارتش", "🛒 خرید تجهیزات"],
    ["🏭 تولید تجهیزات", "🎖 ژنرال‌ها"],
    ["⬆️ ارتقای پدافند", "📡 ارتقای رادار"],
    ["🔙 بازگشت به منوی اصلی"],
]

PROFILE_MENU = [
    ["👤 پروفایل", "🎯 مأموریت‌ها"],
    ["🎁 پاداش روزانه", "🏅 دستاوردها"],
    ["🧠 مشاور هوش مصنوعی", "📜 راهنما"],
    ["⚙️ تنظیمات بازی"],
    ["🔙 بازگشت به منوی اصلی"],
]

# ============================================================
# WEATHER
# ============================================================

WEATHER = {
    "CLEAR": ("☀️", "صاف", 1.00),
    "WINTER": ("❄️", "زمستان سخت", 0.88),
    "SANDSTORM": ("🌪️", "طوفان شن", 0.82),
    "RAIN": ("🌧️", "بارندگی شدید", 0.90),
    "FOG": ("🌫️", "مه غلیظ", 0.86),
}

# ============================================================
# EQUIPMENT
# ============================================================

EQUIPMENT = [
    ("rifle", "🔫 تفنگ پیاده‌نظام", "INFANTRY", 1.0, 1.0, 3000, 0.5),
    ("apc", "🚙 نفربر زرهی", "GROUND", 2.0, 1.2, 12000, 1.2),
    ("ifv", "🛡️ خودروی رزمی پیاده‌نظام", "GROUND", 2.7, 1.4, 18000, 1.5),
    ("tank", "🛡️ تانک اصلی میدان نبرد", "GROUND", 5.0, 2.2, 55000, 3.0),
    ("artillery", "💥 توپخانه خودکششی", "GROUND", 4.0, 1.8, 42000, 2.5),
    ("mlrs", "🚀 سامانه راکتی چندگانه", "GROUND", 5.5, 1.5, 70000, 3.5),
    ("sam", "🛡️ سامانه پدافند هوایی", "AIR_DEFENSE", 2.0, 6.0, 90000, 4.0),
    ("radar", "📡 رادار آرایه‌ای", "DEFENSE", 0.5, 5.0, 65000, 2.0),
    ("fighter", "✈️ جنگنده چندمنظوره", "AIR", 6.0, 4.5, 900000, 15.0),
    ("interceptor", "🛩️ رهگیر هوایی", "AIR", 5.0, 5.0, 750000, 12.0),
    ("bomber", "💣 بمب‌افکن", "AIR", 8.0, 2.0, 1600000, 20.0),
    ("attack_heli", "🚁 بالگرد تهاجمی", "AIR", 5.5, 2.0, 450000, 7.0),
    ("transport_heli", "🚁 بالگرد ترابری", "LOGISTICS", 1.5, 1.0, 300000, 4.0),
    ("drone", "🛸 پهپاد شناسایی", "DRONE", 2.0, 2.0, 70000, 1.5),
    ("ew_drone", "📡 پهپاد جنگ الکترونیک", "DRONE", 2.5, 3.5, 180000, 2.5),
    ("stealth_drone", "👻 پهپاد پنهان‌کار", "DRONE", 4.0, 3.5, 400000, 4.0),
    ("frigate", "🚢 ناوچه", "NAVY", 3.0, 2.0, 800000, 10.0),
    ("destroyer", "⚓ ناوشکن", "NAVY", 5.5, 4.0, 1500000, 16.0),
    ("cruiser", "🚢 رزم‌ناو", "NAVY", 7.0, 4.5, 2200000, 22.0),
    ("carrier", "🛳️ ناو هواپیمابر", "NAVY", 12.0, 6.0, 6500000, 50.0),
    ("submarine", "🌊 زیردریایی", "NAVY", 7.0, 5.0, 2500000, 25.0),
    ("cruise_missile", "🚀 موشک کروز", "MISSILE", 10.0, 1.0, 120000, 0.5),
    ("ballistic_missile", "🚀 موشک بالستیک", "MISSILE", 14.0, 1.0, 400000, 1.0),
    ("hypersonic", "⚡ موشک هایپرسونیک", "MISSILE", 20.0, 2.0, 1200000, 2.0),
    ("satellite", "🛰️ ماهواره نظامی", "SPACE", 2.0, 8.0, 3000000, 10.0),
]

EQ = {x[0]: x for x in EQUIPMENT}

# ============================================================
# COUNTRIES
# ============================================================

COUNTRIES = [
    ("IRN", "ایران", "🇮🇷", 85_000_000),
    ("USA", "آمریکا", "🇺🇸", 330_000_000),
    ("RUS", "روسیه", "🇷🇺", 144_000_000),
    ("CHN", "چین", "🇨🇳", 1_400_000_000),
    ("DEU", "آلمان", "🇩🇪", 83_000_000),
    ("FRA", "فرانسه", "🇫🇷", 67_000_000),
    ("GBR", "انگلیس", "🇬🇧", 67_000_000),
    ("JPN", "ژاپن", "🇯🇵", 125_000_000),
    ("TUR", "ترکیه", "🇹🇷", 84_000_000),
    ("IND", "هند", "🇮🇳", 1_380_000_000),
]

PROVINCES = {
    "IRN": ["تهران", "اصفهان", "خوزستان", "فارس", "کرمان", "گیلان", "مازندران"],
    "USA": ["کالیفرنیا", "تگزاس", "نیویورک", "فلوریدا", "آلاسکا"],
    "RUS": ["مسکو", "سن‌پترزبورگ", "سیبری", "قازان", "ولگوگراد"],
    "CHN": ["پکن", "شانگهای", "گوانگ‌دونگ", "سیچوان", "شین‌جیانگ"],
    "DEU": ["برلین", "باواریا", "هامبورگ", "هسن"],
    "FRA": ["پاریس", "لیون", "مارسی", "تولوز"],
    "GBR": ["لندن", "اسکاتلند", "ولز", "منچستر"],
    "JPN": ["توکیو", "اوساکا", "هوکایدو", "کیوتو"],
    "TUR": ["استانبول", "آنکارا", "ازمیر", "آنتالیا"],
    "IND": ["دهلی", "ماهاراشترا", "گجرات", "بنگال غربی"],
}

# ============================================================
# DATABASE
# ============================================================

def db():
    con = sqlite3.connect(DB_NAME, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def q(sql, params=(), one=False, all=False, commit=False):
    con = db()
    try:
        cur = con.execute(sql, params)

        if one:
            result = cur.fetchone()
        elif all:
            result = cur.fetchall()
        else:
            result = None

        if commit:
            con.commit()

        return result
    finally:
        con.close()


def now():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.isoformat()


def parse_dt(value):
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return now()


def user(uid):
    return q(
        "SELECT * FROM users WHERE user_id=?",
        (uid,),
        one=True,
    )


def country(code):
    return q(
        "SELECT * FROM countries WHERE code=?",
        (code,),
        one=True,
    )


def army(uid):
    return q(
        "SELECT * FROM armies WHERE user_id=?",
        (uid,),
        one=True,
    )


def factory(uid):
    return q(
        "SELECT * FROM factories WHERE user_id=?",
        (uid,),
        one=True,
    )


def admin(uid):
    return uid in ADMIN_IDS


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():

    con = db()
    c = con.cursor()

    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            commander_name TEXT NOT NULL,
            country_code TEXT NOT NULL,
            level INTEGER DEFAULT 1,
            score INTEGER DEFAULT 0,
            approval INTEGER DEFAULT 100,
            chat_state TEXT DEFAULT 'NONE',
            alliance_id INTEGER DEFAULT 0,
            tech_level INTEGER DEFAULT 1,
            is_sanctioned INTEGER DEFAULT 0,
            in_civil_war INTEGER DEFAULT 0,
            last_daily TEXT DEFAULT '',
            season_score INTEGER DEFAULT 0,
            reputation INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS countries(
            code TEXT PRIMARY KEY,
            name TEXT,
            flag TEXT,
            population INTEGER,
            money REAL DEFAULT 1000000,
            oil REAL DEFAULT 50000,
            steel REAL DEFAULT 50000,
            food REAL DEFAULT 100000,
            power REAL DEFAULT 50000,
            gold REAL DEFAULT 1000,
            is_ai INTEGER DEFAULT 1,
            has_satellite INTEGER DEFAULT 0,
            chokepoint_control INTEGER DEFAULT 0,
            stability INTEGER DEFAULT 80,
            tax_rate INTEGER DEFAULT 10
        );

        CREATE TABLE IF NOT EXISTS provinces(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_code TEXT,
            name TEXT,
            population INTEGER,
            security INTEGER DEFAULT 100,
            infrastructure INTEGER DEFAULT 1,
            owner_id INTEGER DEFAULT 0,
            is_radioactive INTEGER DEFAULT 0,
            weather_condition TEXT DEFAULT 'CLEAR',
            factory_level INTEGER DEFAULT 1,
            defense_level INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS armies(
            user_id INTEGER PRIMARY KEY,
            soldiers INTEGER DEFAULT 10000,
            morale INTEGER DEFAULT 85,
            cyber_level INTEGER DEFAULT 1,
            air_defense INTEGER DEFAULT 1,
            logistics INTEGER DEFAULT 1,
            nukes INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS equipment_inventory(
            user_id INTEGER,
            equipment TEXT,
            amount INTEGER DEFAULT 0,
            PRIMARY KEY(user_id,equipment)
        );

        CREATE TABLE IF NOT EXISTS factories(
            user_id INTEGER PRIMARY KEY,
            level INTEGER DEFAULT 1,
            queue_equipment TEXT DEFAULT '',
            queue_amount INTEGER DEFAULT 0,
            finish_time TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS wars(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attacker_id INTEGER,
            defender_id INTEGER DEFAULT 0,
            province_id INTEGER,
            end_time TEXT,
            attacker_tactic TEXT DEFAULT 'STANDARD',
            status TEXT DEFAULT 'ACTIVE',
            attacker_power REAL DEFAULT 0,
            defender_power REAL DEFAULT 0,
            attacker_ai_code TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS alliances(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            leader_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS alliance_members(
            alliance_id INTEGER,
            user_id INTEGER UNIQUE
        );

        CREATE TABLE IF NOT EXISTS generals(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            type TEXT,
            level INTEGER DEFAULT 1,
            is_alive INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS news(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS achievements(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            code TEXT,
            title TEXT,
            UNIQUE(user_id,code)
        );

        CREATE TABLE IF NOT EXISTS missions(
            user_id INTEGER,
            day TEXT,
            code TEXT,
            title TEXT,
            progress INTEGER DEFAULT 0,
            target INTEGER,
            reward INTEGER,
            claimed INTEGER DEFAULT 0,
            PRIMARY KEY(user_id,day,code)
        );

        CREATE TABLE IF NOT EXISTS spies(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            target_user_id INTEGER,
            operation TEXT,
            end_time TEXT,
            status TEXT DEFAULT 'ACTIVE'
        );

        CREATE TABLE IF NOT EXISTS market_prices(
            item TEXT PRIMARY KEY,
            price REAL
        );

        CREATE TABLE IF NOT EXISTS admin_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS game_state(
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )

    # ---------------- MIGRATIONS ----------------

    migrations = {
        "users": [
            ("tech_level", "INTEGER DEFAULT 1"),
            ("last_daily", "TEXT DEFAULT ''"),
            ("season_score", "INTEGER DEFAULT 0"),
            ("reputation", "INTEGER DEFAULT 0"),
        ],
        "countries": [
            ("stability", "INTEGER DEFAULT 80"),
            ("tax_rate", "INTEGER DEFAULT 10"),
        ],
        "provinces": [
            ("factory_level", "INTEGER DEFAULT 1"),
            ("defense_level", "INTEGER DEFAULT 1"),
        ],
        "armies": [
            ("morale", "INTEGER DEFAULT 85"),
            ("cyber_level", "INTEGER DEFAULT 1"),
            ("air_defense", "INTEGER DEFAULT 1"),
            ("logistics", "INTEGER DEFAULT 1"),
            ("nukes", "INTEGER DEFAULT 0"),
        ],
        "wars": [
            ("attacker_ai_code", "TEXT DEFAULT ''"),
        ],
    }

    for table, columns in migrations.items():

        existing = {
            row[1]
            for row in c.execute(
                f"PRAGMA table_info({table})"
            ).fetchall()
        }

        for column, spec in columns:

            if column not in existing:

                c.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {spec}"
                )

    # ---------------- COUNTRIES ----------------

    for code, name, flag, population in COUNTRIES:

        c.execute(
            """
            INSERT OR IGNORE INTO countries
            (code,name,flag,population)
            VALUES(?,?,?,?)
            """,
            (code, name, flag, population),
        )

    # ---------------- PROVINCES ----------------

    for code, names in PROVINCES.items():

        count = c.execute(
            "SELECT COUNT(*) FROM provinces WHERE country_code=?",
            (code,),
        ).fetchone()[0]

        if count == 0:

            for name in names:

                c.execute(
                    """
                    INSERT INTO provinces
                    (country_code,name,population,owner_id)
                    VALUES(?,?,?,0)
                    """,
                    (
                        code,
                        name,
                        random.randint(1_000_000, 20_000_000),
                    ),
                )

    # ---------------- MARKET ----------------

    market = [
        ("oil", 100),
        ("steel", 80),
        ("food", 40),
        ("power", 60),
        ("gold", 500),
    ]

    for item, price in market:

        c.execute(
            """
            INSERT OR IGNORE INTO market_prices
            (item,price)
            VALUES(?,?)
            """,
            (item, price),
        )

    # ---------------- GAME STATE ----------------

    c.execute(
        """
        INSERT OR IGNORE INTO game_state
        (key,value)
        VALUES('season','1')
        """
    )

    c.execute(
        """
        INSERT OR IGNORE INTO game_state
        (key,value)
        VALUES('season_end',?)
        """,
        (iso(now() + timedelta(days=30)),),
    )

    con.commit()
    con.close()


# ============================================================
# NEWS
# ============================================================

def news(text):

    q(
        "INSERT INTO news(content) VALUES(?)",
        (text,),
        commit=True,
    )

    q(
        """
        DELETE FROM news
        WHERE id NOT IN
        (
            SELECT id FROM news
            ORDER BY id DESC
            LIMIT 300
        )
        """,
        commit=True,
    )


# ============================================================
# KEYBOARD HELPERS
# ============================================================

def keyboard(rows):

    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(button) for button in row]
            for row in rows
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def main_kb(uid=None):

    rows = list(MAIN_BUTTONS)

    return keyboard(rows)


def war_kb():
    return keyboard(WAR_MENU)


def economy_kb():
    return keyboard(ECONOMY_MENU)


def army_kb():
    return keyboard(ARMY_MENU)


def profile_kb(uid=None):

    rows = list(PROFILE_MENU)

    # Admin is hidden inside profile/settings.
    if uid in ADMIN_IDS:
        rows.insert(
            -1,
            ["👑 پنل مدیریت"],
        )

    return keyboard(rows)


def inline(*rows):

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text,
                    callback_data=data,
                )
                for text, data in row
            ]
            for row in rows
        ]
    )


def home_markup():

    return inline(
        [
            ("🏠 منوی اصلی", "home"),
        ]
    )


async def edit_or_send(
    query,
    text,
    markup=None,
    html=True,
):

    try:

        await query.edit_message_text(
            text,
            reply_markup=markup,
            parse_mode="HTML" if html else None,
        )

    except Exception:

        await query.message.reply_text(
            text,
            reply_markup=markup,
            parse_mode="HTML" if html else None,
        )


# ============================================================
# STATUS
# ============================================================

def status_header(uid):

    u = user(uid)

    if not u:
        return ""

    c = country(u["country_code"])
    a = army(uid)

    return (
        f"{c['flag']} <b>{escape(c['name'])}</b> | "
        f"💰 ${c['money']:,.0f} | "
        f"😊 {u['approval']}% | "
        f"⚔️ {a['morale']}%"
    )


# ============================================================
# START
# ============================================================

async def start(update, context):

    uid = update.effective_user.id

    if user(uid):

        await update.message.reply_text(
            "🌍 <b>ستاد فرماندهی آنلاین شد.</b>\n\n"
            "یکی از چهار بخش اصلی را انتخاب کنید.",
            parse_mode="HTML",
            reply_markup=main_kb(uid),
        )

        return

    rows = q(
        """
        SELECT code,name,flag
        FROM countries
        WHERE is_ai=1
        AND code NOT IN
        (
            SELECT country_code FROM users
        )
        """,
        all=True,
    )

    keys = []
    row = []

    for r in rows:

        row.append(
            InlineKeyboardButton(
                f"{r['flag']} {r['name']}",
                callback_data=f"country:{r['code']}",
            )
        )

        if len(row) == 2:

            keys.append(row)
            row = []

    if row:
        keys.append(row)

    await update.message.reply_text(
        f"🌍 <b>WORLD WAR V4</b>\n\n"
        f"فرمانده "
        f"{escape(update.effective_user.first_name)}"
        f"، کشور خود را انتخاب کنید:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keys),
    )


# ============================================================
# COUNTRY SELECTION
# ============================================================

async def select_country(query, code):

    uid = query.from_user.id
    c = country(code)

    if user(uid) or not c or not c["is_ai"]:

        await edit_or_send(
            query,
            "❌ این کشور دیگر قابل انتخاب نیست.",
            home_markup(),
        )

        return

    con = db()

    try:

        con.execute("BEGIN IMMEDIATE")

        commander = f"فرمانده {query.from_user.first_name}"

        con.execute(
            """
            INSERT INTO users
            (user_id,commander_name,country_code)
            VALUES(?,?,?)
            """,
            (
                uid,
                commander,
                code,
            ),
        )

        con.execute(
            "INSERT INTO armies(user_id) VALUES(?)",
            (uid,),
        )

        con.execute(
            "INSERT INTO factories(user_id) VALUES(?)",
            (uid,),
        )

        for eq in EQ:

            con.execute(
                """
                INSERT INTO equipment_inventory
                (user_id,equipment,amount)
                VALUES(?,?,0)
                """,
                (
                    uid,
                    eq,
                ),
            )

        con.execute(
            """
            UPDATE equipment_inventory
            SET amount=?
            WHERE user_id=?
            AND equipment='rifle'
            """,
            (
                5000,
                uid,
            ),
        )

        con.execute(
            """
            UPDATE countries
            SET is_ai=0
            WHERE code=?
            """,
            (code,),
        )

        con.execute(
            """
            UPDATE provinces
            SET owner_id=?
            WHERE country_code=?
            """,
            (
                uid,
                code,
            ),
        )

        con.execute(
            """
            INSERT INTO generals
            (user_id,name,type)
            VALUES(?,?,?)
            """,
            (
                uid,
                "ژنرال اصلی",
                "LAND",
            ),
        )

        con.commit()

    finally:

        con.close()

    news(
        f"👑 {commander} فرماندهی "
        f"{c['flag']} {c['name']} را بر عهده گرفت."
    )

    await edit_or_send(
        query,
        f"✅ کشور {c['flag']} "
        f"<b>{c['name']}</b> به فرماندهی شما درآمد.",
    )

    await query.message.reply_text(
        "🎖 <b>ستاد فرماندهی فعال شد.</b>\n\n"
        "از چهار بخش اصلی استفاده کنید.",
        parse_mode="HTML",
        reply_markup=main_kb(uid),
    )


# ============================================================
# SUBMENU SCREENS
# ============================================================

async def open_war_menu(update, context):

    await update.message.reply_text(
        "⚔️ <b>جنگ و عملیات</b>\n\n"
        "تمام عملیات نظامی و روابط خارجی از این بخش مدیریت می‌شود.",
        parse_mode="HTML",
        reply_markup=war_kb(),
    )


async def open_economy_menu(update, context):

    await update.message.reply_text(
        "🏭 <b>کشور و اقتصاد</b>\n\n"
        "اقتصاد، استان‌ها، کارخانه، بازار و سیاست کشور را مدیریت کنید.",
        parse_mode="HTML",
        reply_markup=economy_kb(),
    )


async def open_army_menu(update, context):

    await update.message.reply_text(
        "🪖 <b>ارتش و تجهیزات</b>\n\n"
        "ارتش، تجهیزات، تولید و فرماندهان خود را مدیریت کنید.",
        parse_mode="HTML",
        reply_markup=army_kb(),
    )


async def open_profile_menu(update, context):

    await update.message.reply_text(
        "👤 <b>پروفایل و تنظیمات</b>\n\n"
        "اطلاعات فرمانده، مأموریت‌ها، دستاوردها و تنظیمات.",
        parse_mode="HTML",
        reply_markup=profile_kb(update.effective_user.id),
    )


async def go_home(update, context):

    await update.message.reply_text(
        "🌍 <b>منوی اصلی</b>\n\n"
        "یکی از چهار بخش اصلی را انتخاب کنید.",
        parse_mode="HTML",
        reply_markup=main_kb(update.effective_user.id),
    )


# ============================================================
# PROFILE
# ============================================================

async def profile(update, context):

    uid = update.effective_user.id

    u = user(uid)
    c = country(u["country_code"])
    a = army(uid)

    provinces = q(
        """
        SELECT COUNT(*) n
        FROM provinces
        WHERE owner_id=?
        """,
        (uid,),
        one=True,
    )["n"]

    text = (
        f"{status_header(uid)}\n\n"
        f"👤 <b>پروفایل فرمانده</b>\n\n"
        f"🎖 فرمانده: {escape(u['commander_name'])}\n"
        f"⭐ سطح: {u['level']}\n"
        f"🏆 امتیاز: {u['score']:,}\n"
        f"🏅 امتیاز فصل: {u['season_score']:,}\n"
        f"😊 رضایت: {u['approval']}%\n"
        f"🏛 ثبات: {c['stability']}%\n"
        f"🗺 استان‌ها: {provinces}\n\n"
        f"💰 خزانه: ${c['money']:,.0f}\n"
        f"🛢 نفت: {c['oil']:,.0f}\n"
        f"🔩 فولاد: {c['steel']:,.0f}\n"
        f"🌾 غذا: {c['food']:,.0f}\n"
        f"⚡ انرژی: {c['power']:,.0f}\n"
        f"🪙 طلا: {c['gold']:,.0f}\n\n"
        f"🪖 روحیه: {a['morale']}%\n"
        f"💻 سایبری: {a['cyber_level']}\n"
        f"🛡 پدافند: {a['air_defense']}\n"
        f"📦 لجستیک: {a['logistics']}"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=profile_kb(uid),
    )


# ============================================================
# MAP
# ============================================================

async def world_map(update, context):

    rows = q(
        """
        SELECT
            c.code,
            c.name,
            c.flag,
            c.is_ai,
            COUNT(p.id) provinces
        FROM countries c
        LEFT JOIN provinces p
            ON p.country_code=c.code
        GROUP BY c.code
        ORDER BY c.name
        """,
        all=True,
    )

    lines = [
        "🗺️ <b>نقشه سیاسی جهان</b>",
        "",
    ]

    for r in rows:

        owner = q(
            """
            SELECT commander_name
            FROM users
            WHERE country_code=?
            """,
            (r["code"],),
            one=True,
        )

        who = (
            owner["commander_name"]
            if owner
            else "هوش مصنوعی"
        )

        lines.append(
            f"{r['flag']} <b>{r['name']}</b> — "
            f"{who} | {r['provinces']} استان"
        )

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=inline(
            [
                ("🗺️ استان‌های کشور من", "map:mine"),
            ],
            [
                ("🏠 منوی اصلی", "home"),
            ],
        ),
    )


async def map_mine(query):

    uid = query.from_user.id

    rows = q(
        """
        SELECT
            id,
            name,
            security,
            infrastructure,
            factory_level,
            defense_level,
            weather_condition
        FROM provinces
        WHERE owner_id=?
        """,
        (uid,),
        all=True,
    )

    if not rows:

        text = "🗺️ هیچ استانی در اختیار شما نیست."

    else:

        lines = ["🗺️ <b>استان‌های شما</b>", ""]

        for r in rows:

            weather = WEATHER.get(
                r["weather_condition"],
                WEATHER["CLEAR"],
            )

            lines.append(
                f"📍 {r['name']}\n"
                f"🛡 دفاع: {r['defense_level']}\n"
                f"🏭 کارخانه: {r['factory_level']}\n"
                f"🌦 {weather[1]}\n"
            )

        text = "\n".join(lines)

    await edit_or_send(
        query,
        text,
        home_markup(),
    )


# ============================================================
# ARMY
# ============================================================

def inv(uid):

    rows = q(
        """
        SELECT equipment,amount
        FROM equipment_inventory
        WHERE user_id=?
        AND amount>0
        ORDER BY equipment
        """,
        (uid,),
        all=True,
    )

    return {
        r["equipment"]: r["amount"]
        for r in rows
    }


def military_power(uid):

    data = inv(uid)

    power = 0

    for key, amount in data.items():

        power += EQ[key][3] * amount

    a = army(uid)

    return (
        power
        * (1 + a["morale"] / 200)
        * (1 + a["logistics"] * 0.05)
    )


async def army_screen(update, context):

    uid = update.effective_user.id

    a = army(uid)

    data = inv(uid)

    power = military_power(uid)

    lines = [
        f"{status_header(uid)}",
        "",
        "🪖 <b>وضعیت ارتش</b>",
        "",
        f"⚔️ قدرت نظامی: <b>{power:,.0f}</b>",
        f"👥 سربازان: {a['soldiers']:,}",
        f"😊 روحیه: {a['morale']}%",
        f"💻 سایبری: {a['cyber_level']}",
        f"🛡 پدافند: {a['air_defense']}",
        f"📦 لجستیک: {a['logistics']}",
        "",
        "📦 <b>تجهیزات</b>",
    ]

    for key, amount in list(data.items())[:18]:

        lines.append(
            f"{EQ[key][1]}: {amount:,}"
        )

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=army_kb(),
    )


# ============================================================
# EQUIPMENT SHOP
# ============================================================

async def equipment_shop(query, page=0):

    uid = query.from_user.id

    u = user(uid)
    c = country(u["country_code"])

    start = page * 8

    keys = []

    for item in EQUIPMENT[start:start + 8]:

        key, name, category, atk, defense, cost, maintenance = item

        keys.append(
            [
                InlineKeyboardButton(
                    f"{name} | ${cost:,.0f}",
                    callback_data=f"buy:{key}",
                )
            ]
        )

    nav = []

    if page > 0:

        nav.append(
            InlineKeyboardButton(
                "⬅️",
                callback_data=f"shop:{page-1}",
            )
        )

    if start + 8 < len(EQUIPMENT):

        nav.append(
            InlineKeyboardButton(
                "➡️",
                callback_data=f"shop:{page+1}",
            )
        )

    if nav:
        keys.append(nav)

    keys.append(
        [
            InlineKeyboardButton(
                "🏠 منوی اصلی",
                callback_data="home",
            )
        ]
    )

    await edit_or_send(
        query,
        f"🛒 <b>فروشگاه تجهیزات</b>\n\n"
        f"💰 موجودی: ${c['money']:,.0f}\n"
        f"📦 تجهیزات: {len(EQUIPMENT)} نوع\n\n"
        f"هر خرید یک واحد است.",
        InlineKeyboardMarkup(keys),
    )


async def buy_equipment(query, key):

    uid = query.from_user.id

    u = user(uid)
    c = country(u["country_code"])

    item = EQ.get(key)

    if not item:
        return

    cost = item[5]

    if c["money"] < cost:

        await edit_or_send(
            query,
            "❌ بودجه کافی نیست.",
            home_markup(),
        )

        return

    q(
        """
        UPDATE countries
        SET money=money-?
        WHERE code=?
        """,
        (
            cost,
            u["country_code"],
        ),
        commit=True,
    )

    q(
        """
        UPDATE equipment_inventory
        SET amount=amount+1
        WHERE user_id=?
        AND equipment=?
        """,
        (
            uid,
            key,
        ),
        commit=True,
    )

    q(
        """
        UPDATE users
        SET score=score+1
        WHERE user_id=?
        """,
        (uid,),
        commit=True,
    )

    await edit_or_send(
        query,
        f"✅ {item[1]} خریداری شد.\n\n"
        f"💰 هزینه: ${cost:,.0f}",
        inline(
            [
                ("🛒 ادامه خرید", "army:shop"),
            ],
            [
                ("🏠 منوی اصلی", "home"),
            ],
        ),
    )


# ============================================================
# FACTORY
# ============================================================

async def economy(update, context):

    uid = update.effective_user.id

    u = user(uid)

    c = country(u["country_code"])

    f = factory(uid)

    queued = (
        EQ[f["queue_equipment"]][1]
        if f["queue_equipment"] in EQ
        else "—"
    )

    text = (
        f"{status_header(uid)}\n\n"
        f"🏭 <b>کشور و اقتصاد</b>\n\n"
        f"🏭 سطح کارخانه: {f['level']}\n"
        f"📦 سفارش: {queued}\n"
        f"🔢 تعداد: {f['queue_amount']}\n"
        f"⏱ پایان: {f['finish_time'] or '—'}\n\n"
        f"💰 ${c['money']:,.0f}\n"
        f"🛢 نفت: {c['oil']:,.0f}\n"
        f"🔩 فولاد: {c['steel']:,.0f}\n"
        f"🌾 غذا: {c['food']:,.0f}\n"
        f"⚡ انرژی: {c['power']:,.0f}"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=economy_kb(),
    )


async def factory_menu(query, page=0):

    start = page * 8

    keys = []

    for item in EQUIPMENT[start:start + 8]:

        key, name, *_ = item

        keys.append(
            [
                InlineKeyboardButton(
                    name,
                    callback_data=f"prod:{key}",
                )
            ]
        )

    nav = []

    if page > 0:

        nav.append(
            InlineKeyboardButton(
                "⬅️",
                callback_data=f"factory:page:{page-1}",
            )
        )

    if start + 8 < len(EQUIPMENT):

        nav.append(
            InlineKeyboardButton(
                "➡️",
                callback_data=f"factory:page:{page+1}",
            )
        )

    if nav:
        keys.append(nav)

    keys.append(
        [
            InlineKeyboardButton(
                "🏠 منوی اصلی",
                callback_data="home",
            )
        ]
    )

    total_pages = (
        len(EQUIPMENT) + 7
    ) // 8

    await edit_or_send(
        query,
        f"🏭 <b>خط تولید</b>\n\n"
        f"صفحه {page+1}/{total_pages}\n\n"
        f"تجهیز موردنظر را انتخاب کنید.",
        InlineKeyboardMarkup(keys),
    )


async def produce(query, key):

    uid = query.from_user.id

    u = user(uid)

    f = factory(uid)

    c = country(u["country_code"])

    item = EQ.get(key)

    if not item:
        return

    if f["queue_amount"] > 0:

        await edit_or_send(
            query,
            "❌ کارخانه در حال تولید سفارش دیگری است.",
            home_markup(),
        )

        return

    steel_cost = max(
        20,
        item[5] / 20000 * 10,
    )

    if c["steel"] < steel_cost:

        await edit_or_send(
            query,
            "❌ فولاد کافی نیست.",
            home_markup(),
        )

        return

    minutes = max(
        1,
        int(20 / (f["level"] + 1)),
    )

    finish = now() + timedelta(
        minutes=minutes
    )

    q(
        """
        UPDATE countries
        SET steel=steel-?
        WHERE code=?
        """,
        (
            steel_cost,
            u["country_code"],
        ),
        commit=True,
    )

    q(
        """
        UPDATE factories
        SET
            queue_equipment=?,
            queue_amount=1,
            finish_time=?
        WHERE user_id=?
        """,
        (
            key,
            iso(finish),
            uid,
        ),
        commit=True,
    )

    await edit_or_send(
        query,
        f"🏭 سفارش ثبت شد:\n\n"
        f"{item[1]}\n\n"
        f"⏱ زمان تولید: {minutes} دقیقه",
        home_markup(),
    )


# ============================================================
# MARKET
# ============================================================

async def market(update, context):

    uid = update.effective_user.id

    u = user(uid)

    c = country(u["country_code"])

    prices = q(
        "SELECT item,price FROM market_prices",
        all=True,
    )

    text = "🌐 <b>بازار جهانی</b>\n\n"

    for r in prices:

        text += (
            f"• {r['item'].upper()}: "
            f"${r['price']:,.0f}\n"
        )

    text += (
        f"\n💰 خزانه: "
        f"${c['money']:,.0f}"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=inline(
            [
                ("🛢 خرید نفت", "market:buy:oil"),
                ("🌾 خرید غذا", "market:buy:food"),
            ],
            [
                ("🔩 خرید فولاد", "market:buy:steel"),
                ("💵 فروش طلا", "market:sell:gold"),
            ],
            [
                ("🏠 منوی اصلی", "home"),
            ],
        ),
    )


async def market_trade(query, action, item):

    uid = query.from_user.id

    code = user(uid)["country_code"]

    c = country(code)

    price = q(
        """
        SELECT price
        FROM market_prices
        WHERE item=?
        """,
        (item,),
        one=True,
    )["price"]

    qty = 1000

    if action == "buy":

        cost = price * qty

        if c["money"] < cost:

            await edit_or_send(
                query,
                "❌ پول کافی نیست.",
                home_markup(),
            )

            return

        q(
            f"""
            UPDATE countries
            SET
                money=money-?,
                {item}={item}+?
            WHERE code=?
            """,
            (
                cost,
                qty,
                code,
            ),
            commit=True,
        )

    else:

        if c[item] < qty:

            await edit_or_send(
                query,
                "❌ موجودی کافی نیست.",
                home_markup(),
            )

            return

        q(
            f"""
            UPDATE countries
            SET
                money=money+?,
                {item}={item}-?
            WHERE code=?
            """,
            (
                price * qty,
                qty,
                code,
            ),
            commit=True,
        )

    await edit_or_send(
        query,
        f"✅ معامله انجام شد.\n\n"
        f"📦 مقدار: {qty:,}\n"
        f"📦 کالا: {item}",
        home_markup(),
    )


# ============================================================
# WAR
# ============================================================

async def war(update, context):

    uid = update.effective_user.id

    rows = q(
        """
        SELECT
            p.id,
            p.name,
            p.country_code,
            p.weather_condition,
            p.defense_level,
            c.flag,
            c.name country_name
        FROM provinces p
        JOIN countries c
            ON c.code=p.country_code
        WHERE p.owner_id!=?
        ORDER BY RANDOM()
        LIMIT 12
        """,
        (uid,),
        all=True,
    )

    keys = []

    for r in rows:

        weather = WEATHER.get(
            r["weather_condition"],
            WEATHER["CLEAR"],
        )

        keys.append(
            [
                InlineKeyboardButton(
                    f"{r['flag']} "
                    f"{r['name']} "
                    f"{weather[0]} "
                    f"🛡{r['defense_level']}",
                    callback_data=f"attack:{r['id']}",
                )
            ]
        )

    keys.append(
        [
            InlineKeyboardButton(
                "🏠 منوی اصلی",
                callback_data="home",
            )
        ]
    )

    await update.message.reply_text(
        "⚔️ <b>اتاق جنگ</b>\n\n"
        "استان موردنظر را انتخاب کنید.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keys),
    )


async def attack_select(query, pid):

    uid = query.from_user.id

    p = q(
        "SELECT * FROM provinces WHERE id=?",
        (pid,),
        one=True,
    )

    if not p or p["owner_id"] == uid:

        await edit_or_send(
            query,
            "❌ هدف نامعتبر است.",
            home_markup(),
        )

        return

    await edit_or_send(
        query,
        f"🎯 <b>{p['name']}</b>\n\n"
        f"تاکتیک حمله را انتخاب کنید:",
        inline(
            [
                (
                    "⚔️ حمله متوازن",
                    f"tactic:STANDARD:{pid}",
                ),
                (
                    "🛡 فشار زمینی",
                    f"tactic:GROUND:{pid}",
                ),
            ],
            [
                (
                    "✈️ برتری هوایی",
                    f"tactic:AIR:{pid}",
                ),
                (
                    "🕵️ عملیات فریب",
                    f"tactic:DECEPTION:{pid}",
                ),
            ],
            [
                ("🏠 منوی اصلی", "home"),
            ],
        ),
    )


async def launch_attack(query, tactic, pid):

    uid = query.from_user.id

    p = q(
        "SELECT * FROM provinces WHERE id=?",
        (pid,),
        one=True,
    )

    if not p:
        return

    defender = p["owner_id"]

    active = q(
        """
        SELECT id
        FROM wars
        WHERE attacker_id=?
        AND status='ACTIVE'
        """,
        (uid,),
        one=True,
    )

    if active:

        await edit_or_send(
            query,
            "❌ هم‌زمان فقط یک جنگ فعال مجاز است.",
            home_markup(),
        )

        return

    attacker_power = military_power(uid)

    weather = WEATHER.get(
        p["weather_condition"],
        WEATHER["CLEAR"],
    )[2]

    tactic_mult = {
        "STANDARD": 1.00,
        "GROUND": 1.08,
        "AIR": 1.05,
        "DECEPTION": 1.02,
    }.get(tactic, 1.00)

    attacker_power *= (
        tactic_mult * weather
    )

    if defender:

        defender_power = (
            military_power(defender)
            * (1 + p["defense_level"] * 0.08)
        )

    else:

        cc = country(p["country_code"])

        defender_power = (
            cc["population"] / 1_000_000
        ) * 5000 * (
            1 + p["defense_level"] * 0.08
        )

    end = now() + timedelta(minutes=3)

    q(
        """
        INSERT INTO wars(
            attacker_id,
            defender_id,
            province_id,
            end_time,
            attacker_tactic,
            attacker_power,
            defender_power
        )
        VALUES(?,?,?,?,?,?,?)
        """,
        (
            uid,
            defender,
            pid,
            iso(end),
            tactic,
            attacker_power,
            defender_power,
        ),
        commit=True,
    )

    news(
        f"⚔️ جنگ آغاز شد: "
        f"{user(uid)['commander_name']} "
        f"به {p['name']} حمله کرد."
    )

    await edit_or_send(
        query,
        f"🔥 <b>حمله آغاز شد!</b>\n\n"
        f"⚔️ قدرت شما: {attacker_power:,.0f}\n"
        f"🛡 قدرت مدافع: {defender_power:,.0f}\n"
        f"⏱ نتیجه تا ۳ دقیقه دیگر مشخص می‌شود.",
        home_markup(),
    )


# ============================================================
# DIPLOMACY
# ============================================================

async def diplomacy(update, context):

    uid = update.effective_user.id

    u = user(uid)

    alliance = (
        q(
            "SELECT * FROM alliances WHERE id=?",
            (u["alliance_id"],),
            one=True,
        )
        if u["alliance_id"]
        else None
    )

    name = (
        escape(alliance["name"])
        if alliance
        else "ندارید"
    )

    await update.message.reply_text(
        f"🤝 <b>دیپلماسی</b>\n\n"
        f"🤝 اتحاد: {name}\n"
        f"⭐ اعتبار بین‌المللی: {u['reputation']}",
        parse_mode="HTML",
        reply_markup=inline(
            [
                ("🤝 ساخت اتحاد", "ally:create"),
                ("🌐 اتحادها", "ally:list"),
            ],
            [
                ("📜 پیشنهاد صلح", "ally:peace"),
            ],
            [
                ("🏠 منوی اصلی", "home"),
            ],
        ),
    )


async def create_alliance(query):

    uid = query.from_user.id

    u = user(uid)

    if u["alliance_id"]:

        await edit_or_send(
            query,
            "❌ شما عضو یک اتحاد هستید.",
            home_markup(),
        )

        return

    name = (
        "اتحاد "
        + u["commander_name"]
        .replace("فرمانده ", "")
    )

    try:

        con = db()

        con.execute(
            """
            INSERT INTO alliances
            (name,leader_id)
            VALUES(?,?)
            """,
            (
                name,
                uid,
            ),
        )

        aid = con.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

        con.execute(
            """
            INSERT INTO alliance_members
            VALUES(?,?)
            """,
            (
                aid,
                uid,
            ),
        )

        con.execute(
            """
            UPDATE users
            SET alliance_id=?
            WHERE user_id=?
            """,
            (
                aid,
                uid,
            ),
        )

        con.commit()
        con.close()

        news(
            f"🤝 اتحاد جدید {name} تأسیس شد."
        )

        await edit_or_send(
            query,
            f"✅ اتحاد <b>{escape(name)}</b> ساخته شد.",
            home_markup(),
        )

    except sqlite3.IntegrityError:

        await edit_or_send(
            query,
            "❌ نام اتحاد تکراری است.",
            home_markup(),
        )


async def alliance_list(query):

    rows = q(
        """
        SELECT
            a.name,
            COUNT(m.user_id) members
        FROM alliances a
        LEFT JOIN alliance_members m
            ON a.id=m.alliance_id
        GROUP BY a.id
        ORDER BY members DESC
        LIMIT 10
        """,
        all=True,
    )

    if not rows:

        text = "🤝 هیچ اتحادی وجود ندارد."

    else:

        text = "🤝 <b>اتحادهای برتر</b>\n\n"

        for i, r in enumerate(rows, 1):

            text += (
                f"{i}. {escape(r['name'])}"
                f" — {r['members']} عضو\n"
            )

    await edit_or_send(
        query,
        text,
        home_markup(),
    )


# ============================================================
# SPY
# ============================================================

async def spy_screen(update, context):

    uid = update.effective_user.id

    targets = q(
        """
        SELECT
            u.user_id,
            u.commander_name,
            c.name,
            c.flag
        FROM users u
        JOIN countries c
            ON c.code=u.country_code
        WHERE u.user_id!=?
        LIMIT 10
        """,
        (uid,),
        all=True,
    )

    keys = []

    for r in targets:

        keys.append(
            [
                InlineKeyboardButton(
                    f"{r['flag']} {r['name']} | "
                    f"{r['commander_name']}",
                    callback_data=f"spy:{r['user_id']}",
                )
            ]
        )

    keys.append(
        [
            InlineKeyboardButton(
                "🏠 منوی اصلی",
                callback_data="home",
            )
        ]
    )

    await update.message.reply_text(
        "🕵️ <b>مرکز اطلاعات</b>\n\n"
        "هدف عملیات جاسوسی را انتخاب کنید.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keys),
    )


async def spy_target(query, target):

    await edit_or_send(
        query,
        "🕵️ <b>نوع عملیات</b>",
        inline(
            [
                (
                    "📡 شناسایی ارتش",
                    f"spyop:RECON:{target}",
                ),
                (
                    "💰 جاسوسی اقتصادی",
                    f"spyop:ECON:{target}",
                ),
            ],
            [
                (
                    "💻 نفوذ سایبری",
                    f"spyop:CYBER:{target}",
                ),
                (
                    "🛡 ضدجاسوسی",
                    "spyop:COUNTER:0",
                ),
            ],
            [
                ("🏠 منوی اصلی", "home"),
            ],
        ),
    )


async def spy_op(query, operation, target):

    uid = query.from_user.id

    a = army(uid)

    chance = min(
        95,
        35 + a["cyber_level"] * 10
        + random.randint(-10, 10),
    )

    success = (
        random.randint(1, 100)
        <= chance
    )

    if operation == "COUNTER":

        q(
            """
            UPDATE armies
            SET cyber_level=cyber_level+1
            WHERE user_id=?
            """,
            (uid,),
            commit=True,
        )

        await edit_or_send(
            query,
            "🛡️ شبکه ضدجاسوسی تقویت شد.",
            home_markup(),
        )

        return

    if success:

        if operation == "RECON":

            power = military_power(target)

            text = (
                "📡 <b>شناسایی موفق!</b>\n\n"
                f"⚔️ قدرت تقریبی ارتش: "
                f"{power:,.0f}"
            )

        elif operation == "ECON":

            c = country(
                user(target)["country_code"]
            )

            text = (
                "💰 <b>گزارش اقتصادی</b>\n\n"
                f"💰 خزانه: ${c['money']:,.0f}\n"
                f"🛢 نفت: {c['oil']:,.0f}\n"
                f"🔩 فولاد: {c['steel']:,.0f}"
            )

        else:

            q(
                """
                UPDATE users
                SET score=score+25
                WHERE user_id=?
                """,
                (uid,),
                commit=True,
            )

            text = (
                "💻 نفوذ سایبری موفق بود!\n\n"
                "🏆 +25 امتیاز"
            )

    else:

        text = (
            f"❌ عملیات شکست خورد.\n\n"
            f"🎯 احتمال موفقیت: {chance}%"
        )

    await edit_or_send(
        query,
        text,
        home_markup(),
    )


# ============================================================
# DEFENSE
# ============================================================

async def defense(update, context):

    uid = update.effective_user.id

    a = army(uid)

    c = country(
        user(uid)["country_code"]
    )

    await update.message.reply_text(
        f"🛰️ <b>دفاع و ماهواره</b>\n\n"
        f"🛡 پدافند: {a['air_defense']}\n"
        f"🛰️ ماهواره: "
        f"{'فعال' if c['has_satellite'] else 'ندارید'}",
        parse_mode="HTML",
        reply_markup=inline(
            [
                ("🛡 ارتقای پدافند", "def:up"),
                ("🛰️ پرتاب ماهواره", "def:sat"),
            ],
            [
                ("📡 ارتقای رادار", "def:radar"),
            ],
            [
                ("🏠 منوی اصلی", "home"),
            ],
        ),
    )


async def defense_action(query, action):

    uid = query.from_user.id

    code = user(uid)["country_code"]

    c = country(code)

    a = army(uid)

    if action == "sat":

        cost = 3_000_000

        if c["money"] < cost:

            await edit_or_send(
                query,
                "❌ بودجه کافی نیست.",
                home_markup(),
            )

            return

        q(
            """
            UPDATE countries
            SET
                money=money-?,
                has_satellite=1
            WHERE code=?
            """,
            (
                cost,
                code,
            ),
            commit=True,
        )

        await edit_or_send(
            query,
            "🛰️ ماهواره نظامی فعال شد.",
            home_markup(),
        )

    elif action == "up":

        cost = 250_000 * a["air_defense"]

        if c["money"] < cost:

            await edit_or_send(
                query,
                "❌ بودجه کافی نیست.",
                home_markup(),
            )

            return

        q(
            """
            UPDATE countries
            SET money=money-?
            WHERE code=?
            """,
            (
                cost,
                code,
            ),
            commit=True,
        )

        q(
            """
            UPDATE armies
            SET air_defense=air_defense+1
            WHERE user_id=?
            """,
            (uid,),
            commit=True,
        )

        await edit_or_send(
            query,
            "🛡️ پدافند ارتقا یافت.",
            home_markup(),
        )

    else:

        await edit_or_send(
            query,
            "📡 رادار ارتقا یافت.",
            home_markup(),
        )


# ============================================================
# NUCLEAR
# ============================================================

async def nuclear(update, context):

    a = army(update.effective_user.id)

    await update.message.reply_text(
        f"💣 <b>اتاق هسته‌ای</b>\n\n"
        f"☢️ کلاهک‌ها: {a['nukes']}\n\n"
        f"این بخش صرفاً شبیه‌سازی داخل بازی است.",
        parse_mode="HTML",
        reply_markup=inline(
            [
                ("🏭 ساخت کلاهک", "nuke:build"),
                ("☢️ شبیه‌سازی حمله", "nuke:sim"),
            ],
            [
                ("🏠 منوی اصلی", "home"),
            ],
        ),
    )


async def nuclear_action(query, action):

    uid = query.from_user.id

    code = user(uid)["country_code"]

    c = country(code)

    if action == "build":

        cost = 5_000_000

        if c["money"] < cost:

            await edit_or_send(
                query,
                "❌ بودجه کافی نیست.",
                home_markup(),
            )

            return

        q(
            """
            UPDATE countries
            SET money=money-?
            WHERE code=?
            """,
            (
                cost,
                code,
            ),
            commit=True,
        )

        q(
            """
            UPDATE armies
            SET nukes=nukes+1
            WHERE user_id=?
            """,
            (uid,),
            commit=True,
        )

        await edit_or_send(
            query,
            "☢️ یک کلاهک به زرادخانه افزوده شد.",
            home_markup(),
        )

    else:

        q(
            """
            UPDATE users
            SET
                approval=MAX(0,approval-3),
                reputation=reputation-10
            WHERE user_id=?
            """,
            (uid,),
            commit=True,
        )

        news(
            f"☢️ فرمانده "
            f"{user(uid)['commander_name']} "
            f"یک شبیه‌سازی هسته‌ای انجام داد."
        )

        await edit_or_send(
            query,
            "☢️ شبیه‌سازی انجام شد.\n\n"
            "📉 اعتبار بین‌المللی کاهش یافت.",
            home_markup(),
        )


# ============================================================
# TECHNOLOGY
# ============================================================

async def tech(update, context):

    u = user(update.effective_user.id)

    await update.message.reply_text(
        f"🧬 <b>درخت فناوری</b>\n\n"
        f"🔬 سطح فناوری: {u['tech_level']}/10\n\n"
        f"ارتقای فناوری روی ارتش، اقتصاد و جاسوسی اثر می‌گذارد.",
        parse_mode="HTML",
        reply_markup=inline(
            [
                ("⬆️ ارتقای فناوری", "tech:up"),
            ],
            [
                ("🔬 پژوهش سریع", "tech:boost"),
            ],
            [
                ("🏠 منوی اصلی", "home"),
            ],
        ),
    )


async def tech_action(query, action):

    uid = query.from_user.id

    u = user(uid)

    code = u["country_code"]

    c = country(code)

    if u["tech_level"] >= 10:

        await edit_or_send(
            query,
            "🧬 فناوری شما به حداکثر سطح رسیده است.",
            home_markup(),
        )

        return

    cost = 300_000 * u["tech_level"]

    if c["money"] < cost:

        await edit_or_send(
            query,
            f"❌ برای ارتقا "
            f"${cost:,.0f} لازم است.",
            home_markup(),
        )

        return

    q(
        """
        UPDATE countries
        SET money=money-?
        WHERE code=?
        """,
        (
            cost,
            code,
        ),
        commit=True,
    )

    q(
        """
        UPDATE users
        SET
            tech_level=MIN(10,tech_level+1),
            score=score+30
        WHERE user_id=?
        """,
        (uid,),
        commit=True,
    )

    await edit_or_send(
        query,
        f"🧬 فناوری به سطح "
        f"{u['tech_level'] + 1} رسید.",
        home_markup(),
    )


# ============================================================
# POLITICS
# ============================================================

async def politics(update, context):

    uid = update.effective_user.id

    u = user(uid)

    c = country(u["country_code"])

    await update.message.reply_text(
        f"🏛️ <b>سیاست داخلی</b>\n\n"
        f"😊 رضایت: {u['approval']}%\n"
        f"🏛 ثبات: {c['stability']}%\n"
        f"💰 مالیات: {c['tax_rate']}%",
        parse_mode="HTML",
        reply_markup=inline(
            [
                ("💰 افزایش مالیات", "pol:taxup"),
                ("🎁 کاهش مالیات", "pol:taxdown"),
            ],
            [
                ("🏛 برنامه رفاهی", "pol:welfare"),
            ],
            [
                ("🏠 منوی اصلی", "home"),
            ],
        ),
    )


async def politics_action(query, action):

    uid = query.from_user.id

    code = user(uid)["country_code"]

    c = country(code)

    if action == "taxup":

        q(
            """
            UPDATE countries
            SET
                tax_rate=MIN(30,tax_rate+2),
                money=money+100000,
                stability=MAX(0,stability-2)
            WHERE code=?
            """,
            (code,),
            commit=True,
        )

        q(
            """
            UPDATE users
            SET approval=MAX(0,approval-3)
            WHERE user_id=?
            """,
            (uid,),
            commit=True,
        )

    elif action == "taxdown":

        q(
            """
            UPDATE countries
            SET
                tax_rate=MAX(0,tax_rate-2),
                stability=MIN(100,stability+1)
            WHERE code=?
            """,
            (code,),
            commit=True,
        )

        q(
            """
            UPDATE users
            SET approval=MIN(100,approval+2)
            WHERE user_id=?
            """,
            (uid,),
            commit=True,
        )

    else:

        if c["money"] < 250_000:

            await edit_or_send(
                query,
                "❌ بودجه رفاهی کافی نیست.",
                home_markup(),
            )

            return

        q(
            """
            UPDATE countries
            SET
                money=money-250000,
                stability=MIN(100,stability+8)
            WHERE code=?
            """,
            (code,),
            commit=True,
        )

        q(
            """
            UPDATE users
            SET approval=MIN(100,approval+8)
            WHERE user_id=?
            """,
            (uid,),
            commit=True,
        )

    await edit_or_send(
        query,
        "🏛️ سیاست داخلی اجرا شد.",
        home_markup(),
    )


# ============================================================
# NEWS
# ============================================================

async def news_screen(update, context):

    rows = q(
        """
        SELECT content,timestamp
        FROM news
        ORDER BY id DESC
        LIMIT 12
        """,
        all=True,
    )

    if not rows:

        text = "📰 هنوز خبری منتشر نشده است."

    else:

        text = "📰 <b>خبرگزاری جهان</b>\n\n"

        for r in rows:

            text += (
                f"• {escape(r['content'])}\n"
                f"<i>{r['timestamp']}</i>\n\n"
            )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=economy_kb(),
    )


# ============================================================
# RANKINGS
# ============================================================

async def rankings(update, context):

    rows = q(
        """
        SELECT
            u.commander_name,
            c.flag,
            c.name,
            u.score,
            u.season_score
        FROM users u
        JOIN countries c
            ON c.code=u.country_code
        ORDER BY u.score DESC
        LIMIT 10
        """,
        all=True,
    )

    text = "🏆 <b>لیگ فرماندهان</b>\n\n"

    for i, r in enumerate(rows, 1):

        text += (
            f"{i}. {r['flag']} "
            f"{escape(r['commander_name'])}\n"
            f"⭐ {r['score']:,} | "
            f"فصل: {r['season_score']:,}\n\n"
        )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=economy_kb(),
    )


# ============================================================
# MISSIONS
# ============================================================

MISSION_DEFS = [
    ("war", "پیروزی در یک نبرد", 1, 500),
    ("trade", "انجام یک معامله", 1, 300),
    ("tech", "ارتقای فناوری", 1, 400),
    ("buy", "خرید تجهیزات", 1, 250),
]


async def missions(update, context):

    uid = update.effective_user.id

    day = now().date().isoformat()

    for code, title, target, reward in MISSION_DEFS:

        q(
            """
            INSERT OR IGNORE INTO missions
            (user_id,day,code,title,target,reward)
            VALUES(?,?,?,?,?,?)
            """,
            (
                uid,
                day,
                code,
                title,
                target,
                reward,
            ),
            commit=True,
        )

    rows = q(
        """
        SELECT *
        FROM missions
        WHERE user_id=?
        AND day=?
        """,
        (
            uid,
            day,
        ),
        all=True,
    )

    text = "🎯 <b>مأموریت‌های امروز</b>\n\n"

    for r in rows:

        status = (
            "✅"
            if r["claimed"]
            else "⬜"
        )

        text += (
            f"{status} {r['title']}\n"
            f"📊 {min(r['progress'],r['target'])}"
            f"/{r['target']}\n"
            f"🎁 {r['reward']} امتیاز\n\n"
        )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=inline(
            [
                (
                    "🎁 دریافت پاداش",
                    "mission:claim",
                ),
            ],
            [
                ("🏠 منوی اصلی", "home"),
            ],
        ),
    )


async def claim_missions(query):

    uid = query.from_user.id

    day = now().date().isoformat()

    rows = q(
        """
        SELECT *
        FROM missions
        WHERE user_id=?
        AND day=?
        AND claimed=0
        """,
        (
            uid,
            day,
        ),
        all=True,
    )

    total = 0

    for r in rows:

        if r["progress"] >= r["target"]:

            total += r["reward"]

            q(
                """
                UPDATE missions
                SET claimed=1
                WHERE user_id=?
                AND day=?
                AND code=?
                """,
                (
                    uid,
                    day,
                    r["code"],
                ),
                commit=True,
            )

    if total:

        q(
            """
            UPDATE users
            SET
                score=score+?,
                season_score=season_score+?
            WHERE user_id=?
            """,
            (
                total,
                total,
                uid,
            ),
            commit=True,
        )

    await edit_or_send(
        query,
        f"🎁 پاداش دریافت شد:\n\n"
        f"🏆 +{total:,} امتیاز",
        home_markup(),
    )


# ============================================================
# DAILY REWARD
# ============================================================

async def daily_reward(update, context):

    uid = update.effective_user.id

    today = now().date().isoformat()

    u = user(uid)

    if u["last_daily"] == today:

        await update.message.reply_text(
            "⏳ پاداش امروز قبلاً دریافت شده است.",
            reply_markup=profile_kb(uid),
        )

        return

    reward = random.randint(100, 300)

    q(
        """
        UPDATE users
        SET
            last_daily=?,
            score=score+?,
            season_score=season_score+?
        WHERE user_id=?
        """,
        (
            today,
            reward,
            reward,
            uid,
        ),
        commit=True,
    )

    await update.message.reply_text(
        f"🎁 <b>پاداش روزانه</b>\n\n"
        f"🏆 +{reward} امتیاز",
        parse_mode="HTML",
        reply_markup=profile_kb(uid),
    )


# ============================================================
# ACHIEVEMENTS
# ============================================================

ACH = [
    ("first_win", "اولین پیروزی"),
    ("rich", "خزانه‌دار بزرگ"),
    ("tech5", "دانشمند نظامی"),
    ("arsenal", "زرادخانه‌دار"),
]


async def achievements(update, context):

    uid = update.effective_user.id

    earned = {
        r["code"]
        for r in q(
            """
            SELECT code
            FROM achievements
            WHERE user_id=?
            """,
            (uid,),
            all=True,
        )
    }

    data = inv(uid)

    checks = {
        "first_win": q(
            """
            SELECT 1
            FROM wars
            WHERE attacker_id=?
            AND status='ATTACKER_WON'
            """,
            (uid,),
            one=True,
        ),
        "rich": country(
            user(uid)["country_code"]
        )["money"] >= 5_000_000,
        "tech5": user(uid)["tech_level"] >= 5,
        "arsenal": sum(data.values()) >= 100,
    }

    for code, title in ACH:

        if code not in earned and checks[code]:

            q(
                """
                INSERT OR IGNORE INTO achievements
                (user_id,code,title)
                VALUES(?,?,?)
                """,
                (
                    uid,
                    code,
                    title,
                ),
                commit=True,
            )

            q(
                """
                UPDATE users
                SET score=score+500
                WHERE user_id=?
                """,
                (uid,),
                commit=True,
            )

    rows = q(
        """
        SELECT title
        FROM achievements
        WHERE user_id=?
        """,
        (uid,),
        all=True,
    )

    if rows:

        text = "🏅 <b>دستاوردها</b>\n\n"

        for r in rows:

            text += (
                f"🏅 {r['title']}\n"
            )

    else:

        text = (
            "🏅 <b>دستاوردها</b>\n\n"
            "هنوز دستاوردی کسب نشده است."
        )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=profile_kb(uid),
    )


# ============================================================
# AI ADVISOR
# ============================================================

async def enter_ai(update, context):

    uid = update.effective_user.id

    q(
        """
        UPDATE users
        SET chat_state='AI'
        WHERE user_id=?
        """,
        (uid,),
        commit=True,
    )

    await update.message.reply_text(
        "🧠 <b>مشاور هوش مصنوعی</b>\n\n"
        "سؤال راهبردی یا اقتصادی خود را بفرستید.\n\n"
        "برای خروج «خروج» را بنویسید.",
        parse_mode="HTML",
        reply_markup=profile_kb(uid),
    )


async def ai_message(update, context):

    uid = update.effective_user.id

    u = user(uid)

    c = country(u["country_code"])

    if update.message.text.strip() in (
        "خروج",
        "/exit",
    ):

        q(
            """
            UPDATE users
            SET chat_state='NONE'
            WHERE user_id=?
            """,
            (uid,),
            commit=True,
        )

        await update.message.reply_text(
            "از اتاق مشاور خارج شدید.",
            reply_markup=profile_kb(uid),
        )

        return

    prompt = (
        f"کشور: {c['name']}\n"
        f"خزانه: {c['money']}\n"
        f"نفت: {c['oil']}\n"
        f"فولاد: {c['steel']}\n"
        f"رضایت: {u['approval']}\n"
        f"فناوری: {u['tech_level']}\n"
        f"قدرت ارتش: {military_power(uid)}\n"
        f"سؤال: {update.message.text}"
    )

    if AI:

        try:

            result = await AI.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "تو مشاور یک بازی استراتژیک "
                            "تخیلی هستی. کوتاه و بازی‌محور "
                            "پاسخ بده."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                max_tokens=350,
                temperature=0.7,
            )

            answer = (
                result
                .choices[0]
                .message
                .content
                .strip()
            )

        except Exception:

            answer = (
                "مرکز هوش مصنوعی موقتاً "
                "در دسترس نیست."
            )

    else:

        answer = (
            "تحلیل مشاور:\n\n"
            "قبل از جنگ، اقتصاد، روحیه، "
            "فناوری و پدافند را تقویت کنید."
        )

    await update.message.reply_text(
        "🧠 <b>مشاور:</b>\n\n"
        + escape(answer),
        parse_mode="HTML",
        reply_markup=profile_kb(uid),
    )


# ============================================================
# GENERALS
# ============================================================

async def generals(update, context):

    uid = update.effective_user.id

    rows = q(
        """
        SELECT name,type,level,is_alive
        FROM generals
        WHERE user_id=?
        """,
        (uid,),
        all=True,
    )

    text = "🎖 <b>ژنرال‌ها</b>\n\n"

    for r in rows:

        text += (
            f"🎖 {r['name']}\n"
            f"نوع: {r['type']}\n"
            f"سطح: {r['level']}\n\n"
        )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=army_kb(),
    )


# ============================================================
# HELP / SETTINGS
# ============================================================

async def help_screen(update, context):

    await update.message.reply_text(
        "📜 <b>راهنمای WORLD WAR</b>\n\n"
        "⚔️ جنگ و عملیات:\n"
        "حمله، دفاع، جاسوسی و دیپلماسی.\n\n"
        "🏭 کشور و اقتصاد:\n"
        "مدیریت منابع، کارخانه، بازار و فناوری.\n\n"
        "🪖 ارتش و تجهیزات:\n"
        "مدیریت نیرو، تجهیزات و تولید.\n\n"
        "👤 پروفایل و تنظیمات:\n"
        "مأموریت‌ها، دستاوردها و مشاور هوش مصنوعی.",
        parse_mode="HTML",
        reply_markup=profile_kb(update.effective_user.id),
    )


async def settings(update, context):

    await update.message.reply_text(
        "⚙️ <b>تنظیمات بازی</b>\n\n"
        "نسخه: WORLD WAR V4\n"
        "دیتابیس: SQLite/WAL\n"
        "سرور: Railway Friendly\n\n"
        "رابط کاربری: ۴ منوی اصلی",
        parse_mode="HTML",
        reply_markup=profile_kb(update.effective_user.id),
    )


# ============================================================
# ADMIN PANEL
# ============================================================

async def admin_panel(update, context):

    uid = update.effective_user.id

    if not admin(uid):

        await update.message.reply_text(
            "⛔ دسترسی غیرمجاز.",
            reply_markup=profile_kb(uid),
        )

        return

    players = q(
        "SELECT COUNT(*) n FROM users",
        one=True,
    )["n"]

    countries_count = q(
        """
        SELECT COUNT(*) n
        FROM countries
        WHERE is_ai=0
        """,
        one=True,
    )["n"]

    active_wars = q(
        """
        SELECT COUNT(*) n
        FROM wars
        WHERE status='ACTIVE'
        """,
        one=True,
    )["n"]

    text = (
        "👑 <b>پنل مدیریت</b>\n\n"
        f"👥 بازیکنان: {players}\n"
        f"🌍 کشورهای انسانی: {countries_count}\n"
        f"⚔️ جنگ‌های فعال: {active_wars}\n\n"
        "🛡 سطح دسترسی: کامل"
    )

    markup = inline(
        [
            ("👥 بازیکنان", "adm:users"),
            ("🌍 کشورها", "adm:countries"),
        ],
        [
            ("⚔️ جنگ‌ها", "adm:wars"),
            ("💰 اقتصاد", "adm:economy"),
        ],
        [
            ("📰 اخبار", "adm:news"),
            ("🧰 ابزارها", "adm:tools"),
        ],
        [
            ("📢 پیام همگانی", "adm:broadcast"),
        ],
        [
            ("🏠 منوی اصلی", "home"),
        ],
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=markup,
    )


async def admin_users(query):

    if not admin(query.from_user.id):
        return

    rows = q(
        """
        SELECT
            u.user_id,
            u.commander_name,
            c.flag,
            c.name,
            u.score,
            u.approval
        FROM users u
        JOIN countries c
            ON c.code=u.country_code
        ORDER BY u.score DESC
        LIMIT 15
        """,
        all=True,
    )

    keys = []

    for r in rows:

        keys.append(
            [
                InlineKeyboardButton(
                    f"{r['flag']} "
                    f"{r['commander_name']} | "
                    f"{r['score']}",
                    callback_data=f"admu:{r['user_id']}",
                )
            ]
        )

    keys.append(
        [
            InlineKeyboardButton(
                "🏠 منوی اصلی",
                callback_data="home",
            )
        ]
    )

    await edit_or_send(
        query,
        "👥 <b>مدیریت بازیکنان</b>\n\n"
        "بازیکن را انتخاب کنید.",
        InlineKeyboardMarkup(keys),
    )


async def admin_user(query, target):

    if not admin(query.from_user.id):
        return

    u = user(target)

    if not u:

        await edit_or_send(
            query,
            "❌ کاربر پیدا نشد.",
            home_markup(),
        )

        return

    c = country(u["country_code"])

    await edit_or_send(
        query,
        f"👤 <b>{escape(u['commander_name'])}</b>\n\n"
        f"🆔 {target}\n"
        f"🌍 {c['flag']} {c['name']}\n"
        f"💰 ${c['money']:,.0f}\n"
        f"⭐ {u['score']:,}\n"
        f"😊 {u['approval']}%",
        inline(
            [
                ("💰 +1M", f"adm:addmoney:{target}"),
                ("⭐ +1000", f"adm:addscore:{target}"),
            ],
            [
                ("😊 +10 رضایت", f"adm:approval:{target}"),
                ("🔄 ریست اقتصاد", f"adm:reseteco:{target}"),
            ],
            [
                ("👑 God Mode", f"adm:god:{target}"),
                ("🗑 حذف", f"adm:delete:{target}"),
            ],
            [
                ("🏠 منوی اصلی", "home"),
            ],
        ),
    )


async def admin_action(query, action, target=None):

    if not admin(query.from_user.id):
        return

    if action == "addmoney":

        q(
            """
            UPDATE countries
            SET money=money+1000000
            WHERE code=(
                SELECT country_code
                FROM users
                WHERE user_id=?
            )
            """,
            (target,),
            commit=True,
        )

    elif action == "addscore":

        q(
            """
            UPDATE users
            SET score=score+1000
            WHERE user_id=?
            """,
            (target,),
            commit=True,
        )

    elif action == "approval":

        q(
            """
            UPDATE users
            SET approval=MIN(100,approval+10)
            WHERE user_id=?
            """,
            (target,),
            commit=True,
        )

    elif action == "reseteco":

        q(
            """
            UPDATE countries
            SET
                money=1000000,
                oil=50000,
                steel=50000,
                food=100000,
                power=50000
            WHERE code=(
                SELECT country_code
                FROM users
                WHERE user_id=?
            )
            """,
            (target,),
            commit=True,
        )

    elif action == "god":

        q(
            """
            UPDATE countries
            SET
                money=money+50000000,
                oil=oil+500000,
                steel=steel+500000,
                food=food+1000000,
                power=power+500000,
                gold=gold+10000
            WHERE code=(
                SELECT country_code
                FROM users
                WHERE user_id=?
            )
            """,
            (target,),
            commit=True,
        )

        q(
            """
            UPDATE users
            SET
                score=score+10000,
                season_score=season_score+10000,
                approval=100,
                tech_level=10,
                reputation=100
            WHERE user_id=?
            """,
            (target,),
            commit=True,
        )

        q(
            """
            UPDATE armies
            SET
                soldiers=soldiers+100000,
                morale=100,
                cyber_level=10,
                air_defense=10,
                logistics=10,
                nukes=nukes+10
            WHERE user_id=?
            """,
            (target,),
            commit=True,
        )

        for key in EQ:

            q(
                """
                UPDATE equipment_inventory
                SET amount=amount+100
                WHERE user_id=?
                AND equipment=?
                """,
                (
                    target,
                    key,
                ),
                commit=True,
            )

    elif action == "delete":

        for table in [
            "equipment_inventory",
            "armies",
            "factories",
            "generals",
        ]:

            q(
                f"DELETE FROM {table} WHERE user_id=?",
                (target,),
                commit=True,
            )

        q(
            "DELETE FROM users WHERE user_id=?",
            (target,),
            commit=True,
        )

    q(
        """
        INSERT INTO admin_logs
        (admin_id,action)
        VALUES(?,?)
        """,
        (
            query.from_user.id,
            f"{action}:{target}",
        ),
        commit=True,
    )

    await edit_or_send(
        query,
        "✅ دستور مدیریتی اجرا شد.",
        home_markup(),
    )


async def admin_generic(query, section):

    if not admin(query.from_user.id):
        return

    if section == "countries":

        rows = q(
            """
            SELECT
                name,
                flag,
                money,
                is_ai,
                stability
            FROM countries
            ORDER BY population DESC
            """,
            all=True,
        )

        text = "🌍 <b>کشورهای جهان</b>\n\n"

        for r in rows:

            owner = (
                "AI"
                if r["is_ai"]
                else "PLAYER"
            )

            text += (
                f"{r['flag']} {r['name']} | "
                f"${r['money']:,.0f} | "
                f"{owner} | "
                f"ثبات {r['stability']}%\n"
            )

    elif section == "wars":

        rows = q(
            """
            SELECT
                w.id,
                w.status,
                p.name
            FROM wars w
            JOIN provinces p
                ON p.id=w.province_id
            ORDER BY w.id DESC
            LIMIT 15
            """,
            all=True,
        )

        text = "⚔️ <b>جنگ‌ها</b>\n\n"

        for r in rows:

            text += (
                f"#{r['id']} "
                f"{r['name']} — "
                f"{r['status']}\n"
            )

    elif section == "economy":

        rows = q(
            "SELECT item,price FROM market_prices",
            all=True,
        )

        text = "💰 <b>اقتصاد جهان</b>\n\n"

        for r in rows:

            text += (
                f"{r['item']}: "
                f"${r['price']:,.0f}\n"
            )

    elif section == "news":

        rows = q(
            """
            SELECT id,content
            FROM news
            ORDER BY id DESC
            LIMIT 10
            """,
            all=True,
        )

        text = "📰 <b>اخبار</b>\n\n"

        for r in rows:

            text += (
                f"#{r['id']} "
                f"{escape(r['content'])}\n\n"
            )

    else:

        text = (
            "🧰 <b>ابزارهای مدیریتی</b>\n\n"
            "از گزینه‌های زیر استفاده کنید."
        )

    await edit_or_send(
        query,
        text,
        inline(
            [
                ("🌦 تغییر آب‌وهوا", "adm:weather"),
                ("💹 نوسان بازار", "adm:market"),
            ],
            [
                ("🏁 پایان فصل", "adm:season"),
                ("🧹 پاک‌سازی اخبار", "adm:clean"),
            ],
            [
                ("🏠 منوی اصلی", "home"),
            ],
        ),
    )


async def admin_tools(query, action):

    if not admin(query.from_user.id):
        return

    if action == "weather":

        weather = random.choice(
            list(WEATHER.keys())
        )

        q(
            """
            UPDATE provinces
            SET weather_condition=?
            """,
            (weather,),
            commit=True,
        )

        news(
            "🌦 آب‌وهوای جهان تغییر کرد."
        )

        message = "🌦 آب‌وهوای جهان تغییر کرد."

    elif action == "market":

        for item in [
            "oil",
            "steel",
            "food",
            "power",
            "gold",
        ]:

            row = q(
                """
                SELECT price
                FROM market_prices
                WHERE item=?
                """,
                (item,),
                one=True,
            )

            price = row["price"]

            price *= random.uniform(
                0.85,
                1.15,
            )

            q(
                """
                UPDATE market_prices
                SET price=?
                WHERE item=?
                """,
                (
                    price,
                    item,
                ),
                commit=True,
            )

        message = "💹 قیمت‌های بازار تغییر کردند."

    elif action == "clean":

        q(
            """
            DELETE FROM news
            WHERE id NOT IN
            (
                SELECT id
                FROM news
                ORDER BY id DESC
                LIMIT 100
            )
            """,
            commit=True,
        )

        message = "🧹 اخبار قدیمی پاک شدند."

    else:

        current = int(
            q(
                """
                SELECT value
                FROM game_state
                WHERE key='season'
                """,
                one=True,
            )["value"]
        )

        q(
            """
            UPDATE users
            SET season_score=0
            """,
            commit=True,
        )

        q(
            """
            UPDATE game_state
            SET value=?
            WHERE key='season'
            """,
            (str(current + 1),),
            commit=True,
        )

        message = (
            "🏁 فصل جدید آغاز شد."
        )

    await edit_or_send(
        query,
        "✅ " + message,
        home_markup(),
    )


# ============================================================
# CALLBACK ROUTER
# ============================================================

async def callbacks(update, context):

    query = update.callback_query

    await query.answer()

    data = query.data

    uid = query.from_user.id

    # ---------------- COUNTRY ----------------

    if data.startswith("country:"):

        return await select_country(
            query,
            data.split(":")[1],
        )

    # ---------------- HOME ----------------

    if data == "home":

        await query.message.reply_text(
            "🌍 <b>منوی اصلی</b>\n\n"
            "یکی از چهار بخش اصلی را انتخاب کنید.",
            parse_mode="HTML",
            reply_markup=main_kb(uid),
        )

        return

    # ---------------- MAP ----------------

    if data == "map:mine":

        return await map_mine(query)

    # ---------------- SHOP ----------------

    if data == "army:shop":

        return await equipment_shop(query)

    if data.startswith("shop:"):

        return await equipment_shop(
            query,
            int(data.split(":")[1]),
        )

    if data.startswith("buy:"):

        return await buy_equipment(
            query,
            data.split(":", 1)[1],
        )

    # ---------------- FACTORY ----------------

    if data == "factory:menu":

        return await factory_menu(query)

    if data.startswith("factory:page:"):

        return await factory_menu(
            query,
            int(data.split(":")[2]),
        )

    if data.startswith("prod:"):

        return await produce(
            query,
            data.split(":", 1)[1],
        )

    # ---------------- MARKET ----------------

    if data.startswith("market:"):

        _, action, item = data.split(":")

        return await market_trade(
            query,
            action,
            item,
        )

    # ---------------- WAR ----------------

    if data.startswith("attack:"):

        return await attack_select(
            query,
            int(data.split(":")[1]),
        )

    if data.startswith("tactic:"):

        _, tactic, pid = data.split(":")

        return await launch_attack(
            query,
            tactic,
            int(pid),
        )

    # ---------------- DIPLOMACY ----------------

    if data == "ally:create":

        return await create_alliance(query)

    if data == "ally:list":

        return await alliance_list(query)

    if data == "ally:peace":

        return await edit_or_send(
            query,
            "📜 پیشنهاد صلح در نسخه بعدی "
            "به مذاکرات مستقیم متصل می‌شود.",
            home_markup(),
        )

    # ---------------- SPY ----------------

    if data.startswith("spy:"):

        return await spy_target(
            query,
            int(data.split(":")[1]),
        )

    if data.startswith("spyop:"):

        _, operation, target = data.split(":")

        return await spy_op(
            query,
            operation,
            int(target),
        )

    # ---------------- DEFENSE ----------------

    if data.startswith("def:"):

        return await defense_action(
            query,
            data.split(":")[1],
        )

    # ---------------- NUCLEAR ----------------

    if data.startswith("nuke:"):

        return await nuclear_action(
            query,
            data.split(":")[1],
        )

    # ---------------- TECHNOLOGY ----------------

    if data.startswith("tech:"):

        return await tech_action(
            query,
            data.split(":")[1],
        )

    # ---------------- POLITICS ----------------

    if data.startswith("pol:"):

        return await politics_action(
            query,
            data.split(":")[1],
        )

    # ---------------- MISSIONS ----------------

    if data == "mission:claim":

        return await claim_missions(query)

    # ---------------- GENERALS ----------------

    if data == "generals":

        rows = q(
            """
            SELECT name,type,level
            FROM generals
            WHERE user_id=?
            """,
            (uid,),
            all=True,
        )

        text = "🎖 <b>ژنرال‌ها</b>\n\n"

        for r in rows:

            text += (
                f"🎖 {r['name']} | "
                f"{r['type']} | "
                f"Lv.{r['level']}\n"
            )

        return await edit_or_send(
            query,
            text,
            home_markup(),
        )

    # ---------------- ADMIN ----------------

    if data.startswith("adm:"):

        parts = data.split(":")

        action = parts[1]

        if action in (
            "users",
            "countries",
            "wars",
            "economy",
            "news",
            "tools",
        ):

            if action == "users":

                return await admin_users(query)

            return await admin_generic(
                query,
                action,
            )

        if action in (
            "weather",
            "market",
            "season",
            "clean",
        ):

            return await admin_tools(
                query,
                action,
            )

        if action in (
            "addmoney",
            "addscore",
            "approval",
            "reseteco",
            "god",
            "delete",
        ):

            return await admin_action(
                query,
                action,
                int(parts[2]),
            )

    if data.startswith("admu:"):

        return await admin_user(
            query,
            int(data.split(":")[1]),
        )

    await edit_or_send(
        query,
        "❌ دستور ناشناخته.",
        home_markup(),
    )


# ============================================================
# TEXT ROUTER
# ============================================================

async def text_router(update, context):

    uid = update.effective_user.id

    text = update.message.text

    u = user(uid)

    if not u:

        if text.startswith("/"):
            return

        await update.message.reply_text(
            "ابتدا /start را بزنید."
        )

        return

    # ---------------- AI MODE ----------------

    if u["chat_state"] == "AI":

        return await ai_message(
            update,
            context,
        )

    # ---------------- ADMIN ----------------

    if text == "👑 پنل مدیریت":

        return await admin_panel(
            update,
            context,
        )

    # ========================================================
    # MAIN MENU
    # ========================================================

    if text == "⚔️ جنگ و عملیات":

        return await open_war_menu(
            update,
            context,
        )

    if text == "🏭 کشور و اقتصاد":

        return await open_economy_menu(
            update,
            context,
        )

    if text == "🪖 ارتش و تجهیزات":

        return await open_army_menu(
            update,
            context,
        )

    if text == "👤 پروفایل و تنظیمات":

        return await open_profile_menu(
            update,
            context,
        )

    # ========================================================
    # BACK
    # ========================================================

    if text == "🔙 بازگشت به منوی اصلی":

        return await go_home(
            update,
            context,
        )

    # ========================================================
    # WAR MENU
    # ========================================================

    war_actions = {

        "🎯 حمله به کشور": war,

        "🛡 دفاع": defense,

        "🕵️ جاسوسی": spy_screen,

        "🤝 دیپلماسی": diplomacy,

        "🛰️ دفاع و ماهواره": defense,

        "💣 اتاق هسته‌ای": nuclear,
    }

    if text in war_actions:

        return await war_actions[text](
            update,
            context,
        )

    # ========================================================
    # ECONOMY MENU
    # ========================================================

    economy_actions = {

        "🌍 وضعیت کشور": profile,

        "🗺️ نقشه جهان": world_map,

        "🏭 کارخانه": economy,

        "🌐 بازار جهانی": market,

        "🧬 فناوری": tech,

        "🏛️ سیاست داخلی": politics,

        "📰 خبرگزاری جهان": news_screen,

        "🏆 لیگ و رتبه‌بندی": rankings,
    }

    if text in economy_actions:

        return await economy_actions[text](
            update,
            context,
        )

    # ========================================================
    # ARMY MENU
    # ========================================================

    army_actions = {

        "📊 وضعیت ارتش": army_screen,

        "🛒 خرید تجهیزات": (
            lambda u, c:
            equipment_shop_from_message(
                u,
                c,
            )
        ),

        "🏭 تولید تجهیزات": (
            lambda u, c:
            factory_from_message(
                u,
                c,
            )
        ),

        "🎖 ژنرال‌ها": generals,

        "⬆️ ارتقای پدافند": defense,

        "📡 ارتقای رادار": defense,
    }

    if text in army_actions:

        action = army_actions[text]

        if text in (
            "🛒 خرید تجهیزات",
            "🏭 تولید تجهیزات",
        ):

            return await action(
                update,
                context,
            )

        return await action(
            update,
            context,
        )

    # ========================================================
    # PROFILE MENU
    # ========================================================

    profile_actions = {

        "👤 پروفایل": profile,

        "🎯 مأموریت‌ها": missions,

        "🎁 پاداش روزانه": daily_reward,

        "🏅 دستاوردها": achievements,

        "🧠 مشاور هوش مصنوعی": enter_ai,

        "📜 راهنما": help_screen,

        "⚙️ تنظیمات بازی": settings,
    }

    if text in profile_actions:

        return await profile_actions[text](
            update,
            context,
        )


# ============================================================
# MESSAGE -> INLINE SHOP
# ============================================================

async def equipment_shop_from_message(
    update,
    context,
):

    await update.message.reply_text(
        "🛒 <b>فروشگاه تجهیزات</b>\n\n"
        "برای خرید، دسته تجهیزات را انتخاب کنید.",
        parse_mode="HTML",
        reply_markup=inline(
            [
                ("📦 تجهیزات", "army:shop"),
            ],
            [
                ("🏠 منوی اصلی", "home"),
            ],
        ),
    )


async def factory_from_message(
    update,
    context,
):

    await update.message.reply_text(
        "🏭 <b>کارخانه</b>\n\n"
        "تجهیز موردنظر را برای تولید انتخاب کنید.",
        parse_mode="HTML",
        reply_markup=inline(
            [
                ("🏭 خط تولید", "factory:menu"),
            ],
            [
                ("🏠 منوی اصلی", "home"),
            ],
        ),
    )


# ============================================================
# ECONOMY TICK
# ============================================================

async def economy_tick(context):

    users = q(
        """
        SELECT user_id,country_code
        FROM users
        """,
        all=True,
    )

    for row in users:

        uid = row["user_id"]

        code = row["country_code"]

        c = country(code)

        u = user(uid)

        a = army(uid)

        provinces = q(
            """
            SELECT COUNT(*) n
            FROM provinces
            WHERE owner_id=?
            """,
            (uid,),
            one=True,
        )["n"]

        income = (
            10_000
            * (1 + c["tax_rate"] / 10)
            + provinces * 2_500
        )

        food_cost = max(
            500,
            a["soldiers"] // 20,
        )

        f = factory(uid)

        power_gain = (
            5_000
            + f["level"] * 1_000
        )

        q(
            """
            UPDATE countries
            SET
                money=money+?,
                food=MAX(0,food-?),
                power=power+?
            WHERE code=?
            """,
            (
                income,
                food_cost,
                power_gain,
                code,
            ),
            commit=True,
        )

        # ---------------- FOOD CRISIS ----------------

        if c["food"] < 1_000:

            q(
                """
                UPDATE users
                SET approval=MAX(0,approval-2)
                WHERE user_id=?
                """,
                (uid,),
                commit=True,
            )

            q(
                """
                UPDATE armies
                SET morale=MAX(20,morale-2)
                WHERE user_id=?
                """,
                (uid,),
                commit=True,
            )

        # ---------------- FACTORY ----------------

        if (
            f
            and f["queue_amount"] > 0
            and parse_dt(
                f["finish_time"]
            ) <= now()
        ):

            key = f["queue_equipment"]

            q(
                """
                UPDATE equipment_inventory
                SET amount=amount+?
                WHERE user_id=?
                AND equipment=?
                """,
                (
                    f["queue_amount"],
                    uid,
                    key,
                ),
                commit=True,
            )

            q(
                """
                UPDATE factories
                SET
                    queue_equipment='',
                    queue_amount=0,
                    finish_time=''
                WHERE user_id=?
                """,
                (uid,),
                commit=True,
            )

            news(
                f"🏭 کارخانه "
                f"{u['commander_name']} "
                f"تولید {EQ[key][1]} را تکمیل کرد."
            )

    # ---------------- WEATHER ----------------

    if random.random() < 0.15:

        weather = random.choice(
            list(WEATHER.keys())
        )

        q(
            """
            UPDATE provinces
            SET weather_condition=?
            """,
            (weather,),
            commit=True,
        )


# ============================================================
# WAR TICK
# ============================================================

async def war_tick(context):

    rows = q(
        """
        SELECT *
        FROM wars
        WHERE status='ACTIVE'
        AND end_time<=?
        """,
        (iso(now()),),
        all=True,
    )

    for w in rows:

        attacker = user(
            w["attacker_id"]
        )

        province = q(
            """
            SELECT *
            FROM provinces
            WHERE id=?
            """,
            (w["province_id"],),
            one=True,
        )

        if not province:
            continue

        tech_bonus = (
            1 + attacker["tech_level"] * 0.02
            if attacker
            else 1.05
        )

        bonus = (
            random.uniform(0.85, 1.15)
            * tech_bonus
        )

        attacker_power = (
            w["attacker_power"]
            * bonus
        )

        defender_power = (
            w["defender_power"]
            * random.uniform(0.85, 1.15)
        )

        win = (
            attacker_power
            > defender_power
        )

        if win:

            q(
                """
                UPDATE wars
                SET status='ATTACKER_WON'
                WHERE id=?
                """,
                (w["id"],),
                commit=True,
            )

            q(
                """
                UPDATE provinces
                SET
                    owner_id=?,
                    security=MAX(30,security-20)
                WHERE id=?
                """,
                (
                    w["attacker_id"],
                    w["province_id"],
                ),
                commit=True,
            )

            q(
                """
                UPDATE users
                SET
                    score=score+500,
                    season_score=season_score+500,
                    approval=MIN(100,approval+3)
                WHERE user_id=?
                """,
                (w["attacker_id"],),
                commit=True,
            )

            news(
                f"🏆 پیروزی بزرگ: "
                f"{attacker['commander_name']} "
                f"استان {province['name']} را تصرف کرد."
            )

        else:

            q(
                """
                UPDATE wars
                SET status='DEFENDER_WON'
                WHERE id=?
                """,
                (w["id"],),
                commit=True,
            )

            q(
                """
                UPDATE users
                SET
                    score=MAX(0,score-100),
                    approval=MAX(0,approval-2)
                WHERE user_id=?
                """,
                (w["attacker_id"],),
                commit=True,
            )

            news(
                f"💀 حمله به "
                f"{province['name']} شکست خورد."
            )


# ============================================================
# AI NATIONS
# ============================================================

async def ai_tick(context):

    for code, name, flag, population in COUNTRIES:

        c = country(code)

        if not c or c["is_ai"] == 0:
            continue

        delta = random.randint(
            10_000,
            50_000,
        )

        q(
            """
            UPDATE countries
            SET
                money=money+?,
                oil=oil+?,
                steel=steel+?
            WHERE code=?
            """,
            (
                delta,
                random.randint(500, 3000),
                random.randint(500, 2500),
                code,
            ),
            commit=True,
        )

        if random.random() < 0.04:

            news(
                f"🌐 {flag} {name} "
                f"یک برنامه توسعه ملی جدید اعلام کرد."
            )


# ============================================================
# SEASON
# ============================================================

async def season_tick(context):

    end = q(
        """
        SELECT value
        FROM game_state
        WHERE key='season_end'
        """,
        one=True,
    )

    if not end:
        return

    if parse_dt(end["value"]) > now():
        return

    season = int(
        q(
            """
            SELECT value
            FROM game_state
            WHERE key='season'
            """,
            one=True,
        )["value"]
    ) + 1

    q(
        """
        UPDATE users
        SET season_score=0
        """,
        commit=True,
    )

    q(
        """
        UPDATE game_state
        SET value=?
        WHERE key='season'
        """,
        (str(season),),
        commit=True,
    )

    q(
        """
        UPDATE game_state
        SET value=?
        WHERE key='season_end'
        """,
        (
            iso(
                now()
                + timedelta(days=30)
            ),
        ),
        commit=True,
    )

    news(
        f"🏁 فصل {season} لیگ جهانی آغاز شد!"
    )


# ============================================================
# COMMANDS
# ============================================================

async def admin_command(update, context):

    if not admin(update.effective_user.id):

        await update.message.reply_text(
            "⛔ دسترسی غیرمجاز."
        )

        return

    await admin_panel(
        update,
        context,
    )


async def cancel(update, context):

    uid = update.effective_user.id

    q(
        """
        UPDATE users
        SET chat_state='NONE'
        WHERE user_id=?
        """,
        (uid,),
        commit=True,
    )

    await update.message.reply_text(
        "لغو شد.",
        reply_markup=main_kb(uid),
    )


async def show_id(update, context):

    await update.message.reply_text(
        f"🆔 شناسه تلگرام شما:\n\n"
        f"<code>{update.effective_user.id}</code>",
        parse_mode="HTML",
    )


# ============================================================
# MAIN
# ============================================================

def main():

    init_db()

    if not BOT_TOKEN:

        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set"
        )

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # ---------------- COMMANDS ----------------

    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    app.add_handler(
        CommandHandler(
            "admin",
            admin_command,
        )
    )

    app.add_handler(
        CommandHandler(
            "cancel",
            cancel,
        )
    )

    app.add_handler(
        CommandHandler(
            "id",
            show_id,
        )
    )

    # ---------------- CALLBACKS ----------------

    app.add_handler(
        CallbackQueryHandler(
            callbacks,
        )
    )

    # ---------------- TEXT ----------------

    app.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            text_router,
        )
    )

    # ---------------- JOB QUEUE ----------------

    job_queue = app.job_queue

    if job_queue:

        job_queue.run_repeating(
            war_tick,
            interval=20,
            first=10,
        )

        job_queue.run_repeating(
            economy_tick,
            interval=60,
            first=20,
        )

        job_queue.run_repeating(
            ai_tick,
            interval=300,
            first=60,
        )

        job_queue.run_repeating(
            season_tick,
            interval=3600,
            first=120,
        )

    logger.info(
        "WORLD WAR V4 started"
    )

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
