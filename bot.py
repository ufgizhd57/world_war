import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from openai import AsyncOpenAI
from sqlalchemy import DateTime, Float, Integer, String, Text, select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("gamefa-ai")

BOT_TOKEN = os.environ["BOT_TOKEN"]
DATABASE_URL = os.environ["DATABASE_URL"]
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-mini")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
ADMIN_IDS = {int(x.strip()) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip().isdigit()}

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
Session = async_sessionmaker(engine, expire_on_commit=False)
ai = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
router = Router()

class Base(DeclarativeBase):
    pass

class News(Base):
    __tablename__ = "news"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_message_id: Mapped[int | None] = mapped_column(Integer)
    source_chat_id: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(500), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    normalized_text: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str | None] = mapped_column(String(1000))
    category: Mapped[str | None] = mapped_column(String(50))
    ai_summary: Mapped[str | None] = mapped_column(Text)
    ai_data: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[str | None] = mapped_column(Text)  # JSON list; portable without pgvector
    added_by: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Pending(Base):
    __tablename__ = "pending_news"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer)
    source_text: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

def admin(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id in ADMIN_IDS)

def norm(text: str) -> str:
    text = text.lower()
    for a, b in {"ي":"ی", "ى":"ی", "ك":"ک", "ۀ":"ه", "ة":"ه", "\u200c":" "}.items():
        text = text.replace(a, b)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^\w\s\u0600-\u06ff]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def lexical_score(a: str, b: str) -> float:
    na, nb = norm(a), norm(b)
    if not na or not nb: return 0.0
    sa, sb = set(na.split()), set(nb.split())
    jac = len(sa & sb) / max(1, len(sa | sb))
    seq = SequenceMatcher(None, na, nb).ratio()
    return 0.55 * jac + 0.45 * seq

def buttons(pid: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 مشاهده مشابه‌ها", callback_data=f"similar:{pid}")],
        [InlineKeyboardButton(text="✅ ثبت به عنوان خبر جدید", callback_data=f"save:{pid}"),
         InlineKeyboardButton(text="❌ رد", callback_data=f"reject:{pid}")],
    ])

def extract_forward(message: Message):
    text = (message.text or message.caption or "").strip()
    if not text and message.forward_from_chat:
        text = ""
    url = None
    if message.forward_from_message_id and message.forward_from_chat:
        chat = message.forward_from_chat
        if chat.username:
            url = f"https://t.me/{chat.username}/{message.forward_from_message_id}"
    return text, url

async def ai_analyze(text: str) -> dict:
    if not ai:
        return {"category":"نامشخص", "topic":"", "entities":[], "event":"", "summary":"", "keywords":[]}
    prompt = f'''تو دستیار تحریریه فارسی گیمفا هستی. متن خبر زیر را تحلیل کن.
فقط JSON معتبر بده با کلیدهای category, topic, entities, event, dates, summary, keywords.
category فقط یکی از: بازی، فیلم و سریال، فناوری، سایر.
entities آرایه‌ای از نام بازی/فیلم/سریال/شرکت/شخص باشد.
summary حداکثر 2 جمله فارسی باشد.
خبر:
{text[:12000]}'''
    try:
        r = await ai.responses.create(model=OPENAI_MODEL, input=prompt)
        raw = r.output_text.strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw).strip()
        return json.loads(raw)
    except Exception as e:
        log.exception("AI analysis failed: %s", e)
        return {"category":"نامشخص", "topic":"", "entities":[], "event":"", "dates":[], "summary":"", "keywords":[]}

async def embedding(text: str):
    if not ai: return None
    try:
        r = await ai.embeddings.create(model=EMBEDDING_MODEL, input=text[:8000])
        return r.data[0].embedding
    except Exception as e:
        log.exception("Embedding failed: %s", e)
        return None

def cosine(a, b):
    if not a or not b: return 0.0
    dot = sum(x*y for x,y in zip(a,b)); na = sum(x*x for x in a) ** .5; nb = sum(y*y for y in b) ** .5
    return dot / (na*nb) if na and nb else 0.0

async def candidates(text: str):
    n = norm(text)
    words = [w for w in n.split() if len(w) >= 4][:10]
    async with Session() as s:
        if words:
            stmt = select(News).where(or_(*[News.normalized_text.ilike(f"%{w}%") for w in words])).order_by(News.created_at.desc()).limit(400)
        else:
            stmt = select(News).order_by(News.created_at.desc()).limit(400)
        return (await s.execute(stmt)).scalars().all()

async def score_matches(text: str, ai_data: dict):
    emb = await embedding(text)
    rows = await candidates(text)
    out=[]
    new_entities=set(x.lower() for x in ai_data.get("entities",[]) if isinstance(x,str))
    for row in rows:
        lexical = lexical_score(text, row.text)
        semantic = 0.0
        if emb and row.embedding:
            try: semantic = cosine(emb, json.loads(row.embedding))
            except Exception: pass
        old_entities=set()
        try: old_entities=set(x.lower() for x in json.loads(row.ai_data or "{}").get("entities",[]))
        except Exception: pass
        entity = len(new_entities & old_entities) / max(1, len(new_entities | old_entities)) if new_entities and old_entities else 0.0
        score = (0.35*lexical + 0.50*semantic + 0.15*entity) if emb else (0.75*lexical + 0.25*entity)
        if score >= 0.38: out.append((score,row))
    return sorted(out,key=lambda x:x[0],reverse=True)[:5]

async def save_news(user_id: int, text: str, url: str | None, ai_data: dict):
    emb = await embedding(text)
    title = next((x.strip() for x in text.splitlines() if x.strip()), text[:180])[:500]
    row = News(title=title, text=text, normalized_text=norm(text), url=url, category=ai_data.get("category"), ai_summary=ai_data.get("summary"), ai_data=json.dumps(ai_data,ensure_ascii=False), embedding=json.dumps(emb) if emb else None, added_by=user_id)
    async with Session() as s:
        s.add(row); await s.commit(); await s.refresh(row)
    return row

@router.message(CommandStart())
async def start(message: Message):
    if not admin(message): return await message.answer("⛔ دسترسی ندارید.")
    await message.answer("🤖 دستیار هوشمند گیمفا فعال است. خبر را همین‌جا بفرست یا فوروارد کن.")

@router.message(Command("stats"))
async def stats(message: Message):
    if not admin(message): return
    async with Session() as s:
        total = await s.scalar(select(func.count(News.id)))
        cats = (await s.execute(select(News.category, func.count(News.id)).group_by(News.category))).all()
    text = "📊 آمار گیمفا\n\n📰 کل اخبار: %s\n" % total
    for c,n in cats: text += f"• {c or 'نامشخص'}: {n}\n"
    await message.answer(text)

@router.message(Command("search"))
async def search(message: Message):
    if not admin(message): return
    q=message.text.partition(" ")[2].strip()
    if not q: return await message.answer("مثال: /search GTA VI")
    async with Session() as s:
        rows=(await s.execute(select(News).where(News.normalized_text.ilike(f"%{norm(q)}%")).order_by(News.created_at.desc()).limit(10))).scalars().all()
    if not rows: return await message.answer("🔎 موردی پیدا نشد.")
    await message.answer("\n\n".join(f"#{r.id} — {r.title}\n{r.url or ''}" for r in rows))

@router.callback_query(F.data.startswith("save:"))
async def save_callback(c: CallbackQuery):
    if c.from_user.id not in ADMIN_IDS: return await c.answer("دسترسی ندارید", show_alert=True)
    pid=int(c.data.split(":")[1])
    async with Session() as s:
        p=await s.get(Pending,pid)
    if not p: return await c.answer("این درخواست منقضی شده.", show_alert=True)
    ai_data=await ai_analyze(p.source_text)
    row=await save_news(p.user_id,p.source_text,p.source_url,ai_data)
    async with Session() as s:
        await s.delete(p); await s.commit()
    await c.message.edit_text(f"✅ خبر ثبت شد.\n\nشناسه: #{row.id}\nدسته: {row.category or 'نامشخص'}\n{row.ai_summary or ''}")
    await c.answer("ثبت شد")

@router.callback_query(F.data.startswith("reject:"))
async def reject_callback(c: CallbackQuery):
    if c.from_user.id not in ADMIN_IDS: return
    pid=int(c.data.split(":")[1])
    async with Session() as s:
        p=await s.get(Pending,pid)
        if p: await s.delete(p); await s.commit()
    await c.message.edit_text("❌ خبر رد شد و ذخیره نشد.")
    await c.answer("رد شد")

@router.callback_query(F.data.startswith("similar:"))
async def similar_callback(c: CallbackQuery):
    if c.from_user.id not in ADMIN_IDS: return
    pid=int(c.data.split(":")[1])
    async with Session() as s: p=await s.get(Pending,pid)
    if not p: return await c.answer("منقضی شده", show_alert=True)
    data=await ai_analyze(p.source_text); matches=await score_matches(p.source_text,data)
    if not matches: return await c.answer("مورد مشابهی پیدا نشد", show_alert=True)
    txt="🔎 مشابه‌ترین اخبار:\n\n"+"\n\n".join(f"{i+1}) {round(sc*100)}٪ — {r.title}\n{r.url or ''}" for i,(sc,r) in enumerate(matches))
    await c.message.answer(txt); await c.answer()

@router.message(F.text | F.caption)
async def check(message: Message):
    if not admin(message): return
    text,url=extract_forward(message)
    if not text or text.startswith("/"): return
    data=await ai_analyze(text)
    matches=await score_matches(text,data)
    top=matches[0][0] if matches else 0
    if top>=0.72: level="🔴 احتمال تکراری بودن بسیار زیاد است"
    elif top>=0.52: level="🟠 خبر مشابه پیدا شد؛ بررسی کن"
    else: level="🟢 احتمالاً خبر جدید است"
    p=Pending(user_id=message.from_user.id,source_text=text,source_url=url)
    async with Session() as s: s.add(p); await s.commit(); await s.refresh(p)
    entities=", ".join(data.get("entities",[])[:8]) or "—"
    similar=""
    if matches:
        similar="\n\n🔎 مشابه‌ترین خبر:\n"+f"{matches[0][1].title}\nشباهت: {round(matches[0][0]*100)}٪\n{matches[0][1].url or ''}"
    await message.answer(f"🧠 تحلیل هوشمند گیمفا\n\n{level}\n\n📌 موضوع: {data.get('topic') or '—'}\n🏷 دسته: {data.get('category') or '—'}\n🎯 موجودیت‌ها: {entities}\n📝 خلاصه: {data.get('summary') or '—'}{similar}", reply_markup=buttons(p.id))

@router.channel_post()
async def channel_post(message: Message):
    text,url=extract_forward(message)
    if not text: return
    # Auto-index new channel posts; no AI analysis is required if no API key.
    async with Session() as s:
        exact=await s.scalar(select(News).where(News.normalized_text==norm(text)).limit(1))
        if exact: return
    data=await ai_analyze(text)
    await save_news(0,text,url,data)

async def main():
    await init_db()
    bot=Bot(BOT_TOKEN)
    dp=Dispatcher(); dp.include_router(router)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
