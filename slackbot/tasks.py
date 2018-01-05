from __future__ import absolute_import, unicode_literals
from putzplan_generator.celery import app
from .slackbot import *


@app.task(ignore_result=True)
def poll_slack():
    if slack_running():
        read_slack()
    else:
        start_slack()
