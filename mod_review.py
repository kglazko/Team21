from enum import Enum, auto
import discord
import re

class State(Enum):
    REVIEW_START = auto()
    AWAITING_MESSAGE = auto()
    REPORT_COMPLETE = auto()
    AWAITING_CONFIRMATION = auto()
    AWAITING_TYPE = auto()

class Review:
    START_KEYWORD = "start"
    CANCEL_KEYWORD = "cancel"
    REVIEW_KEYWORD = "review"
    CONFIRM_KEYWORD = "confirm"
    WARNING_KEYWORD = "1"
    DELETE_KEYWORD = "2"
    BAN_KEYWORD = "3"

    def __init__(self, client):
        self.state = State.REVIEW_START
        self.client = client
        self.reporter = ""
        self.message = ""
        self.message_raw = None
        self.author = ""
        self.action_type = ""
    
    async def handle_mod_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Review cancelled."]
        
        if self.state == State.REVIEW_START:
            reply =  "Thank you for starting the reviewing process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the review you want to review.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.AWAITING_CONFIRMATION
            self.message = message.content
            self.message_raw = message
            self.reporter = self.client.user.name
            self.author = message.author.name
            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
                    "Please type `confirm` if this is the message you want to review."]
        
        if self.state == State.AWAITING_CONFIRMATION:
            if message.content == self.CONFIRM_KEYWORD:
                report_intro = "**What action do you want to take?**\n"
                report_options = "`1` Send Warning Only\n"
                report_options += "`2` Send Warning and Delete Message\n"
                report_options += "`3` Delete Message and Ban User\n"
                self.state = State.AWAITING_TYPE
                return [report_intro + report_options]
            else:
                self.state = State.AWAITING_TYPE

        if self.state == State.AWAITING_TYPE:
            if message.content == self.WARNING_KEYWORD:
                self.state = State.REPORT_COMPLETE
                self.action_type = "Warning"
                report_string = "FINAL REVIEW"
                report_string += self.action_type + '\n'
                report_string += self.message
                return [report_string]


            if message.content == self.DELETE_KEYWORD:
                self.state = State.REPORT_COMPLETE
                self.action_type = "Delete"
                report_string = "FINAL REVIEW"
                report_string += self.action_type + '\n'
                report_string += self.message
                return [report_string]

            if message.content == self.BAN_KEYWORD:
                self.state = State.REPORT_COMPLETE
                self.action_type = "Ban"
                report_string = "FINAL REVIEW"
                report_string += self.action_type + '\n'
                report_string += self.message
                return [report_string]


        return []


    def report_complete(self):
    
        return self.state == State.REPORT_COMPLETE