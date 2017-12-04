# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-12-03 14:09
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webinterface', '0006_auto_20171203_1359'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cleaningplan',
            name='cleaners_per_date',
            field=models.IntegerField(choices=[(1, 'One'), (2, 'Two')], default=1),
        ),
    ]
