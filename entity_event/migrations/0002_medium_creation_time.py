# -*- coding: utf-8 -*-
# Generated by Django 1.9.11 on 2017-05-24 18:07

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('entity_event', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='medium',
            name='time_created',
            field=models.DateTimeField(auto_now_add=True, default=datetime.datetime(2017, 5, 24, 18, 7, 45, 987701)),
            preserve_default=False,
        ),
    ]
