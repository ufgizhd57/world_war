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

    for code, name, flag, population in COUNTRIES:
        c.execute(
            """
            INSERT OR IGNORE INTO countries
            (code,name,flag,population)
            VALUES(?,?,?,?)
            """,
            (code, name, flag, population),
        )

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
# FACTORY & PRODUCTION
# ============================================================

async def factory_screen(update, context):
    uid = update.effective_user.id
    f = factory(uid)
    u = user(uid)
    c = country(u["country_code"])

    lines = [
        f"{status_header(uid)}",
        "",
        "🏭 <b>کارخانه ملی تسلیحاتی</b>",
        "",
        f"⭐ سطح کارخانه: {f['level']}",
    ]

    if f["queue_equipment"]:
        eq_name = EQ.get(f["queue_equipment"], ("", f["queue_equipment"]))[1]
        lines.append(f"⚙️ در حال تولید: {f['queue_amount']} عدد {eq_name}")
        lines.append(f"⏳ زمان اتمام: {f['finish_time']}")
    else:
        lines.append("💤 کارخانه در حال حاضر بیکار است.")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=inline(
            [("⚙️ تولید تفنگ (5 عددی)", "produce:rifle:5")],
            [("⚙️ تولید نفربر (1 عددی)", "produce:apc:1")],
            [("⚙️ تولید تانک (1 عددی)", "produce:tank:1")],
            [("🏠 منوی اصلی", "home")],
        ),
    )


async def produce_item(query, key, amount):
    uid = query.from_user.id
    item = EQ.get(key)
    if not item:
        return

    total_cost = item[5] * int(amount)
    u = user(uid)
    c = country(u["country_code"])

    if c["money"] < total_cost:
        await edit_or_send(query, "❌ بودجه کافی برای تولید این تجهیزات وجود ندارد.", home_markup())
        return

    q("UPDATE countries SET money=money-? WHERE code=?", (total_cost, u["country_code"]), commit=True)
    
    q(
        "UPDATE equipment_inventory SET amount=amount+? WHERE user_id=? AND equipment=?",
        (int(amount), uid, key),
        commit=True
    )

    await edit_or_send(
        query,
        f"✅ تولید موفقیت‌آمیز!\n\nتعداد {amount} عدد {item[1]} به ارتش شما افزوده شد.\n💰 هزینه کل: ${total_cost:,.0f}",
        inline([("🏭 بازگشت به کارخانه", "economy:factory"), ("🏠 منوی اصلی", "home")])
    )


# ============================================================
# WAR & ATTACK SYSTEM
# ============================================================

async def attack_menu(update, context):
    uid = update.effective_user.id
    u = user(uid)

    rows = q(
        "SELECT code, name, flag FROM countries WHERE code!=? AND is_ai=0",
        (u["country_code"],),
        all=True
    )

    if not rows:
        await update.message.reply_text(
            "⚔️ در حال حاضر کشور دیگری برای حمله وجود ندارد.",
            reply_markup=war_kb()
        )
        return

    keys = []
    for r in rows:
        keys.append([InlineKeyboardButton(f"⚔️ حمله به {r['flag']} {r['name']}", callback_data=f"attack_target:{r['code']}")])

    keys.append([InlineKeyboardButton("🏠 منوی اصلی", callback_data="home")])

    await update.message.reply_text(
        "🎯 <b>انتخاب هدف برای عملیات نظامی</b>\n\nکشور مورد نظر خود را انتخاب کنید:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keys)
    )


async def execute_attack(query, target_code):
    uid = query.from_user.id
    attacker_power = military_power(uid)
    
    target_country = country(target_code)
    if not target_country:
        await edit_or_send(query, "❌ کشور هدف یافت نشد.", home_markup())
        return

    win = attacker_power > 50000

    if win:
        q("UPDATE users SET score=score+50 WHERE user_id=?", (uid,), commit=True)
        result_text = f"🎉 <b>پیروزی بزرگ!</b>\n\nعملیات نظامی علیه {target_country['flag']} {target_country['name']} با موفقیت انجام شد و دشمن شکست خورد."
        news(f"🚨 جنگ: کشور {target_country['name']} در نبرد شکست خورد!")
    else:
        result_text = f"❌ <b>شکست در عملیات!</b>\n\nمدافعان دشمن قوی‌تر بودند و نیروهای ما عقب‌نشینی کردند."

    await edit_or_send(
        query,
        result_text,
        inline([("⚔️ عملیات دیگر", "war:attack"), ("🏠 منوی اصلی", "home")])
    )


# ============================================================
# MESSAGE & CALLBACK ROUTER
# ============================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "⚔️ جنگ و عملیات":
        await open_war_menu(update, context)
    elif text == "🏭 کشور و اقتصاد":
        await open_economy_menu(update, context)
    elif text == "🪖 ارتش و تجهیزات":
        await open_army_menu(update, context)
    elif text == "👤 پروفایل و تنظیمات":
        await open_profile_menu(update, context)
    elif text == "👤 پروفایل":
        await profile(update, context)
    elif text == "🗺️ نقشه جهان":
        await world_map(update, context)
    elif text == "📊 وضعیت ارتش":
        await army_screen(update, context)
    elif text == "🏭 کارخانه":
        await factory_screen(update, context)
    elif text == "🎯 حمله به کشور":
        await attack_menu(update, context)
    elif text == "🔙 بازگشت به منوی اصلی":
        await go_home(update, context)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "home":
        await query.message.reply_text("🌍 منوی اصلی:", reply_markup=main_kb(query.from_user.id))
    elif data.startswith("country:"):
        code = data.split(":")[1]
        await select_country(query, code)
    elif data == "map:mine":
        await map_mine(query)
    elif data.startswith("shop:"):
        page = int(data.split(":")[1])
        await equipment_shop(query, page)
    elif data.startswith("buy:"):
        key = data.split(":")[1]
        await buy_equipment(query, key)
    elif data == "army:shop":
        await equipment_shop(query, 0)
    elif data == "economy:factory":
        await factory_screen(update, context)
    elif data.startswith("produce:"):
        parts = data.split(":")
        await produce_item(query, parts[1], parts[2])
    elif data.startswith("attack_target:"):
        target_code = data.split(":")[1]
        await execute_attack(query, target_code)
    elif data == "war:attack":
        await attack_menu(update.callback_query, context) if hasattr(update.callback_query, 'message') else None


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def main():
    init_db()
    
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is missing!")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is starting...")
    application.run_polling()


if __name__ == "__main__":
    main()
