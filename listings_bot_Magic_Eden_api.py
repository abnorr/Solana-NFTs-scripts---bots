import requests
import json
from decimal import Decimal
import discord
from time import sleep
import urllib.request
from discord import Webhook, AsyncWebhookAdapter
import aiohttp
import asyncio
import cloudscraper
from json.decoder import JSONDecodeError
from pprint import pprint as P
import sys
from datetime import datetime, timedelta
import traceback

# ###############
# CONSTANTS
COINGECKO = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
LAMPORTS = 1000000000

# In case script is started and the json is corrupt or empty or has only one entry, then we consider that sales to be "the old way"
# In the old way, we simply consider all PAST transactions as processed
# However in the new way, we will consider missing ids as valuable and those need to be processed
IS_NEW_WAY = False
REPORTED_DICT_LENGTH = False

# ###############
# SCRIPT_RELATED

SALES_FILE_NAME = "dump_listings.txt"
URL = 'https://api-mainnet.magiceden.dev/v2/collections/collectionName/listings?offset=0&limit=20'
WEBHOOK_URL = "INSERT_DISCORD_WEBHOOK_URL"


# ###############

scraper = cloudscraper.create_scraper(
    browser = 'chrome',
    interpreter='nodejs',
    captcha={
     'provider': '2captcha',
     'api_key': 'c28aed587a7e8eb9b6baf7cb6d61ec3f'
   }    
)

class TooManyRequests(Exception):
    timeout_val = 1
    def __init__(self, timeout_val):
        self.timeout_val = timeout_val

def beautify(url):
    res = scraper.get(url)
    P(res.status_code)
    if res.ok:
        return json.loads(res.text)
    if res.status_code==429:
        P(res.text)
        P(res)
        raise TooManyRequests(10)
    return False

def listings():
    global IS_NEW_WAY, REPORTED_DICT_LENGTH
    cnt = 0
    scriptStartedAt = datetime.utcnow()
    P(str(scriptStartedAt))
    while True:
        sleep(1)
        if (cnt > 32000):
            cnt = 0
        if (cnt % 30 == 0):
            try:
                P(str(datetime.utcnow()))
                solprice = requests.get(COINGECKO, headers = {"accept":"application/json"})
                P(solprice.json()['solana']['usd'])
                data = beautify(URL)
            except TooManyRequests as e:
                print("TooManyRequests")
                sleep(e.timeout_val)
                sleep(1)
                continue
            except JSONDecodeError as e:
                P("=========")
                P("=========")
                print(str(e))
                print(traceback.format_exc())
                P("=========")
                P("=========")
                continue
        if not data:
            print("Data or data2 are not filled up, continuing...")
            continue
        cnt += 1
        
        file_content = None
        with open(SALES_FILE_NAME) as sales_file:
            file_content = sales_file.read()
        file_dict = {}
        if file_content is not None:
            try:
                file_dict = json.loads(file_content)
                if not REPORTED_DICT_LENGTH:
                    print(f"Listings dict length = {len(file_dict)}")
                    REPORTED_DICT_LENGTH = True
                if len(file_dict) > 0:
                    IS_NEW_WAY = True
            except:
                pass
        crtdict = [20]
        for i in range(len(crtdict)):
            crtdict = data[i]
            crtTransactionTime = datetime.strptime(crtdict['rarity']['moonrank']['crawl']['created'], "%Y-%m-%dT%H:%M:%S.%fZ")
            deltaOfTime = crtTransactionTime - scriptStartedAt
            crt_pda = crtdict['pdaAddress']
            if deltaOfTime.days < 0:
                if crt_pda in file_dict:
                    continue
                if not IS_NEW_WAY:
                    file_dict[crt_pda] = data[i]
                    continue
            P(str(crtTransactionTime))
            if 'pdaAddress' in str(data[i]):
                P('New Listing Found!')
                img = crtdict['extra']['img']
                rank = crtdict['rarity']['moonrank']['rank']
                price = crtdict['price']
                priceEQ1 = round(float(solprice.json()['solana']['usd']) * float(price), 2)
                priceEQ = "$" + str(priceEQ1)
                seller_address = crtdict['seller']
                token_mint = crtdict['tokenMint']
                mint_token = 'https://magiceden.io/item-details/' + str(token_mint)
                seller_add_exp = 'https://explorer.solana.com/address/' + str(seller_address)
                rank = crtdict['rarity']['moonrank']['rank']
                P(priceEQ)
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                asyncio.run(postWebhook(mint_token, price, img, priceEQ, seller_add_exp, rank))
                file_dict[crt_pda]=data[i]
        with open(SALES_FILE_NAME, "w") as sales_file:
            sales_file.write(json.dumps(file_dict, indent = 2))

async def postWebhook(mint_token, price, img, priceEQ, seller_add_exp, rank):
    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(WEBHOOK_URL, adapter = AsyncWebhookAdapter(session))
        embed = discord.Embed(
            title = '',
            description = '',
            colour=discord.Colour(0x9933FF)
        )
        msg = "NameOfYourNFT or use the metadata → LISTED"
        msg2 = str(price) + ' S◎L' + ' `(' + str(priceEQ) + " USD" + ')`'
        embed.set_author(name = msg)
        embed.add_field(name = "Price", value = msg2, inline = False)
        embed.add_field(name = "View Token", value = '[NFT](' + mint_token+ ') ⧉', inline = True)
        embed.add_field(name = "Seller", value = '[Address](' + seller_add_exp+ ') ⧉', inline = True)
        embed.add_field(name = "Rank", value = rank, inline = True)
        text = 'Listed on Magic Eden'
        embed.set_footer(text = f"{text}", icon_url = 'https://i.postimg.cc/j2TbqJ3x/favicon.png%27')
        embed.set_thumbnail(url = img)
        sleep(1)
        await webhook.send(embed = embed)     
listings()