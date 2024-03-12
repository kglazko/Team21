# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
import unicodedata
from report import Report
from mod_review import Review

#Set up global variables
auto_ban_threshold = 0.9
auto_delete_threshold = 0.8

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'token.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']
    perspective_key = tokens['perspective']


class ModBot(discord.Client):
    def __init__(self, key):
        intents = discord.Intents.default()
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None   
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.reviews = {} #Map from mod IDs to the state of their review
        self.perps = []
        self.perp_warnings = []
        self.message_reports = []
        self.message_with_victim = []
        self.messages_correlated = []
        self.perspective_key = key

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")
        
        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel

    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs). 
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel. 
        '''
        # Ignore messages from us 
        if message.author.id == self.user.id:
            return
        
        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)
            await self.handle_mod_dm(message)

    async def handle_dm(self, message):

        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)
        
        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)
        final_report = ""
        for r in responses:
            await message.channel.send(r)
            if 'FINAL REPORT' in r:
                for channel in self.mod_channels.values():
                    my_message = await channel.send(f'Submitted By: {message.author.name}\n {r}')
                    self.message_reports.append(my_message.content)
                    self.message_with_victim.append(message.author)
                    self.messages_correlated.append(self.reports[author_id].message_raw)

                    #Auto-moderate
                    stripped = r.replace('**', '')
                    stripped = stripped.replace(':', '')
                    stripped = stripped.replace('\n', '')
                    final_message = re.search('Message(.*)Author', stripped).group(1)
                    perp_name = re.search('Author(.*)Abuse Type', stripped).group(1)
                    perp = self.reports[author_id].message_raw.author

                    scores = self.eval_reported_text(final_message)

                    for attr, score in scores.items():
                        if score >= 0.8: 
                            # Add warning
                            if perp in self.perps:
                                self.perp_warnings[self.perps.index(perp)] += 1

                            else:
                                self.perps.append(perp)
                                int_to_append = 1
                                self.perp_warnings.append(int_to_append)
                            
                            perp_index = self.perps.index(perp)
                            print(str(perp_index))
                            num_warnings = self.perp_warnings[perp_index]

                            await channel.send(f'User `{perp_name}` was sent a warning for excessive abuse for `{final_message}`')
                            await perp.send('A message you sent has been flagged as abusive.\n This is your ' + str(num_warnings) + '/3 warning.')

                            if num_warnings >=3:
                                await perp.send('You have been banned.')
                                await channel.send(f'User `{perp_name}` was banned for being a baddie.')
                                await message.author.send(f'`{perp_name}` has been banned for multiple incidents of abuse. Thank you for your report.')
                            await message.author.send(f'`{perp_name}` was sent an automatic warning. Thank you for your report.')


        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
            self.reports.pop(author_id)

    async def handle_mod_dm(self, message):

        # Handle a review message
        if message.content == Review.REVIEW_KEYWORD:
            reply =  "Use the `start` command to begin the reviewing process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reviews and not message.content.startswith(Review.START_KEYWORD):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reviews:
            self.reviews[author_id] = Review(self)
        
        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reviews[author_id].handle_mod_message(message)
        final_report = ""
        for r in responses:
            await message.channel.send(r)
            if 'FINAL REVIEW' in r:
                for channel in self.mod_channels.values():
                    my_message = await channel.send(f'Reviewing: {message.author.name}\n {r}')
                    for i in self.message_reports:
                        print(i)

                    print(self.reviews[author_id].message)
                    if (self.reviews[author_id].message in self.message_reports):
                        index = self.message_reports.index(self.reviews[author_id].message)
                        perp = self.messages_correlated[index].author
                        victim = self.message_with_victim[index]
                        perp_name = perp.name
                        msg_to_delete = self.messages_correlated[index].content

                        if perp in self.perps:
                                self.perp_warnings[self.perps.index(perp)] += 1

                        else:
                            self.perps.append(perp)
                            int_to_append = 1
                            self.perp_warnings.append(int_to_append)
                            
                            perp_index = self.perps.index(perp)
                            print(str(perp_index))
                            num_warnings = self.perp_warnings[perp_index]

                        if "Warn" in r:
                            await perp.send('A message you sent has been flagged as abusive.\n This is your ' + str(num_warnings) + '/3 warning.')
                            await victim.send(f'`{perp_name}` was sent an automatic warning. Thank you for your report.')

                        if "Delete" in r:
                            await perp.send('A message you sent has been flagged as abusive.\n This is your ' + str(num_warnings) + '/3 warning.')
                            await victim.send(f'`{perp_name}` was sent an automatic warning and the message `{msg_to_delete}` will be removed. \n Thank you for your report.')
                            await self.messages_correlated[index].delete()

                        if "Ban" in r:
                            await perp.send('You have been banned.')
                            await victim.send(f'`{perp_name}` was banned and the message `{msg_to_delete}` will be removed. \n Thank you for your report.')
                            await self.messages_correlated[index].delete()

        # If the report is complete or cancelled, remove it from our map
        if self.reviews[author_id].report_complete():
            self.reviews.pop(author_id)


    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if not message.channel.name == f'group-{self.group_num}':
            return 
        

        # Check #1: Prevent ASCII abuse such as sending abuse through foreign letters
        # Force into ASCII to counvert to unicode letters if not ASCII
        # Replace message content with converted
        # Example: ŞĹŬŤ  

        if not message.content.isascii():
            to_convert = message.content
            to_convert = unicodedata.normalize('NFKD', to_convert).encode('ascii', 'ignore')
            to_convert = str(to_convert)
            to_convert = to_convert.replace("b'", "")
            to_convert = to_convert.replace("'", "")

            # For some reason lowercase has higher toxicity ratings, we want to err on the side of high
            message.content = to_convert.lower()

        # Check #2: Prevent a user from sending abuse words that have spaces between the letters
        # Example: S L U T

        letters_num = other_num = 0
        for i in message.content:
            if i.isalpha():
                letters_num = letters_num + 1

            if i == " ":
                other_num = other_num + 1

        if other_num >= letters_num - 1:

            # For some reason lowercase has higher toxicity ratings, we want to err on the side of high
            message.content = message.content.replace(" ","").lower()





        # Forward the message to the mod channel
        mod_channel = self.mod_channels[message.guild.id]
        await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')

        scores = self.eval_text(message)
        await mod_channel.send(self.code_format(json.dumps(scores, indent=2)))

        # Automoderate based on threshold

        # Bool tracked to see if already auto-mod
        already_auto = False

        # Very serious offense
        for attr, score in scores.items():
            if score >= 0.90:
                await mod_channel.send(f'Message `{message.content}` by `{message.author.name}` was auto-deleted\n')
                await message.author.send(f'Your message \n `{message.content}` has been flagged as abusive and was deleted')
                await message.delete()
                already_auto = True
                break

        # Warning offense
        for attr, score in scores.items():
            if score <= 0.84 and score > 0.65 and not already_auto:
                await mod_channel.send(f'Message `{message.content}` by `{message.author.name}` resulted in a warn\n')
                await message.author.send(f'Your message \n `{message.content}` has been flagged as abusive')
                break


    def eval_text(self, message):
        '''
        Given a message, forwards the message to Perspective and returns a dictionary of scores.
        '''
        PERSPECTIVE_URL = 'https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze'

        url = PERSPECTIVE_URL + '?key=' + self.perspective_key
        data_dict = {
            'comment': {'text': message.content},
            'languages': ['en'],
            'requestedAttributes': {
                                    'SEVERE_TOXICITY': {}, 'PROFANITY': {},
                                    'IDENTITY_ATTACK': {}, 'THREAT': {},
                                    'TOXICITY': {}, 'FLIRTATION': {}
                                },
            'doNotStore': True
        }
        response = requests.post(url, data=json.dumps(data_dict))
        response_dict = response.json()

        scores = {}
        for attr in response_dict["attributeScores"]:
            scores[attr] = response_dict["attributeScores"][attr]["summaryScore"]["value"]

        return scores

    def eval_reported_text(self, reported_message):
        '''
        Given a message, forwards the message to Perspective and returns a dictionary of scores.
        '''
        PERSPECTIVE_URL = 'https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze'

        url = PERSPECTIVE_URL + '?key=' + self.perspective_key
        data_dict = {
            'comment': {'text': reported_message},
            'languages': ['en'],
            'requestedAttributes': {
                                    'SEVERE_TOXICITY': {}, 'PROFANITY': {},
                                    'IDENTITY_ATTACK': {}, 'THREAT': {},
                                    'TOXICITY': {}, 'FLIRTATION': {}
                                },
            'doNotStore': True
        }
        response = requests.post(url, data=json.dumps(data_dict))
        response_dict = response.json()

        scores = {}
        for attr in response_dict["attributeScores"]:
            scores[attr] = response_dict["attributeScores"][attr]["summaryScore"]["value"]

        return scores
    
    def code_format(self, text):
        return "```" + text + "```"
            
        
client = ModBot(perspective_key)
client.run(discord_token)
