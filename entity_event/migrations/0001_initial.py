# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('entity', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContextRenderer',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('name', models.CharField(max_length=64, unique=True)),
                ('text_template_path', models.CharField(max_length=256, default='')),
                ('html_template_path', models.CharField(max_length=256, default='')),
                ('text_template', models.TextField(default='')),
                ('html_template', models.TextField(default='')),
                ('context_hints', jsonfield.fields.JSONField(null=True, default=None)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('context', jsonfield.fields.JSONField()),
                ('time', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('time_expires', models.DateTimeField(db_index=True, default=datetime.datetime(9999, 12, 31, 23, 59, 59, 999999))),
                ('uuid', models.CharField(max_length=128, unique=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EventActor',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('entity', models.ForeignKey(to='entity.Entity')),
                ('event', models.ForeignKey(to='entity_event.Event')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EventSeen',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('time_seen', models.DateTimeField(default=datetime.datetime.utcnow)),
                ('event', models.ForeignKey(to='entity_event.Event')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Medium',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('name', models.CharField(max_length=64, unique=True)),
                ('display_name', models.CharField(max_length=64)),
                ('description', models.TextField()),
                ('additional_context', jsonfield.fields.JSONField(null=True, default=None)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RenderingStyle',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('name', models.CharField(max_length=64, unique=True)),
                ('display_name', models.CharField(max_length=64, default='')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Source',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('name', models.CharField(max_length=64, unique=True)),
                ('display_name', models.CharField(max_length=64)),
                ('description', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SourceGroup',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('name', models.CharField(max_length=64, unique=True)),
                ('display_name', models.CharField(max_length=64)),
                ('description', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('only_following', models.BooleanField(default=True)),
                ('entity', models.ForeignKey(related_name='+', to='entity.Entity')),
                ('medium', models.ForeignKey(to='entity_event.Medium')),
                ('source', models.ForeignKey(to='entity_event.Source')),
                ('sub_entity_kind', models.ForeignKey(null=True, related_name='+', to='entity.EntityKind', default=None)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Unsubscription',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('entity', models.ForeignKey(to='entity.Entity')),
                ('medium', models.ForeignKey(to='entity_event.Medium')),
                ('source', models.ForeignKey(to='entity_event.Source')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='source',
            name='group',
            field=models.ForeignKey(to='entity_event.SourceGroup'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='medium',
            name='rendering_style',
            field=models.ForeignKey(to='entity_event.RenderingStyle', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventseen',
            name='medium',
            field=models.ForeignKey(to='entity_event.Medium'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='eventseen',
            unique_together=set([('event', 'medium')]),
        ),
        migrations.AddField(
            model_name='event',
            name='source',
            field=models.ForeignKey(to='entity_event.Source'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contextrenderer',
            name='rendering_style',
            field=models.ForeignKey(to='entity_event.RenderingStyle'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contextrenderer',
            name='source',
            field=models.ForeignKey(to='entity_event.Source', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contextrenderer',
            name='source_group',
            field=models.ForeignKey(to='entity_event.SourceGroup', null=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='contextrenderer',
            unique_together=set([('source', 'rendering_style')]),
        ),
        migrations.CreateModel(
            name='AdminEvent',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('entity_event.event',),
        ),
    ]
