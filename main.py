#!/usr/bin/env python3
"""SST TRADER v21 ULTIMATE (1777230342) FINAL — STABLE REBUILD"""
import os, logging, requests, random, asyncio, threading, time, json as json_module
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from telegram.constants import ParseMode

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN: logger.error("No BOT_TOKEN"); exit(1)
SIGNALS_CHANNEL_ID = os.getenv('SIGNALS_CHANNEL_ID','')
SUPPORT_LINK = "https://t.me/+Gy_Y6ddZ4KBlZTI6"
ADMIN_ID = os.getenv('ADMIN_IDS','254409923')

ALL_TOKENS = ['BTC','ETH','SOL','BNB','XRP','ADA','DOGE','TAO','FET','RENDER','PEPE','WIF','BONK','ARB','OP','SUI','SEI','TIA','APT','INJ','RUNE']
BASE_PRICES = {'BTC':78000,'ETH':2300,'SOL':140,'BNB':580,'XRP':0.5,'DOGE':0.15,'ADA':0.45,'TAO':580,'FET':0.9,'RENDER':8,'PEPE':0.000001,'WIF':2.5,'BONK':0.00002,'ARB':0.8,'OP':2,'SUI':1.5,'SEI':0.5,'TIA':10,'APT':12,'INJ':35,'RUNE':6}

STRATEGIES = {
    'dca':{'name':'💰 DCA','win':80,'profit':1.0,'price':0},
    'scalp':{'name':'⚡ Скальпинг','win':65,'profit':3.0,'price':0},
    'trend':{'name':'📈 Тренд','win':68,'profit':2.5,'price':0},
    'ai':{'name':'🤖 AI-Пилот','win':75,'profit':2.0,'price':0},
    'martin':{'name':'🎲 Мартингейл','win':85,'profit':5.0,'price':500},
    'breakout':{'name':'💥 Пробой','win':62,'profit':3.5,'price':300},
    'arb':{'name':'🔄 Арбитраж','win':90,'profit':0.5,'price':800},
}

SUBSCRIPTIONS = {
    'demo':{'name':'🆓 Demo','price':0},
    'starter':{'name':'🚀 Starter','price':50},
    'pro':{'name':'⚡ Pro','price':150},
    'ai_max':{'name':'🤖 AI Max','price':400},
}

SST_PACKAGES = {'sst_1000':{'sst':1000,'rub':490},'sst_3000':{'sst':3000,'rub':1290}}
DEMO_EXTEND = {'ext_12h':{'hours':12,'sst':200},'ext_24h':{'hours':24,'sst':350}}

DATA_FILE = 'sst_data.json'
users = {}
open_trades = {}
trade_id_counter = 0

def save_data():
    try:
        with open(DATA_FILE,'w') as f:
            json_module.dump({'users':users,'trades':open_trades,'counter':trade_id_counter},f)
    except: pass

def load_data():
    global users, open_trades, trade_id_counter
    try:
        with open(DATA_FILE) as f:
            d=json_module.load(f)
            users=d.get('users',{})
            open_trades=d.get('trades',{})
            trade_id_counter=d.get('counter',0)
    except: pass

load_data()

def get_user(uid):
    uid=str(uid)
    if uid not in users:
        users[uid]={'name':None,'age':None,'coins':1000,'profit':0,'trades':0,'wins':0,'losses':0,'strategy':'dca','auto':False,'sub':'demo','level':1,'xp':0,'disclaimer':False,'demo_start':datetime.now().isoformat(),'demo_hours':24}
        open_trades[uid]=[]
    return users[uid]

def check_demo(uid):
    u=get_user(uid)
    start=datetime.fromisoformat(u.get('demo_start',datetime.now().isoformat()))
    hours=u.get('demo_hours',24)
    elapsed=(datetime.now()-start).total_seconds()/3600
    return max(0,hours-elapsed)>0, max(0,hours-elapsed)

DISCLAIMER="🚨 *ВНИМАНИЕ!* 🚨\n\n24ч бесплатного демо.\n1000 SST Coins.\n\nОтправьте *ПРИНИМАЮ*."

class DexScreener:
    def get_trending(self,limit=20):
        try:
            r=requests.get("https://api.dexscreener.com/latest/dex/search?q=trending",timeout=10)
            if r.status_code==200:
                tokens=[]
                for p in r.json().get('pairs',[])[:limit]:
                    s=p.get('baseToken',{}).get('symbol','')
                    if s and s!='UNKNOWN' and len(s)<=8:
                        tokens.append({'symbol':s,'price':float(p.get('priceUsd',0)),'change':float(p.get('priceChange',{}).get('h24',0)),'liq':float(p.get('liquidity',{}).get('usd',0))})
                return tokens
        except: pass
        return []

dex=DexScreener()

def execute_trade(uid,sym,side,amount):
    u=get_user(uid);s=STRATEGIES.get(u['strategy'],STRATEGIES['dca'])
    pr=BASE_PRICES.get(sym,random.uniform(1,100))
    u['coins']-=amount
    global trade_id_counter;trade_id_counter+=1
    t={'id':trade_id_counter,'symbol':sym,'side':side,'amount':amount,'price':pr,'status':'open'}
    open_trades.setdefault(uid,[]).append(t)
    save_data()
    return t

def menu():
    return ReplyKeyboardMarkup([
        ["🚀 СТАРТ", "🤖 SST Alpha", "🎯 СИГНАЛЫ"],
        ["🔄 ТОРГОВЛЯ", "🤖 АВТО", "💰 БАЛАНС"],
        ["📈 СТРАТЕГИИ", "💎 ПОДПИСКА", "📊 ПОЗИЦИИ"],
        ["📋 ИСТОРИЯ", "🏆 РЕЙТИНГ", "🔄 РЕИНВЕСТ"],
        ["🛒 КУПИТЬ SST", "⏰ ПРОДЛИТЬ", "💎 DEMO vs REAL"],
        ["📩 СВЯЗЬ", "📊 ROI", "🧠 AI"]
    ], resize_keyboard=True)

async def start_cmd(update:Update,context:ContextTypes.DEFAULT_TYPE):
    uid=str(update.effective_user.id);u=get_user(uid)
    if not u.get('disclaimer'): await update.message.reply_text(DISCLAIMER,parse_mode=ParseMode.MARKDOWN);return
    if not u['name']: await update.message.reply_text("📝 Имя:");return
    await show_main(update,uid,u)

async def show_main(update,uid,u):
    ok,h=check_demo(uid)
    if not ok:
        await update.message.reply_text("⏰ Демо закончилось.\n🛒 Купить SST или 💎 Подписка")
        return
    s=STRATEGIES.get(u['strategy'],STRATEGIES['dca'])
    wr=(u['wins']/u['trades']*100) if u['trades']>0 else 0
    text=f"🚀 *SST TRADER v20 FINAL*\n\n👤 {u['name']} | 🏆 Lv.{u['level']}\n🪙 {u['coins']:,.0f} SST | ⏰ {h:.0f}ч\n💵 {u['profit']:+,.0f} | {s['name']}\n📊 {u['trades']} сделок | Win:{wr:.0f}%"
    await update.message.reply_text(text,parse_mode=ParseMode.MARKDOWN,reply_markup=menu())

async def handle_msg(update:Update,context:ContextTypes.DEFAULT_TYPE):
    uid=str(update.effective_user.id);text=update.message.text.strip();u=get_user(uid)
    
    if not u.get('disclaimer'):
        if 'ПРИНИМАЮ' in text.upper():u['disclaimer']=True;await update.message.reply_text("📝 Имя:");return
        await update.message.reply_text("Отправьте *ПРИНИМАЮ*");return
    
    if not u['name']:u['name']=text;await update.message.reply_text("📝 Возраст:");return
    if u['name'] and not u['age']:
        try:u['age']=int(text);await update.message.reply_text(f"✅ {u['name']}, {u['age']} лет\n🪙 1000 SST!");await show_main(update,uid,u);return
        except:await update.message.reply_text("❌ Число!");return
    
    demo_ok,demo_h=check_demo(uid)
    if not demo_ok and text not in ["🚀 СТАРТ","🛒 МАРКЕТПЛЕЙС","💎 ПОДПИСКА","⏰ ПРОДЛИТЬ ДЕМО","💰 БАЛАНС","📩 СВЯЗЬ"]:
        await update.message.reply_text("⏰ Демо закончилось.");return
    
    if text=="🚀 СТАРТ":await show_main(update,uid,u)
    elif text=="🤖 SST Alpha":
        decision = sst_ai.analyze_market()
        prediction = sst_ai.predict_best_trade(uid)
        status = sst_ai.get_ai_status()
        resp = "🐺 *SST Alpha v" + status["version"] + "*\n\n"
        resp += "📊 *Рынок:* " + decision.get("market_phase","—") + "\n"
        resp += "📈 Сентимент: " + str(int(decision.get("sentiment",50))) + "%\n"
        resp += "🎯 *Стратегия:* " + decision.get("best_strategy_name","—") + "\n"
        resp += "📊 Уверенность: " + str(int(decision.get("confidence",50))) + "%\n\n"
        resp += "🔥 *Топ-5 токенов:*\n"
        for t in decision.get("top_ideas", [])[:5]:
            score = sst_ai._score_token(t)
            em = "🟢" if score >= 50 else "🟡"
            ps = f"${t["price"]:.8f}" if t["price"] < 0.01 else f"${t["price"]:.4f}"
            resp += em + " *" + t["symbol"] + "* | " + ps + " | AI: " + str(score) + "\n"
        resp += "\n🎯 *Лучшая сделка:* " + prediction["symbol"] + " (" + str(int(prediction["amount"])) + " SST)\n"
        resp += "💬 *Совет:* " + sst_ai.get_ai_advice(uid)["personal_tip"] + "\n"
        resp += "🧠 *Точность AI:* " + status["accuracy"]
        await update.message.reply_text(resp, parse_mode=ParseMode.MARKDOWN)
    elif text=="🎯 СИГНАЛЫ":
        tokens=dex.get_trending(10)
        if tokens:
            resp="🎯 *СИГНАЛЫ*\n\n";btns=[]
            for t in tokens[:6]:
                em="🟢" if t['change']>0 else "🔴"
                resp+=f"{em} *{t['symbol']}* | ${t['price']:.6f} | {t['change']:+.1f}%\n\n"
                btns.append(InlineKeyboardButton(f"BUY {t['symbol']} 50",callback_data=f"sig_{t['symbol']}_50"))
                btns.append(InlineKeyboardButton(f"100",callback_data=f"sig_{t['symbol']}_100"))
            kb=[btns[i:i+3] for i in range(0,len(btns),3)]
            await update.message.reply_text(resp,parse_mode=ParseMode.MARKDOWN,reply_markup=InlineKeyboardMarkup(kb[:4]))
        else:await update.message.reply_text("⚠️ Нет данных")
    elif text=="🔄 ТОРГОВЛЯ":
        btns=[]
        for sym in ['BTC','ETH','SOL','BNB']:
            btns.append(InlineKeyboardButton(f"BUY {sym}",callback_data=f"trade_buy_{sym}_50"))
            btns.append(InlineKeyboardButton(f"SELL {sym}",callback_data=f"trade_sell_{sym}_50"))
        await update.message.reply_text(f"🔄 *ТОРГОВЛЯ*\n🪙 {u['coins']:,.0f} SST",parse_mode=ParseMode.MARKDOWN,reply_markup=InlineKeyboardMarkup([btns[i:i+4] for i in range(0,len(btns),4)]))
    elif text=="🤖 АВТО":u['auto']=not u['auto'];await update.message.reply_text(f"🤖 Авто: {'✅' if u['auto'] else '❌'}")
    elif text=="💰 БАЛАНС":
        wr=(u['wins']/u['trades']*100) if u['trades']>0 else 0
        await update.message.reply_text(f"💰 *БАЛАНС*\n\n🪙 {u['coins']:,.0f} SST\n💵 {u['profit']:+,.0f}\n📊 {u['trades']} сделок\n📈 Win:{wr:.0f}%",parse_mode=ParseMode.MARKDOWN)
    elif text=="📈 СТРАТЕГИИ":
        resp="📈 *СТРАТЕГИИ*\n\n";btns=[]
        for sid,s in STRATEGIES.items():
            act=" ✅" if u['strategy']==sid else ""
            resp+=f"{s['name']}{act} | Win:{s['win']}%\n"
            btns.append(InlineKeyboardButton(s['name'],callback_data=f'strat_{sid}'))
        await update.message.reply_text(resp,parse_mode=ParseMode.MARKDOWN,reply_markup=InlineKeyboardMarkup([btns[i:i+2] for i in range(0,len(btns),2)]))
    elif text=="🛒 МАРКЕТПЛЕЙС":
        resp="🛒 *МАРКЕТПЛЕЙС*\n\n";btns=[]
        for sid,s in STRATEGIES.items():
            if s['price']>0:resp+=f"{s['name']} — {s['price']} SST\n";btns.append(InlineKeyboardButton(f"Купить ({s['price']})",callback_data=f'buy_{sid}'))
        await update.message.reply_text(resp,parse_mode=ParseMode.MARKDOWN,reply_markup=InlineKeyboardMarkup([btns[i:i+2] for i in range(0,len(btns),2)]) if btns else None)
    elif text=="💎 ПОДПИСКА":
        resp="💎 *ПОДПИСКА*\n\n";kb=[]
        for sid,s in SUBSCRIPTIONS.items():resp+=f"{s['name']} — ${s['price']}/мес\n";kb.append(InlineKeyboardButton(s['name'],callback_data=f'sub_{sid}'))
        await update.message.reply_text(resp,parse_mode=ParseMode.MARKDOWN,reply_markup=InlineKeyboardMarkup([kb[i:i+2] for i in range(0,len(kb),2)]))
    elif text=="⏰ ПРОДЛИТЬ ДЕМО":
        resp=f"⏰ *ПРОДЛИТЬ*\n🪙 {u['coins']:,.0f} SST\n\n";kb=[]
        for eid,e in DEMO_EXTEND.items():resp+=f"{e['hours']}ч — {e['sst']} SST\n";kb.append(InlineKeyboardButton(f"{e['hours']}ч ({e['sst']})",callback_data=f'ext_{eid}'))
        await update.message.reply_text(resp,parse_mode=ParseMode.MARKDOWN,reply_markup=InlineKeyboardMarkup(kb))
    elif text=="📊 ПОЗИЦИИ":
        trades=open_trades.get(uid,[]);resp="📊 *ПОЗИЦИИ*\n\n"
        for t in trades:
            if t['status']=='open':resp+=f"#{t['id']} {t['symbol']} {t['side']} {t['amount']:.0f} SST\n💰 ${t['price']:.2f}\n\n"
        if not trades:resp+="Нет позиций"
        await update.message.reply_text(resp,parse_mode=ParseMode.MARKDOWN)
    elif text=="📋 ИСТОРИЯ":
        wr=(u['wins']/u['trades']*100) if u['trades']>0 else 0
        await update.message.reply_text(f"📋 *ИСТОРИЯ*\n\n📊 {u['trades']} сделок\n✅ {u['wins']} | ❌ {u['losses']}\n📈 {wr:.0f}%\n💰 {u['profit']:+,.0f}",parse_mode=ParseMode.MARKDOWN)
    elif text=="🏆 РЕЙТИНГ":
        lb=sorted(users.items(),key=lambda x:x[1]['profit'],reverse=True)[:10];resp="🏆 *ТОП-10*\n\n"
        for i,(id2,u2) in enumerate(lb,1):resp+=f"{'🥇🥈🥉'[i-1] if i<=3 else f'{i}.'} *{u2['name']}* — {u2['profit']:+,.0f}\n"
        await update.message.reply_text(resp,parse_mode=ParseMode.MARKDOWN)
    elif text=="📩 СВЯЗЬ":await update.message.reply_text(f"📩 {SUPPORT_LINK}")
    elif text.upper().startswith('BUY ') or text.upper().startswith('SELL '):
        parts=text.upper().split()
        if len(parts)>=3:
            try:
                amt=float(parts[2]);sym=parts[1];side='BUY' if parts[0]=='BUY' else 'SELL'
                if amt>u['coins']:await update.message.reply_text("❌ Недостаточно!");return
                t=execute_trade(uid,sym,side,amt)
                await update.message.reply_text(f"✅ #{t['id']} {sym} {side} {amt:.0f}\n💰 ${t['price']:.2f}",parse_mode=ParseMode.MARKDOWN)
            except:await update.message.reply_text("❌ Ошибка!")

async def btn_handler(update:Update,context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query;await q.answer();data=q.data;uid=str(q.from_user.id);u=get_user(uid)
    if data.startswith('strat_'):sid=data.replace('strat_','');u['strategy']=sid if sid in STRATEGIES else u['strategy'];await q.message.edit_text(f"✅ {STRATEGIES.get(sid,{}).get('name','?')}")
    elif data.startswith('buy_'):sid=data.replace('buy_','');s=STRATEGIES.get(sid)
    if s and u['coins']>=s['price']:u['coins']-=s['price'];await q.message.edit_text(f"✅ {s['name']} куплена!")
    elif data.startswith('sub_'):await q.message.edit_text(f"💎 Тариф выбран. Оплата: {SUPPORT_LINK}")
    elif data.startswith('ext_'):eid=data.replace('ext_','');e=DEMO_EXTEND.get(eid)
    if e and u['coins']>=e['sst']:u['coins']-=e['sst'];u['demo_hours']=u.get('demo_hours',24)+e['hours'];await q.message.edit_text(f"✅ +{e['hours']}ч!")
    elif data.startswith('sig_') or data.startswith('trade_'):
        parts=data.split('_');sym=parts[1];amt=float(parts[-1]) if len(parts)>=4 else float(parts[2])
        side='SELL' if 'sell' in data else 'BUY'
        if amt>u['coins']:await q.message.edit_text("❌ Недостаточно!");return
        t=execute_trade(uid,sym,side,amt);await q.message.edit_text(f"✅ #{t['id']} {sym} {side} {amt:.0f}")

def auto_trade():
    def run():
        while True:
            try:
                for uid,u in list(users.items()):
                    if u.get('auto') and u['coins']>0 and check_demo(uid)[0]:
                        s=STRATEGIES.get(u['strategy'],STRATEGIES['dca']);tk=random.choice(ALL_TOKENS[:10])
                        amt=min(50,u['coins']*0.1);win=random.random()<(s['win']/100)
                        pf=amt*(s['profit']/100) if win else -amt*0.02
                        if u['coins']+pf>0:u['coins']+=pf;u['trades']+=1
                        if win:u['wins']+=1
                        else:u['losses']+=1
                        u['profit']+=pf
                save_data();time.sleep(60)
            except:time.sleep(60)
    threading.Thread(target=run,daemon=True).start()

def main():
    logger.info("🚀 SST TRADER v20 FINAL STABLE")
    auto_trade()
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start',start_cmd))
    app.add_handler(CallbackQueryHandler(btn_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,handle_msg))
    logger.info("✅ READY!")
    app.run_polling()

if __name__=='__main__':main()
