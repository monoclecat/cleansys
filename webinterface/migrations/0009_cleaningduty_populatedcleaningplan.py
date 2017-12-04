# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-12-04 12:14
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('webinterface', '0008_auto_20171203_1503'),
    ]

    operations = [
        migrations.CreateModel(
            name='CleaningDuty',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('cleaner1', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cleaner1', to='webinterface.Cleaner')),
                ('cleaner2', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='cleaner2', to='webinterface.Cleaner')),
            ],
        ),
        migrations.CreateModel(
            name='PopulatedCleaningPlan',
            fields=[
                ('cleaningplan_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='webinterface.CleaningPlan')),
                ('duties', models.ManyToManyField(to='webinterface.CleaningDuty')),
            ],
            bases=('webinterface.cleaningplan',),
        ),
    ]
