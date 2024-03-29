# -*- coding: utf-8 -*-

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='TestFKModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.CharField(max_length=64)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TestFKModel2',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.CharField(max_length=64)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TestModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.CharField(max_length=64)),
                ('fk', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tests.TestFKModel')),
                ('fk2', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tests.TestFKModel2')),
                ('fk_m2m', models.ManyToManyField(related_name='+', to='tests.TestFKModel')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
