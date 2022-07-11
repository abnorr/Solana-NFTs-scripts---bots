import tweepy
import os
import requests

class poster:
    def twitter_api(self):
        #your twitter API keys & secrets
        access_token = ''
        access_token_secret = ''
        consumer_key = ''
        consumer_secret = ''
                           
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        api = tweepy.API(auth)
        self.api = api

    def tweet_image(self,url, message):
        
        filename = 'tempImage.jpg'
        request = requests.get(url, stream=True)
        if request.status_code == 200:
            with open(filename, 'wb') as image:
                for chunk in request:
                    image.write(chunk)

            media = self.api.media_upload(filename)
            os.remove(filename)
            post_result = self.api.update_status(status=message, media_ids=[media.media_id])
        else:
            print("Unable to download image")

