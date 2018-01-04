from __future__ import absolute_import, unicode_literals
from putzplan_generator.celery import app
from .slackbot import *


@app.task
def test_in_tasks(arg):
    print(arg)


@app.task
def query_slack():
    if not slack_running():
        start_slack()
    poll_slack()
    print("Slack polled!")
