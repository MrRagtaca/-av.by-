import asyncio
import requests
import json
import os
from lxml import html
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

from config import BOT_TOKEN, RECIPIENTS, SEARCH_URL, CHECK_INTERVAL

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

HISTORY_FILE = "sent_ads.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except: return set()
    return set()

def save_history(history_set):
    limited = list(history_set)[-3000:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(limited, f)

def parse_avby():
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        print(f"⏳ Стучусь на av.by по ссылке: {SEARCH_URL[:50]}...")
        resp = requests.get(SEARCH_URL, headers=headers, timeout=20)
        
        if resp.status_code != 200:
            print(f"❌ Ошибка сайта: статус {resp.status_code}")
            return []

        tree = html.fromstring(resp.text)
        items = tree.xpath("//div[contains(@class, 'listing-item')]")
        print(f"🔍 Найдено на странице: {len(items)} объявлений")
        
        found_ads = []
        for item in items:
            try:
                link_elem = item.xpath(".//a[contains(@class, 'listing-item__link')]")
                if not link_elem: continue
                
                link = link_elem[0].get('href')
                if link.startswith('/'):
                    link = "https://cars.av.by" + link
                
                title = item.xpath(".//span[contains(@class, 'listing-item__title')]/text()")
                title = title[0].strip() if title else "Без названия"
                
                price = item.xpath(".//div[contains(@class, 'listing-item__price')]/text()")
                price = price[0].strip() if price else "Цена не указана"
                
                ad_id = link.split('/')[-1]
                
                found_ads.append({
                    "id": ad_id,
                    "title": title,
                    "price": price,
                    "link": link
                })
            except Exception as e:
                continue
        return found_ads
    except Exception as e:
        print(f"❌ Ошибка парсинга: {e}")
        return []

async def monitor():
    print("🚀 Мониторинг av.by запущен...")
    while True:
        ads = parse_avby()
        history = load_history()
        
        new_ads_count = 0
        for ad in ads:
            if ad["id"] not in history:
                msg = (
                    f"🚗 <b>Новое объявление!</b>\n\n"
                    f"<b>{ad['title']}</b>\n"
                    f"💰 Цена: {ad['price']}\n"
                    f"🔗 <a href='{ad['link']}'>Открыть на av.by</a>"
                )
                
                for user_id in RECIPIENTS:
                    try:
                        await bot.send_message(chat_id=user_id, text=msg, parse_mode="HTML")
                    except Exception as e:
                        print(f"Ошибка отправки {user_id}: {e}")
                
                history.add(ad["id"])
                new_ads_count += 1
        
        if new_ads_count > 0:
            save_history(history)
            print(f"✅ Отправлено новых объявлений: {new_ads_count}")
        else:
            print("😴 Новых объявлений нет.")
        
        print(f"💤 Отдыхаю {CHECK_INTERVAL} секунд...")
        await asyncio.sleep(CHECK_INTERVAL)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id in RECIPIENTS:
        await message.answer("Привет! Я слежу за Opel Grandland X на av.by. Буду присылать новые объявления.")
    else:
        await message.answer("Привет! У тебя нет доступа к этому боту.")

async def main():
    asyncio.create_task(monitor())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
