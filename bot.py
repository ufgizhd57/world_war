import os
import random
import sqlite3
import logging
from datetime import datetime, timedelta, timezone
from html import escape

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
log = logging.getLogger('world-war-v5')

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
DB_NAME = os.getenv('DB_NAME', 'world_war.db')
ADMIN_IDS = {int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip().isdigit()}

MAIN_MENU = [
    ['⚔️ جنگ و عملیات', '🏭 کشور و اقتصاد'],
    ['🪖 ارتش و تجهیزات', '👤 پروفایل و تنظیمات'],
]
WAR_MENU = [
    ['🎯 حمله', '🛡 دفاع'],
    ['🕵️ جاسوسی', '🤝 دیپلماسی'],
    ['🌍 رویدادهای جهان', '🏆 رنکینگ'],
    ['🔙 منوی اصلی'],
]
ECONOMY_MENU = [
    ['🌍 کشور من', '🗺️ شهرها'],
    ['🏭 صنعت', '🌐 بازار جهانی'],
    ['🧬 فناوری', '🏛️ سیاست داخلی'],
    ['📰 اخبار جهان', '🏅 لیگ و فصل'],
    ['🔙 منوی اصلی'],
]
ARMY_MENU = [
    ['📊 ارتش', '🛒 تجهیزات'],
    ['🏭 تولید', '🎖️ فرماندهان'],
    ['✈️ نیروی هوایی', '⚓ نیروی دریایی'],
    ['🔙 منوی اصلی'],
]
PROFILE_MENU = [
    ['👤 پروفایل', '🎯 مأموریت‌ها'],
    ['🏅 دستاوردها', '🎁 پاداش روزانه'],
    ['🧠 مشاور', '📜 راهنما'],
    ['⚙️ تنظیمات'],
    ['🔙 منوی اصلی'],
]

COUNTRIES = {
    'IRN': ('ایران', '🇮🇷', 85_000_000, '⛽ انرژی', 1.12, 1.05),
    'USA': ('آمریکا', '🇺🇸', 330_000_000, '🏭 صنعت', 1.12, 1.10),
    'RUS': ('روسیه', '🇷🇺', 144_000_000, '🛡️ عمق دفاعی', 1.08, 1.15),
    'CHN': ('چین', '🇨🇳', 1_400_000_000, '🏗️ تولید انبوه', 1.15, 1.08),
    'DEU': ('آلمان', '🇩🇪', 83_000_000, '⚙️ مهندسی', 1.14, 1.06),
    'FRA': ('فرانسه', '🇫🇷', 67_000_000, '✈️ هوافضا', 1.08, 1.10),
    'GBR': ('انگلیس', '🇬🇧', 67_000_000, '⚓ دریایی', 1.06, 1.14),
    'JPN': ('ژاپن', '🇯🇵', 125_000_000, '🤖 فناوری', 1.13, 1.08),
    'TUR': ('ترکیه', '🇹🇷', 84_000_000, '🧭 موقعیت راهبردی', 1.06, 1.10),
    'IND': ('هند', '🇮🇳', 1_380_000_000, '👥 نیروی انسانی', 1.18, 1.03),
}

CITY_NAMES = {
    'IRN': ['تهران','اصفهان','شیراز','تبریز','مشهد'], 'USA':['واشنگتن','نیویورک','تگزاس','کالیفرنیا','فلوریدا'],
    'RUS':['مسکو','سن‌پترزبورگ','کازان','سیبری','ولگوگراد'], 'CHN':['پکن','شانگهای','گوانگ‌ژو','سیچوان','شین‌جیانگ'],
    'DEU':['برلین','هامبورگ','مونیخ','هسن'], 'FRA':['پاریس','لیون','مارسی','تولوز'],
    'GBR':['لندن','منچستر','اسکاتلند','ولز'], 'JPN':['توکیو','اوساکا','کیوتو','هوکایدو'],
    'TUR':['آنکارا','استانبول','ازمیر','آنتالیا'], 'IND':['دهلی','گجرات','ماهاراشترا','بنگال'],
}

EQUIPMENT = {
    'infantry': ('🪖 پیاده‌نظام', 1.0, 3000, 1), 'apc': ('🚙 نفربر', 2.0, 12000, 1.2),
    'ifv': ('🛡️ خودروی رزمی', 2.7, 18000, 1.5), 'tank': ('🛡️ تانک', 5.0, 55000, 3),
    'artillery': ('💥 توپخانه', 4.0, 42000, 2.5), 'mlrs': ('🚀 راکت‌انداز', 5.5, 70000, 3.5),
    'sam': ('🛡️ پدافند هوایی', 2.0, 90000, 4), 'fighter': ('✈️ جنگنده', 6.0, 900000, 15),
    'bomber': ('💣 بمب‌افکن', 8.0, 1600000, 20), 'heli': ('🚁 بالگرد تهاجمی', 5.5, 450000, 7),
    'drone': ('🛸 پهپاد', 2.0, 70000, 1.5), 'ew': ('📡 جنگ الکترونیک', 2.5, 180000, 2.5),
    'frigate': ('🚢 ناوچه', 3.0, 800000, 10), 'destroyer': ('⚓ ناوشکن', 5.5, 1500000, 16),
    'cruiser': ('🚢 رزم‌ناو', 7.0, 2200000, 22), 'carrier': ('🛳️ ناو هواپیمابر', 12.0, 6500000, 50),
    'submarine': ('🌊 زیردریایی', 7.0, 2500000, 25), 'satellite': ('🛰️ ماهواره', 2.0, 3000000, 10),
    'cruise': ('🚀 موشک کروز', 10.0, 120000, .5), 'hypersonic': ('⚡ هایپرسونیک', 20.0, 1200000, 2),
}
TECHS = {
    'industry': ('🏭 صنعت پیشرفته', 150000, 1.08), 'armor': ('🛡️ زرهی', 180000, 1.07),
    'air': ('✈️ هوافضا', 250000, 1.08), 'navy': ('⚓ دریایی', 260000, 1.08),
    'cyber': ('💻 سایبری', 300000, 1.10), 'space': ('🛰️ فضایی', 500000, 1.10),
    'doctrine': ('📚 دکترین', 650000, 1.12), 'logistics': ('🚚 لجستیک', 120000, 1.06),
}
EVENTS = [
    ('📈 رونق اقتصادی','درآمد افزایش یافت','eco'), ('🛢️ کشف منابع','نفت و فولاد افزایش یافت','res'),
    ('⚠️ بحران داخلی','رضایت کاهش یافت','crisis'), ('🌧️ بارندگی شدید','تولید موقتاً کاهش یافت','rain'),
    ('🚀 جهش فناوری','پیشرفت فناوری افزایش یافت','tech'),
]


def db():
    c = sqlite3.connect(DB_NAME, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA journal_mode=WAL')
    return c


def q(sql, params=(), one=False, all=False, commit=False):
    c = db()
    try:
        cur = c.execute(sql, params)
        result = cur.fetchone() if one else (cur.fetchall() if all else None)
        if commit: c.commit()
        return result
    finally: c.close()


def now(): return datetime.now(timezone.utc)
def iso(d): return d.isoformat()
def uid_of(update): return update.effective_user.id

def kb(rows): return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)
def ikb(rows): return InlineKeyboardMarkup([[InlineKeyboardButton(a, callback_data=b) for a,b in r] for r in rows])

def get_user(uid): return q('SELECT * FROM users WHERE user_id=?',(uid,),one=True)
def get_country(code): return q('SELECT * FROM countries WHERE code=?',(code,),one=True)
def is_admin(uid): return uid in ADMIN_IDS


def init_db():
    c=db(); c.executescript('''
    CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY,name TEXT,country TEXT,level INTEGER DEFAULT 1,score INTEGER DEFAULT 0,season_score INTEGER DEFAULT 0,approval INTEGER DEFAULT 100,morale INTEGER DEFAULT 85,reputation INTEGER DEFAULT 0,last_daily TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS countries(code TEXT PRIMARY KEY,name TEXT,flag TEXT,population INTEGER,money REAL DEFAULT 1000000,oil REAL DEFAULT 50000,steel REAL DEFAULT 50000,food REAL DEFAULT 100000,power REAL DEFAULT 50000,occupied INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS cities(id INTEGER PRIMARY KEY AUTOINCREMENT,owner INTEGER,name TEXT,level INTEGER DEFAULT 1,population INTEGER,industry INTEGER DEFAULT 1,defense INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS armies(user_id INTEGER PRIMARY KEY,soldiers INTEGER DEFAULT 10000,morale INTEGER DEFAULT 85,air_defense INTEGER DEFAULT 1,cyber INTEGER DEFAULT 1,logistics INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS equipment(user_id INTEGER,item TEXT,amount INTEGER DEFAULT 0,PRIMARY KEY(user_id,item));
    CREATE TABLE IF NOT EXISTS generals(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,name TEXT,role TEXT,level INTEGER DEFAULT 1,attack REAL DEFAULT 1,defense REAL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS tech(user_id INTEGER,code TEXT,level INTEGER DEFAULT 0,progress INTEGER DEFAULT 0,PRIMARY KEY(user_id,code));
    CREATE TABLE IF NOT EXISTS wars(id INTEGER PRIMARY KEY AUTOINCREMENT,attacker INTEGER,defender INTEGER,city_id INTEGER,end_time TEXT,attack_power REAL,defense_power REAL,status TEXT DEFAULT 'ACTIVE');
    CREATE TABLE IF NOT EXISTS diplomacy(id INTEGER PRIMARY KEY AUTOINCREMENT,a INTEGER,b INTEGER,relation TEXT,status TEXT DEFAULT 'ACTIVE',expires TEXT);
    CREATE TABLE IF NOT EXISTS spy_ops(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,target INTEGER,op TEXT,success INTEGER,report TEXT,created TEXT);
    CREATE TABLE IF NOT EXISTS market(item TEXT PRIMARY KEY,price REAL);
    CREATE TABLE IF NOT EXISTS missions(user_id INTEGER,day TEXT,code TEXT,title TEXT,progress INTEGER,target INTEGER,reward INTEGER,claimed INTEGER DEFAULT 0,PRIMARY KEY(user_id,day,code));
    CREATE TABLE IF NOT EXISTS achievements(user_id INTEGER,code TEXT,title TEXT,PRIMARY KEY(user_id,code));
    CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,title TEXT,body TEXT,created TEXT);
    CREATE TABLE IF NOT EXISTS news(id INTEGER PRIMARY KEY AUTOINCREMENT,text TEXT,created TEXT);
    CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY,value TEXT);
    CREATE TABLE IF NOT EXISTS settings(user_id INTEGER PRIMARY KEY,notifications INTEGER DEFAULT 1);
    ''')
    for code,(name,flag,pop,trait,eco,mil) in COUNTRIES.items():
        c.execute('INSERT OR IGNORE INTO countries(code,name,flag,population) VALUES(?,?,?,?)',(code,name,flag,pop))
    for item,price in [('oil',100),('steel',80),('food',40),('power',60),('gold',500)]:
        c.execute('INSERT OR IGNORE INTO market(item,price) VALUES(?,?)',(item,price))
    c.execute("INSERT OR IGNORE INTO state(key,value) VALUES('season','1')")
    c.execute("INSERT OR IGNORE INTO state(key,value) VALUES('season_end',?)",(iso(now()+timedelta(days=30)),))
    c.commit(); c.close()


def seed(uid):
    u=get_user(uid)
    if not u:return
    for code in TECHS:q('INSERT OR IGNORE INTO tech(user_id,code) VALUES(?,?)',(uid,code),commit=True)
    q('INSERT OR IGNORE INTO settings(user_id) VALUES(?)',(uid,),commit=True)
    if not q('SELECT 1 FROM cities WHERE owner=? LIMIT 1',(uid,),one=True):
        names=CITY_NAMES.get(u['country'],['پایتخت'])
        pop=get_country(u['country'])['population']//10
        for i,n in enumerate(names[:5]):
            q('INSERT INTO cities(owner,name,population,industry,defense) VALUES(?,?,?,?,?)',(uid,n,max(500000,pop//len(names)),2 if i==0 else 1,2 if i==0 else 1),commit=True)
    for item in EQUIPMENT:q('INSERT OR IGNORE INTO equipment(user_id,item,amount) VALUES(?,?,0)',(uid,item),commit=True)
    q("UPDATE equipment SET amount=MAX(amount,?) WHERE user_id=? AND item='infantry'",(5000,uid),commit=True)
    q('INSERT OR IGNORE INTO armies(user_id) VALUES(?)',(uid,),commit=True)
    q("INSERT OR IGNORE INTO generals(user_id,name,role,attack,defense) VALUES(?,?,?,?,?)",(uid,'ژنرال اصلی','استراتژیست',1.10,1.08),commit=True)
    missions_seed(uid)


def missions_seed(uid):
    day=now().strftime('%Y-%m-%d')
    data=[('win','⚔️ یک جنگ را ببر',1,1000),('trade','🌐 سه معامله انجام بده',3,900),('research','🧬 یک فناوری ارتقا بده',1,1000),('spy','🕵️ یک عملیات جاسوسی',1,700),('city','🏙️ یک شهر را ارتقا بده',1,800)]
    for code,title,target,reward in data:q('INSERT OR IGNORE INTO missions VALUES(?,?,?,?,0,?,?,0)',(uid,day,code,title,target,reward),commit=True)


def progress(uid,code,n=1):
    day=now().strftime('%Y-%m-%d'); q('UPDATE missions SET progress=MIN(target,progress+?) WHERE user_id=? AND day=? AND code=?',(n,uid,day,code),commit=True)


def add_news(text): q('INSERT INTO news(text,created) VALUES(?,?)',(text,iso(now())),commit=True)

def trait(uid):
    u=get_user(uid); return COUNTRIES[u['country']][3:]

def tech_mult(uid,code):
    r=q('SELECT level FROM tech WHERE user_id=? AND code=?',(uid,code),one=True); return 1+(r['level'] if r else 0)*TECHS[code][2]/10

def military_power(uid):
    a=q('SELECT * FROM armies WHERE user_id=?',(uid,),one=True); base=a['soldiers']*.8
    for item,(_,power,_,_) in EQUIPMENT.items():
        r=q('SELECT amount FROM equipment WHERE user_id=? AND item=?',(uid,item),one=True); base+=(r['amount'] if r else 0)*power
    g=q('SELECT attack,defense,level FROM generals WHERE user_id=? AND level=(SELECT MAX(level) FROM generals WHERE user_id=?) LIMIT 1',(uid,uid),one=True)
    bonus=(g['attack'] if g else 1)*((g['level'] if g else 1)*.03+1)
    return base*bonus*tech_mult(uid,'doctrine')*tech_mult(uid,'logistics')

async def start(update,context):
    uid=uid_of(update); u=get_user(uid)
    if u:
        seed(uid); return await update.message.reply_text('🌍 <b>ستاد فرماندهی</b> آماده است.\n\nچهار بخش اصلی را انتخاب کنید.',parse_mode='HTML',reply_markup=kb(MAIN_MENU))
    rows=[]; line=[]
    for code,(name,flag,*_) in COUNTRIES.items():
        line.append(InlineKeyboardButton(f'{flag} {name}',callback_data=f'country:{code}'))
        if len(line)==2:rows.append(line);line=[]
    if line:rows.append(line)
    await update.message.reply_text('🌍 <b>WORLD WAR V5</b>\n\nکشور خود را انتخاب کنید:',parse_mode='HTML',reply_markup=InlineKeyboardMarkup(rows))

async def choose_country(query,code):
    uid=query.from_user.id; c=get_country(code)
    if get_user(uid):return await query.message.reply_text('قبلاً کشور انتخاب شده است.')
    if c['occupied']:return await query.message.reply_text('❌ این کشور در اختیار بازیکن دیگری است.')
    q('INSERT INTO users(user_id,name,country) VALUES(?,?,?)',(uid,query.from_user.first_name,code),commit=True)
    q('UPDATE countries SET occupied=1 WHERE code=?',(code,),commit=True); seed(uid)
    await query.edit_message_text(f"{c['flag']} <b>{escape(c['name'])}</b> انتخاب شد.\n\nکشورت را بساز، ارتش تشکیل بده و جهان را فتح کن!",parse_mode='HTML')
    await query.message.reply_text('🏠 منوی اصلی',reply_markup=kb(MAIN_MENU))

async def country_screen(update,context):
    uid=uid_of(update);u=get_user(uid);c=get_country(u['country']); cities=q('SELECT * FROM cities WHERE owner=?',(uid,),all=True);t,m=trait(uid)
    text=f"{c['flag']} <b>{c['name']}</b>\n\n🧬 ویژگی: {COUNTRIES[u['country']][3]}\n💰 ${c['money']:,.0f}\n🛢️ {c['oil']:,.0f} نفت\n🏭 {c['steel']:,.0f} فولاد\n🌾 {c['food']:,.0f} غذا\n😊 رضایت: {u['approval']}%\n⚡ قدرت: {military_power(uid):,.0f}\n🏙️ شهرها: {len(cities)}"
    await update.message.reply_text(text,parse_mode='HTML',reply_markup=kb(ECONOMY_MENU))

async def cities_screen(update,context):
    uid=uid_of(update); rows=q('SELECT * FROM cities WHERE owner=?',(uid,),all=True); buttons=[[(f"🏙️ {r['name']} | Lv.{r['level']}",f'city:{r["id"]}')] for r in rows];buttons.append([('🏠 منوی اصلی','home')])
    await update.message.reply_text('🗺️ <b>شهرهای شما</b>\n\nیک شهر را انتخاب کنید.',parse_mode='HTML',reply_markup=ikb(buttons))

async def city_callback(query,cid):
    uid=query.from_user.id;r=q('SELECT * FROM cities WHERE id=? AND owner=?',(cid,uid),one=True)
    if not r:return await query.answer('شهر نامعتبر',show_alert=True)
    cost=r['level']*100000
    await query.edit_message_text(f"🏙️ <b>{escape(r['name'])}</b>\n\nسطح: {r['level']}\n👥 جمعیت: {r['population']:,}\n🏭 صنعت: {r['industry']}\n🛡 دفاع: {r['defense']}\n\nهزینه ارتقا: ${cost:,}",parse_mode='HTML',reply_markup=ikb([[('🏗️ ارتقا',f'cityup:{cid}')],[('🏠 خانه','home')]]))

async def city_upgrade(query,cid):
    uid=query.from_user.id;r=q('SELECT * FROM cities WHERE id=? AND owner=?',(cid,uid),one=True);u=get_user(uid);c=get_country(u['country'])
    if not r:return await query.answer('شهر نامعتبر',show_alert=True)
    cost=r['level']*100000
    if c['money']<cost:return await query.answer('بودجه کافی نیست',show_alert=True)
    q('UPDATE countries SET money=money-? WHERE code=?',(cost,u['country']),commit=True);q('UPDATE cities SET level=level+1,industry=industry+1,defense=defense+1 WHERE id=?',(cid,),commit=True);progress(uid,'city');await query.edit_message_text('✅ شهر با موفقیت ارتقا یافت.',reply_markup=ikb([[('🏠 خانه','home')]]))

async def tech_screen(update,context):
    uid=uid_of(update);rows=q('SELECT * FROM tech WHERE user_id=?',(uid,),all=True);text='🧬 <b>درخت فناوری</b>\n\n';buttons=[]
    for r in rows:
        title,cost,m=TECHS[r['code']];text+=f'{title} — Lv.{r["level"]} — {r["progress"]}/100\n';buttons.append([(f'⬆️ {title}',f'tech:{r["code"]}')])
    buttons.append([('🏠 خانه','home')]);await update.message.reply_text(text,parse_mode='HTML',reply_markup=ikb(buttons))

async def tech_upgrade(query,code):
    uid=query.from_user.id;title,cost,m=TECHS[code];r=q('SELECT level FROM tech WHERE user_id=? AND code=?',(uid,code),one=True);price=cost*(r['level']+1);c=get_country(get_user(uid)['country'])
    if c['money']<price:return await query.answer(f'نیاز به ${price:,}',show_alert=True)
    q('UPDATE countries SET money=money-? WHERE code=?',(price,get_user(uid)['country']),commit=True);q('UPDATE tech SET level=level+1,progress=0 WHERE user_id=? AND code=?',(uid,code),commit=True);progress(uid,'research');q('INSERT OR IGNORE INTO achievements VALUES(?,?,?)',(uid,'tech_'+code,'پژوهشگر '+title),commit=True);await query.edit_message_text(f'✅ {title} به سطح {r["level"]+1} رسید.',reply_markup=ikb([[('🏠 خانه','home')]]))

async def army_screen(update,context):
    uid=uid_of(update);a=q('SELECT * FROM armies WHERE user_id=?',(uid,),one=True);text=f'🪖 <b>ارتش</b>\n\n👥 سرباز: {a["soldiers"]:,}\n❤️ روحیه: {a["morale"]}%\n🛡 پدافند: {a["air_defense"]}\n💻 سایبر: {a["cyber"]}\n🚚 لجستیک: {a["logistics"]}\n⚡ قدرت کل: {military_power(uid):,.0f}'
    await update.message.reply_text(text,parse_mode='HTML',reply_markup=kb(ARMY_MENU))

async def equipment_screen(update,context):
    uid=uid_of(update);text='🛒 <b>تجهیزات</b>\n\n';buttons=[]
    for code,(name,power,cost,maint) in EQUIPMENT.items():
        r=q('SELECT amount FROM equipment WHERE user_id=? AND item=?',(uid,code),one=True);text+=f'{name}: {r["amount"]}\n';buttons.append([(f'🛒 {name}',f'buy:{code}')])
    buttons.append([('🏠 خانه','home')]);await update.message.reply_text(text,parse_mode='HTML',reply_markup=ikb(buttons))

async def buy(query,code):
    uid=query.from_user.id;name,power,cost,maint=EQUIPMENT[code];c=get_country(get_user(uid)['country']);qty=1
    if c['money']<cost:return await query.answer('پول کافی نیست',show_alert=True)
    q('UPDATE countries SET money=money-? WHERE code=?',(cost,c['code']),commit=True);q('UPDATE equipment SET amount=amount+1 WHERE user_id=? AND item=?',(uid,code),commit=True);await query.answer(f'{name} خریداری شد')

async def generals_screen(update,context):
    uid=uid_of(update);rows=q('SELECT * FROM generals WHERE user_id=?',(uid,),all=True);text='🎖️ <b>فرماندهان</b>\n\n'
    for r in rows:text+=f"{r['name']} | {r['role']} | Lv.{r['level']} | ⚔️{r['attack']:.2f} 🛡{r['defense']:.2f}\n"
    await update.message.reply_text(text,parse_mode='HTML',reply_markup=kb(ARMY_MENU))

async def war_screen(update,context):
    uid=uid_of(update);rows=q('SELECT c.id,c.name,c.owner FROM cities c WHERE c.owner!=?',(uid,),all=True);buttons=[]
    for r in rows:buttons.append([(f'🎯 {r["name"]}',f'attack:{r["id"]}')])
    buttons.append([('🏠 خانه','home')]);await update.message.reply_text('🎯 <b>اهداف نظامی</b>\n\nشهر موردنظر را انتخاب کنید.',parse_mode='HTML',reply_markup=ikb(buttons))

async def launch_attack(query,cid):
    uid=query.from_user.id;r=q('SELECT * FROM cities WHERE id=? AND owner!=?',(cid,uid),one=True)
    if not r:return await query.answer('هدف نامعتبر',show_alert=True)
    defender=r['owner'];ap=military_power(uid)*random.uniform(.85,1.15);dp=(military_power(defender)*.65+r['defense']*5000 if get_user(defender) else r['defense']*5000)
    win=ap>dp
    if win:
        q('UPDATE cities SET owner=? WHERE id=?',(uid,cid),commit=True);q('UPDATE users SET score=score+500,season_score=season_score+500,approval=MIN(100,approval+3) WHERE user_id=?',(uid,),commit=True);progress(uid,'win');msg=f'🏆 پیروزی! شهر {r["name"]} تصرف شد.'
    else:q('UPDATE users SET score=MAX(0,score-100),approval=MAX(0,approval-2) WHERE user_id=?',(uid,),commit=True);msg=f'💀 حمله به {r["name"]} شکست خورد.'
    add_news(msg);await query.edit_message_text(msg,reply_markup=ikb([[('🏠 خانه','home')]]))

async def diplomacy_screen(update,context):
    uid=uid_of(update);rows=q('SELECT u.user_id,c.name,c.flag FROM users u JOIN countries c ON c.code=u.country WHERE u.user_id!=?',(uid,),all=True);buttons=[]
    for r in rows:buttons.append([(f'🤝 {r["flag"]} {r["name"]}',f'dip:{r["user_id"]}')])
    buttons.append([('🏠 خانه','home')]);await update.message.reply_text('🤝 <b>دیپلماسی</b>',parse_mode='HTML',reply_markup=ikb(buttons))

async def dip_target(query,target):await query.edit_message_text('🤝 نوع رابطه:',reply_markup=ikb([[('🕊️ صلح',f'dipact:PEACE:{target}'),('🤝 اتحاد',f'dipact:ALLY:{target}')],[('🚫 تحریم',f'dipact:SANC:{target}')],[('🏠 خانه','home')]]))

async def dip_action(query,rel,target):
    uid=query.from_user.id;expires=iso(now()+timedelta(days=7));q('INSERT INTO diplomacy(a,b,relation,expires) VALUES(?,?,?,?,?)',(uid,target,rel,expires),commit=True)
    if rel=='SANC':q('UPDATE users SET approval=MAX(0,approval-1) WHERE user_id=?',(target,),commit=True)
    await query.edit_message_text('✅ اقدام دیپلماتیک ثبت شد.',reply_markup=ikb([[('🏠 خانه','home')]]))

async def spy_screen(update,context):
    uid=uid_of(update);rows=q('SELECT u.user_id,c.name,c.flag FROM users u JOIN countries c ON c.code=u.country WHERE u.user_id!=?',(uid,),all=True);buttons=[[(f'🕵️ {r["flag"]} {r["name"]}',f'spy:{r["user_id"]}')] for r in rows];buttons.append([('🏠 خانه','home')]);await update.message.reply_text('🕵️ <b>شبکه جاسوسی</b>',parse_mode='HTML',reply_markup=ikb(buttons))

async def spy_target(query,target):await query.edit_message_text('🕵️ عملیات:',reply_markup=ikb([[('📊 شناسایی ارتش',f'spyact:RECON:{target}'),('💰 اقتصاد',f'spyact:ECO:{target}')],[('💻 سایبری',f'spyact:CYBER:{target}')],[('🏠 خانه','home')]]))

async def spy_action(query,op,target):
    uid=query.from_user.id;a=q('SELECT cyber FROM armies WHERE user_id=?',(uid,),one=True);chance=min(.9,.55+a['cyber']*.05);ok=random.random()<chance;u=get_user(target);report=''
    if ok:
        c=get_country(u['country']);report=f'ارتش: {military_power(target):,.0f}\nخزانه: ${c["money"]:,.0f}\nرضایت: {u["approval"]}%'
        if op=='CYBER':q('UPDATE countries SET power=MAX(0,power-3000) WHERE code=?',(u['country'],),commit=True)
    else:report='❌ عملیات شکست خورد.'
    q('INSERT INTO spy_ops(user_id,target,op,success,report,created) VALUES(?,?,?,?,?,?)',(uid,target,op,int(ok),report,iso(now())),commit=True);progress(uid,'spy');await query.edit_message_text('🕵️ <b>گزارش</b>\n\n'+escape(report),parse_mode='HTML',reply_markup=ikb([[('🏠 خانه','home')]]))

async def market_screen(update,context):
    rows=q('SELECT * FROM market',all=True);text='🌐 <b>بازار جهانی</b>\n\n';buttons=[]
    for r in rows:text+=f"{r['item']}: ${r['price']:.2f}\n";buttons.append([(f'🛒 خرید {r["item"]}',f'market:BUY:{r["item"]}'),(f'💵 فروش {r["item"]}',f'market:SELL:{r["item"]}')])
    buttons.append([('🏠 خانه','home')]);await update.message.reply_text(text,parse_mode='HTML',reply_markup=ikb(buttons))

async def trade(query,side,item):
    uid=query.from_user.id;u=get_user(uid);c=get_country(u['country']);p=q('SELECT price FROM market WHERE item=?',(item,),one=True)['price'];amount=100;total=p*amount
    if side=='BUY':
        if c['money']<total:return await query.answer('پول کافی نیست',show_alert=True)
        q(f'UPDATE countries SET money=money-?,{item}={item}+? WHERE code=?',(total,amount,c['code']),commit=True)
    else:
        if c[item]<amount:return await query.answer('موجودی کافی نیست',show_alert=True)
        q(f'UPDATE countries SET money=money+?,{item}={item}-? WHERE code=?',(total,amount,c['code']),commit=True)
    q('UPDATE market SET price=? WHERE item=?',(max(1,p*random.uniform(.96,1.04)),item),commit=True);progress(uid,'trade');await query.answer('معامله انجام شد')

async def industry(update,context):
    uid=uid_of(update);u=get_user(uid);c=get_country(u['country']);cities=q('SELECT SUM(industry) n FROM cities WHERE owner=?',(uid,),one=True)['n'] or 0;income=15000+cities*4000;steel=1000+cities*250;oil=700+cities*100;q('UPDATE countries SET money=money+?,steel=steel+?,oil=oil+?,power=power+500 WHERE code=?',(income,steel,oil,c['code']),commit=True);await update.message.reply_text(f'🏭 تولید انجام شد.\n\n💰 +${income:,}\n🏭 +{steel} فولاد\n🛢️ +{oil} نفت',reply_markup=kb(ECONOMY_MENU))

async def politics(update,context):
    uid=uid_of(update);u=get_user(uid);await update.message.reply_text(f'🏛️ <b>سیاست داخلی</b>\n\n😊 رضایت: {u["approval"]}%\n⭐ اعتبار: {u["reputation"]}\n\nبا توسعه شهرها، اقتصاد و امنیت رضایت را بالا نگه دارید.',parse_mode='HTML',reply_markup=kb(ECONOMY_MENU))

async def events_screen(update,context):
    uid=uid_of(update);title,body,effect=random.choice(EVENTS);u=get_user(uid);c=get_country(u['country'])
    if effect=='eco':q('UPDATE countries SET money=money+150000,power=power+5000 WHERE code=?',(u['country'],),commit=True)
    elif effect=='res':q('UPDATE countries SET oil=oil+8000,steel=steel+6000 WHERE code=?',(u['country'],),commit=True)
    elif effect=='crisis':q('UPDATE users SET approval=MAX(0,approval-8) WHERE user_id=?',(uid,),commit=True)
    elif effect=='tech':q('UPDATE tech SET progress=MIN(100,progress+40) WHERE user_id=?',(uid,),commit=True)
    q('INSERT INTO events(user_id,title,body,created) VALUES(?,?,?,?)',(uid,title,body,iso(now())),commit=True);await update.message.reply_text(f'{title}\n\n{body}',reply_markup=kb(WAR_MENU))

async def news_screen(update,context):
    rows=q('SELECT text FROM news ORDER BY id DESC LIMIT 15',all=True);text='📰 <b>خبرگزاری جهان</b>\n\n'+('\n'.join('• '+r['text'] for r in rows) if rows else 'هنوز خبری ثبت نشده است.');await update.message.reply_text(text,parse_mode='HTML',reply_markup=kb(ECONOMY_MENU))

async def rankings(update,context):
    rows=q('SELECT u.name,c.flag,c.name country,u.season_score FROM users u JOIN countries c ON c.code=u.country ORDER BY u.season_score DESC,u.score DESC LIMIT 20',all=True);text='🏆 <b>رنکینگ جهانی</b>\n\n';
    for i,r in enumerate(rows,1):text+=f'{i}. {r["flag"]} {escape(r["name"])} — {r["season_score"]:,}\n'
    await update.message.reply_text(text,parse_mode='HTML',reply_markup=kb(WAR_MENU))

async def league(update,context):
    season=q("SELECT value FROM state WHERE key='season'",one=True)['value'];await update.message.reply_text(f'🏅 <b>فصل {season}</b>\n\nفصل ۳۰ روزه است. امتیاز جنگ، اقتصاد و فناوری رتبه فصل را تعیین می‌کند.',parse_mode='HTML',reply_markup=kb(ECONOMY_MENU))

async def missions(update,context):
    uid=uid_of(update);missions_seed(uid);day=now().strftime('%Y-%m-%d');rows=q('SELECT * FROM missions WHERE user_id=? AND day=?',(uid,day),all=True);text='🎯 <b>مأموریت‌ها</b>\n\n'
    for r in rows:text+=f'{r["title"]}: {r["progress"]}/{r["target"]} — 💰 {r["reward"]:,}\n'
    await update.message.reply_text(text,parse_mode='HTML',reply_markup=kb(PROFILE_MENU))

async def achievements(update,context):
    rows=q('SELECT title FROM achievements WHERE user_id=?',(uid_of(update),),all=True);await update.message.reply_text('🏅 <b>دستاوردها</b>\n\n'+('\n'.join('🏅 '+r['title'] for r in rows) if rows else 'هنوز دستاوردی کسب نشده.'),parse_mode='HTML',reply_markup=kb(PROFILE_MENU))

async def daily(update,context):
    uid=uid_of(update);u=get_user(uid);today=now().strftime('%Y-%m-%d')
    if u['last_daily']==today:return await update.message.reply_text('⏳ پاداش امروز قبلاً دریافت شده.',reply_markup=kb(PROFILE_MENU))
    q('UPDATE users SET last_daily=?,score=score+200,season_score=season_score+200 WHERE user_id=?',(today,uid),commit=True);q('UPDATE countries SET money=money+100000 WHERE code=?',(u['country'],),commit=True);await update.message.reply_text('🎁 ${100,000} و ۲۰۰ امتیاز دریافت شد.',reply_markup=kb(PROFILE_MENU))

async def profile(update,context):
    uid=uid_of(update);u=get_user(uid);c=get_country(u['country']);await update.message.reply_text(f'👤 <b>{escape(u["name"])}</b>\n\n{c["flag"]} {c["name"]}\n⭐ سطح: {u["level"]}\n🏆 امتیاز: {u["score"]:,}\n🏅 فصل: {u["season_score"]:,}\n😊 رضایت: {u["approval"]}%\n⚡ قدرت: {military_power(uid):,.0f}',parse_mode='HTML',reply_markup=kb(PROFILE_MENU))

async def guide(update,context):await update.message.reply_text('📜 <b>راهنما</b>\n\n۴ دکمه اصلی فقط رابط ورود هستند. تمام امکانات داخل زیرمنوها قرار گرفته‌اند. اقتصاد، شهرها، فناوری، ارتش، جنگ، جاسوسی، دیپلماسی، بازار، مأموریت، دستاورد، رویداد و لیگ فعال هستند.',parse_mode='HTML',reply_markup=kb(PROFILE_MENU))
async def settings(update,context):await update.message.reply_text('⚙️ <b>تنظیمات</b>\n\nRailway + SQLite/WAL\nWORLD WAR V5\nرابط اصلی: ۴ دکمه',parse_mode='HTML',reply_markup=kb(PROFILE_MENU))
async def advisor(update,context):await update.message.reply_text('🧠 <b>مشاور</b>\n\nپیشنهاد: ابتدا اقتصاد و لجستیک را تقویت کن، سپس فناوری و ارتش را توسعه بده و قبل از جنگ پدافند را بالا ببر.',parse_mode='HTML',reply_markup=kb(PROFILE_MENU))

async def text_router(update,context):
    uid=uid_of(update);text=update.message.text
    if not get_user(uid):return await update.message.reply_text('ابتدا /start را بزنید.')
    seed(uid)
    if text in ('🔙 منوی اصلی','🏠 منوی اصلی'):return await update.message.reply_text('🏠 منوی اصلی',reply_markup=kb(MAIN_MENU))
    routes={
        '⚔️ جنگ و عملیات':lambda: update.message.reply_text('⚔️ <b>جنگ و عملیات</b>',parse_mode='HTML',reply_markup=kb(WAR_MENU)),
        '🏭 کشور و اقتصاد':lambda: update.message.reply_text('🏭 <b>کشور و اقتصاد</b>',parse_mode='HTML',reply_markup=kb(ECONOMY_MENU)),
        '🪖 ارتش و تجهیزات':lambda: update.message.reply_text('🪖 <b>ارتش و تجهیزات</b>',parse_mode='HTML',reply_markup=kb(ARMY_MENU)),
        '👤 پروفایل و تنظیمات':lambda: update.message.reply_text('👤 <b>پروفایل و تنظیمات</b>',parse_mode='HTML',reply_markup=kb(PROFILE_MENU)),
        '🎯 حمله':lambda:war_screen(update,context),'🕵️ جاسوسی':lambda:spy_screen(update,context),'🤝 دیپلماسی':lambda:diplomacy_screen(update,context),'🌍 رویدادهای جهان':lambda:events_screen(update,context),'🏆 رنکینگ':lambda:rankings(update,context),
        '🌍 کشور من':lambda:country_screen(update,context),'🗺️ شهرها':lambda:cities_screen(update,context),'🏭 صنعت':lambda:industry(update,context),'🌐 بازار جهانی':lambda:market_screen(update,context),'🧬 فناوری':lambda:tech_screen(update,context),'🏛️ سیاست داخلی':lambda:politics(update,context),'📰 اخبار جهان':lambda:news_screen(update,context),'🏅 لیگ و فصل':lambda:league(update,context),
        '📊 ارتش':lambda:army_screen(update,context),'🛒 تجهیزات':lambda:equipment_screen(update,context),'🎖️ فرماندهان':lambda:generals_screen(update,context),'✈️ نیروی هوایی':lambda:army_screen(update,context),'⚓ نیروی دریایی':lambda:army_screen(update,context),
        '👤 پروفایل':lambda:profile(update,context),'🎯 مأموریت‌ها':lambda:missions(update,context),'🏅 دستاوردها':lambda:achievements(update,context),'🎁 پاداش روزانه':lambda:daily(update,context),'🧠 مشاور':lambda:advisor(update,context),'📜 راهنما':lambda:guide(update,context),'⚙️ تنظیمات':lambda:settings(update,context),
    }
    fn=routes.get(text)
    if fn:return await fn()

async def callback(update,context):
    query=update.callback_query;await query.answer();data=query.data;uid=query.from_user.id
    if data.startswith('country:'):return await choose_country(query,data.split(':')[1])
    if data=='home':return await query.message.reply_text('🏠 منوی اصلی',reply_markup=kb(MAIN_MENU))
    if data.startswith('city:'):return await city_callback(query,int(data.split(':')[1]))
    if data.startswith('cityup:'):return await city_upgrade(query,int(data.split(':')[1]))
    if data.startswith('tech:'):return await tech_upgrade(query,data.split(':',1)[1])
    if data.startswith('buy:'):return await buy(query,data.split(':',1)[1])
    if data.startswith('attack:'):return await launch_attack(query,int(data.split(':')[1]))
    if data.startswith('dip:'):return await dip_target(query,int(data.split(':')[1]))
    if data.startswith('dipact:'):
        _,rel,target=data.split(':');return await dip_action(query,rel,int(target))
    if data.startswith('spy:'):return await spy_target(query,int(data.split(':')[1]))
    if data.startswith('spyact:'):
        _,op,target=data.split(':');return await spy_action(query,op,int(target))
    if data.startswith('market:'):
        _,side,item=data.split(':');return await trade(query,side,item)

async def tick(context):
    for r in q('SELECT user_id FROM users',all=True):
        uid=r['user_id'];seed(uid)
        u=get_user(uid);c=get_country(u['country']);cities=q('SELECT COALESCE(SUM(industry),0) n FROM cities WHERE owner=?',(uid,),one=True)['n'];income=(10000+cities*2500)*COUNTRIES[u['country']][4]
        q('UPDATE countries SET money=money+?,food=MAX(0,food-?),power=power+? WHERE code=?',(income,max(500,q('SELECT soldiers FROM armies WHERE user_id=?',(uid,),one=True)['soldiers']//20),3000,u['country']),commit=True)
        q('UPDATE tech SET progress=MIN(100,progress+5) WHERE user_id=?',(uid,),commit=True)
        if random.random()<.02:
            title,body,effect=random.choice(EVENTS);events_effect(uid,effect,title,body)
    season=q("SELECT value FROM state WHERE key='season_end'",one=True)
    if season and datetime.fromisoformat(season['value'])<=now():
        s=int(q("SELECT value FROM state WHERE key='season'",one=True)['value'])+1;q("UPDATE state SET value=? WHERE key='season'",(str(s),),commit=True);q("UPDATE state SET value=? WHERE key='season_end'",(iso(now()+timedelta(days=30)),),commit=True);add_news(f'🏁 فصل {s} آغاز شد.')

def events_effect(uid,effect,title,body):
    u=get_user(uid)
    if effect=='eco':q('UPDATE countries SET money=money+150000 WHERE code=?',(u['country'],),commit=True)
    elif effect=='res':q('UPDATE countries SET oil=oil+8000,steel=steel+6000 WHERE code=?',(u['country'],),commit=True)
    elif effect=='crisis':q('UPDATE users SET approval=MAX(0,approval-8) WHERE user_id=?',(uid,),commit=True)
    elif effect=='tech':q('UPDATE tech SET progress=MIN(100,progress+40) WHERE user_id=?',(uid,),commit=True)
    q('INSERT INTO events(user_id,title,body,created) VALUES(?,?,?,?)',(uid,title,body,iso(now())),commit=True)

async def admin(update,context):
    uid=uid_of(update)
    if not is_admin(uid):return await update.message.reply_text('⛔ دسترسی غیرمجاز.')
    n=q('SELECT COUNT(*) n FROM users',one=True)['n'];w=q("SELECT COUNT(*) n FROM wars WHERE status='ACTIVE'",one=True)['n'];await update.message.reply_text(f'👑 <b>پنل مدیریت</b>\n\n👥 بازیکنان: {n}\n⚔️ جنگ‌های فعال: {w}',parse_mode='HTML')

async def cancel(update,context):await update.message.reply_text('لغو شد.',reply_markup=kb(MAIN_MENU))


def main():
    init_db()
    if not BOT_TOKEN:raise RuntimeError('TELEGRAM_BOT_TOKEN is not set')
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start',start));app.add_handler(CommandHandler('admin',admin));app.add_handler(CommandHandler('cancel',cancel));app.add_handler(CallbackQueryHandler(callback));app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text_router))
    if app.job_queue:app.job_queue.run_repeating(tick,interval=60,first=10)
    log.info('WORLD WAR V5 started')
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__=='__main__':main()
