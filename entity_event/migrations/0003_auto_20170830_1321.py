# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-30 13:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('entity_event', '0002_medium_creation_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='uuid',
            field=models.CharField(max_length=512, unique=True),
        ),
    ]
