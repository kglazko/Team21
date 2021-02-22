from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    AWAITING_CONFIRMATION = auto()
    AWAITING_TYPE = auto()
    AWAITING_DETAILS = auto()
    FINALIZING_REPORT = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    CONFIRM_KEYWORD = "confirm"
    SEX_KEYWORD = "1"
    HATE_KEYWORD = "2"
    VIOLENCE_KEYWORD = "3"
    BULLYING_KEYWORD = "4"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.reporter = None
        self.message = None
        self.message_raw = None
        self.author = None
        self.abuse_type = None
        self.abuse_details = None
        self.comments = None
        self.mods = None
    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
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
                    "Please type `confirm` if this is the message you want to report."]
        
        if self.state == State.AWAITING_CONFIRMATION:
            if message.content == self.CONFIRM_KEYWORD:
                report_intro = "**Why are you reporting this post?\n**" + "If someone is in immediate danger, call the local emergency services- don't wait. \n"
                report_options = "**Please type one of the following\n**"
                report_options += "`1` Nudity or sexual activity\n"
                report_options += "`2` Hate speech or symbols\n"
                report_options += "`3` Violence or dangerous organizations\n"
                report_options += "`4` Bullying or harrassment\n"
                self.state = State.AWAITING_TYPE
                return [report_intro + report_options]
            else:
                self.state = State.AWAITING_TYPE
        if self.state == State.AWAITING_TYPE:
            if message.content == self.SEX_KEYWORD:
                self.state = State.AWAITING_DETAILS
                self.abuse_type = "Nudity of sexual activity"
                report_intro = "**Why are you reporting this post?\n**"
                report_options = "`N` Nudity\n"
                report_options += "`P` Pornography\n"
                report_options += "`S` Sexual harrassment\n"
                return [report_intro + report_options]

            if message.content == self.HATE_KEYWORD:
                self.state = State.FINALIZING_REPORT
                self.abuse_type = "Hate speech or symbols"
                report_options = "We remove:\n"
                report_options += "- Photos or videos of hate speech or symbols\n"
                report_options += "- Posts with captions that encourage violence or attack anyone based on who they are\n"
                report_string = "**Reporter: **" + self.reporter + "\n"
                report_string += "**Message: **" + self.message + "\n"
                report_string += "**Author: **" + self.author + "\n"
                report_string += "**Abuse Type: **" + self.abuse_type + "\n"
                report_string += "**Abuse Details: **" + self.abuse_details + "\n"
                report_sample = "**Please enter any final comments**"
                return [report_options + report_string + report_sample]

            if message.content == self.VIOLENCE_KEYWORD:
                self.state = State.AWAITING_DETAILS
                self.abuse_type = "Violence or dangerous organizations"
                report_intro = "**What kind of violence are you reporting?\n**"
                report_options = "`V` Violent threat\n"
                report_options += "`D` Dangerous organizations or individuals\n"
                return [report_intro + report_options]

            if message.content == self.BULLYING_KEYWORD:
                self.state = State.AWAITING_DETAILS
                self.abuse_type = "Bullying or harrassment"
                report_intro = "**Who is being bullied?\n**"
                report_options = "`M` Myself\n"
                report_options = "`SE` Someone else\n"
                return [report_intro + report_options]

        if self.state== State.AWAITING_DETAILS:
            if message.content == "N":
                self.state = State.FINALIZING_REPORT
                self.abuse_details = "Nudity"
                report_string = "**Reporter: **" + self.reporter + "\n"
                report_string += "**Message: **" + self.message + "\n"
                report_string += "**Author: **" + self.author + "\n"
                report_string += "**Abuse Type: **" + self.abuse_type + "\n"
                report_string += "**Abuse Details: **" + self.abuse_details + "\n"
                report_sample = "**Please enter any final comments**"
                return [report_string + report_sample]

            if message.content == "P":
                self.state = State.FINALIZING_REPORT
                self.abuse_details = "Pornography"
                report_string = "**Reporter: **" + self.reporter + "\n"
                report_string += "**Message: **" + self.message + "\n"
                report_string += "**Author: **" + self.author + "\n"
                report_string += "**Abuse Type: **" + self.abuse_type + "\n"
                report_string += "**Abuse Details: **" + self.abuse_details + "\n"
                report_sample = "**Please enter any final comments**"
                return [report_string + report_sample]

            if message.content == "S":
                self.state = State.FINALIZING_REPORT
                self.abuse_details = "Sexual harrassment"
                report_string = "**Reporter: **" + self.reporter + "\n"
                report_string += "**Message: **" + self.message + "\n"
                report_string += "**Author: **" + self.author + "\n"
                report_string += "**Abuse Type: **" + self.abuse_type + "\n"
                report_string += "**Abuse Details: **" + self.abuse_details + "\n"
                report_sample = "**Please enter any final comments**"
                return [report_string + report_sample]

            if message.content == "V":
                self.state = State.FINALIZING_REPORT
                self.abuse_details = "Violent threat"
                report_string = "**Reporter: **" + self.reporter + "\n"
                report_string += "**Message: **" + self.message + "\n"
                report_string += "**Author: **" + self.author + "\n"
                report_string += "**Abuse Type: **" + self.abuse_type + "\n"
                report_string += "**Abuse Details: **" + self.abuse_details + "\n"
                report_sample = "**Please enter any final comments**"
                return [report_string + report_sample]

            if message.content == "D":
                self.state = State.FINALIZING_REPORT
                self.abuse_details = "Dangerous organizations or individuals"
                report_string = "**Reporter: **" + self.reporter + "\n"
                report_string += "**Message: **" + self.message + "\n"
                report_string += "**Author: **" + self.author + "\n"
                report_string += "**Abuse Type: **" + self.abuse_type + "\n"
                report_string += "**Abuse Details: **" + self.abuse_details + "\n"
                report_sample = "**Please enter any final comments**"
                return [report_string + report_sample]

            if message.content == "M":
                self.state = State.FINALIZING_REPORT
                self.abuse_details = "Myself"
                report_string = "**Reporter: **" + self.reporter + "\n"
                report_string += "**Message: **" + self.message + "\n"
                report_string += "**Author: **" + self.author + "\n"
                report_string += "**Abuse Type: **" + self.abuse_type + "\n"
                report_string += "**Abuse Details: **" + self.abuse_details + "\n"
                report_sample = "**Please enter any final comments**"
                return [report_string + report_sample]

            if message.content == "SE":
                self.state = State.FINALIZING_REPORT
                self.abuse_details = "Someone else"
                report_string = "**Reporter: **" + self.reporter + "\n"
                report_string += "**Message: **" + self.message + "\n"
                report_string += "**Author: **" + self.author + "\n"
                report_string += "**Abuse Type: **" + self.abuse_type + "\n"
                report_string += "**Abuse Details: **" + self.abuse_details + "\n"
                report_string += "**Comments: **" + self.comments + "\n"
                report_sample += report_sample_generate + "**Please enter any final comments**"
                return [report_string + report_sample]

        if self.state == State.FINALIZING_REPORT:
            self.comments = message.content
            self.state = State.REPORT_COMPLETE
            report_title = "**FINAL REPORT**\n"
            report_string = "**Reporter: **" + self.reporter + "\n"
            report_string += "**Message: **" + self.message + "\n"
            report_string += "**Author: **" + self.author + "\n"
            report_string += "**Abuse Type: **" + self.abuse_type + "\n"
            report_string += "**Abuse Details: **" + self.abuse_details + "\n"
            report_string += "**Comments: **" + self.comments + "\n"

            thanks = "Thank you for submitting a report. It has been sent to the moderators."

            return [report_title + report_string + thanks]


        return []


    def report_complete(self):
        report_title = "**FINAL REPORT**\n"
        report_string = "**Reporter: **" + self.reporter + "\n"
        report_string += "**Message: **" + self.message + "\n"
        report_string += "**Author: **" + self.author + "\n"
        report_string += "**Abuse Type: **" + self.abuse_type + "\n"
        report_string += "**Abuse Details: **" + self.abuse_details + "\n"
        report_string += "**Comments: **" + self.comments + "\n"
        mod_channel = self.client.mod_channels[self.message_raw.guild.id]
        self.mods = mod_channel.send(report_title + report_string)
        return self.state == State.REPORT_COMPLETE
    


    

