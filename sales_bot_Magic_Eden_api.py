from numpy import block
import requests
import json
from decimal import Decimal
import discord
import time
from time import sleep
import tweepy
import urllib.request
from discord import Webhook, AsyncWebhookAdapter
import aiohttp
import random
import asyncio
from json.decoder import JSONDecodeError
from pprint import pprint as P
import sys
from datetime import datetime
import traceback
import cloudscraper
from twitterPost import poster
twitterPoster = poster()
twitterPoster.twitter_api()

# we use the counter to not get limited by ME, we send a request from this script roughly every ~35s
counter = 35
# able to pull from 20 up to 500, I mostly use the latest 40 activities (listing/bids/sales)
limit = 40

# ###############
# CONSTANTS
COINGECKO = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
LAMPORTS = 1000000000

# In case the script is run and the sales are corrupt/empty or the file only has one entry, then we consider that sales to be "the old way"
# in the old way, we simply consider all the past transactions as processed.
# however in the new way, we will consider missing signatures as valuable and those must be processed
IS_NEW_WAY = False
REPORTED_DICT_LENGTH = False

# ###############
# SCRIPT_RELATED

SALES_FILE_NAME = "dump_sales.txt"
URL = f'https://api-mainnet.magiceden.dev/v2/collections/collectionName/activities?offset=0&limit={limit}'
URL_token = "https://api-mainnet.magiceden.dev/v2/tokens/"
WEBHOOK_URL = "INSERT_DISCORD_WEBHOOK_URL"

# ###############

scraper = cloudscraper.create_scraper(
    browser = 'chrome',
    interpreter ='nodejs',
    captcha={
     'provider': '2captcha',
     'api_key': 'cantypeanything'
   }    
)

# handling req
class TooManyRequests(Exception):
    timeout_val = 1
    def __init__(self, timeout_val):
        self.timeout_val = timeout_val

def beautify(url):
    res = scraper.get(url)
    P(res.status_code)
    if res.ok:
        return json.loads(res.text)
    if res.status_code == 429:
        P(res.text)
        P(res)
        raise TooManyRequests(10)
    return False

def sales():
    global IS_NEW_WAY, REPORTED_DICT_LENGTH
    cnt = 0
    scriptStartedAt = time.time()
    P(str(scriptStartedAt))
    while True:
        sleep(1)
        if (cnt > 32000):
            cnt = 0
        if (cnt % counter == 0):
            try:
                P(str(datetime.utcnow()))
                solprice = requests.get(COINGECKO, headers = {"accept":"application/json"})
                P(solprice.json()['solana']['usd'])
                data = beautify(URL)
            except TooManyRequests as e:
                P("TooManyRequests")
                sleep(e.timeout_val)
                sleep(1)
                continue
            except JSONDecodeError as e:
                P("=========")
                P(str(e))
                P(traceback.format_exc())
                P("=========")
                P(data)
                P("=========")
                continue
        if not data:
            P("Data is not filled up, continuing...")
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
                    P(f"Sales dict length = {len(file_dict)}")
                    REPORTED_DICT_LENGTH = True
                if len(file_dict) > 0:
                    IS_NEW_WAY = True
            except:
                pass
        for i in range(limit-1, -1, -1):
            deltaOfTime = data[i]['blockTime'] - scriptStartedAt
            if data[i]['type'] != 'buyNow':
                continue
            crt_signature = data[i]['signature']
            if deltaOfTime < 0:
                if crt_signature in file_dict:
                    continue
                if not IS_NEW_WAY:
                    file_dict[crt_signature] = data[i]
                    continue
            scriptStartedAt = time.time()
            # here we arrive when transaction is old, we are in the new way, and transaction was not found in sales, hence it was not processed
            # so we simply continue with below script
            if 'signature' in str(data[i]) and data[i]['type'] == 'buyNow':
                P('New Sale Found!')
                img = data[i]['image']
                price = data[i]['price']
                seller_address = data[i]['seller']
                buyer_address = data[i]['buyer']
                token_mint = data[i]['tokenMint']
                listOfStrings = [URL_token, token_mint]
                finalURL = "".join(listOfStrings)
                data_token = beautify(finalURL)
                mint_token = 'https://magiceden.io/item-details/' + str(token_mint)
                priceEQ1 = round(float(solprice.json()['solana']['usd']) * float(price), 2)
                priceEQFinal = "$" + str(priceEQ1)
                seller_add_exp = 'https://nfteyez.global/accounts/' + str(seller_address)
                buyer_add_exp = 'https://nfteyez.global/accounts/' + str(buyer_address)
                P(priceEQFinal)
                type = data[i]['type']
                name = data_token['name']
                # This is the Twitter message
                msg = f"{name} → SOLD for {price} S◎L ({priceEQFinal})! \n\n\
→ {mint_token}"
                # only use this line, 158, if you run the script on a Windows server, otherwise it's not needed
                # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                asyncio.run(postWebhook(name, type, price, img, priceEQFinal, mint_token, seller_add_exp, buyer_add_exp))
                # tweeting
                twitterPoster.tweet_image(img, msg)

                # let's consider this transaction as processed and store it
                file_dict[crt_signature] = data[i]
        with open(SALES_FILE_NAME, "w") as sales_file:
            sales_file.write(json.dumps(file_dict, indent = 2))

# posting it as an embed message to a Discord server, using the given WEBHOOK_URL
async def postWebhook(name, type, price, img, priceEQFinal, mint_token, seller_add_exp, buyer_add_exp):
    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(WEBHOOK_URL, adapter = AsyncWebhookAdapter(session))
        embed = discord.Embed(
            title = '',
            description = '',
            colour=discord.Colour(0x9933FF)
        )
        if type == 'buyNow':
            msgName = name + " → SOLD"
            msgPrice = str(price) + ' S◎L' + ' `(' + str(priceEQFinal) + " USD" + ')`'
        embed.set_author(name = msgName)
        embed.add_field(name = "Price", value = msgPrice, inline = False)
        embed.add_field(name = "View Token", value = '[NFT](' + mint_token+ ') ⧉', inline = True)
        embed.add_field(name = "Seller", value = '[Address](' + seller_add_exp+ ') ⧉', inline = False)
        embed.add_field(name = "Buyer", value = '[Address](' + buyer_add_exp+ ') ⧉', inline = False)
        text = 'Sold on Magic Eden'
        embed.set_footer(text = f"{text}", icon_url = 'https://i.postimg.cc/j2TbqJ3x/favicon.png%27')
        embed.set_thumbnail(url = img)
        sleep(1)
        await webhook.send(embed = embed)              
sales()
