import os
from celery import shared_task
import re
import slack
import logging


# instantiate Slack client
slack_client = slack.WebClient(os.environ.get('SLACK_BOT_TOKEN'))
# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = None
SLACK_BOT_START_INITIATED = False

EXAMPLE_COMMAND = "do"
MENTION_REGEX = "^<@(|[WU].+)>(.*)"


def parse_direct_mention(message_text):
    """
        Finds a direct mention (a mention that is at the beginning) in message text
        and returns the user ID which was mentioned. If there is no direct mention, returns None
    """
    matches = re.search(MENTION_REGEX, message_text)
    # the first group contains the username, the second group contains the remaining message
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None)


def handle_command(command, channel):
    """
        Executes bot command if the command is known
    """
    # Default response is help text for the user
    default_response = "Not sure what you mean. Try *{}*.".format(EXAMPLE_COMMAND)

    # Finds and executes the given command, filling in response
    response = None
    # This is where you start to implement more commands!
    if command.startswith(EXAMPLE_COMMAND):
        response = "Sure...write some more code then I can do that!"

    # Sends the response back to the channel
    slack_client.api_call(
        "chat.postMessage",
        channel=channel,
        text=response or default_response
    )


def get_slack_users():
    """Returns a list of tuples (slack user id, real name) of all human users in the workspace"""
    global starterbot_id
    if starterbot_id:
        response = slack_client.api_call("users.list")
    else:
        response = []
    if not response:
        return [(None, "--------------------")]
    users = [(None, "--------------------")]
    for user in response['members']:
        if 'bot_id' not in user['profile'] and user['name'] != "slackbot":
            users.append((user['id'], user['real_name']))
    return users


def read_slack():
    """Function to be scheduled every second. Reads messages from Slack workspace and processes them with the
    other functions."""
    global slack_client
    slack_events = slack_client.rtm_read()
    for event in slack_events:
        if event["type"] == "message" and "subtype" not in event:
            print(event)


def start_slack():
    global starterbot_id, slack_client
    if not starterbot_id:
        if slack_client.rtm_connect(with_team_state=False):
            print("Starter Bot connected and running!")
            # Read bot's user ID by calling Web API method `auth.test`
            starterbot_id = slack_client.api_call("auth.test")["user_id"]
        else:
            print("Connection failed. Exception traceback printed above.")


def slack_running():
    global starterbot_id
    return starterbot_id is not None
