# Generated by Django 3.2.19 on 2023-05-31 20:54

import datetime
import django.core.serializers.json
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    replaces = [('entity_event', '0001_initial'), ('entity_event', '0002_medium_creation_time'), ('entity_event', '0003_auto_20170830_1321'), ('entity_event', '0004_auto_20180403_1655'), ('entity_event', '0005_auto_20200409_1612')]

    dependencies = [
        ('entity', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('context', models.JSONField()),
                ('time', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('time_expires', models.DateTimeField(db_index=True, default=datetime.datetime(9999, 12, 31, 23, 59, 59, 999999))),
                ('uuid', models.CharField(max_length=128, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='EventActor',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='entity.entity')),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='entity_event.event')),
            ],
        ),
        migrations.CreateModel(
            name='Medium',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64, unique=True)),
                ('display_name', models.CharField(max_length=64)),
                ('description', models.TextField()),
                ('additional_context', models.JSONField(default=None, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='RenderingStyle',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256, unique=True)),
                ('display_name', models.CharField(default='', max_length=256)),
            ],
        ),
        migrations.CreateModel(
            name='Source',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64, unique=True)),
                ('display_name', models.CharField(max_length=64)),
                ('description', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='SourceGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256, unique=True)),
                ('display_name', models.CharField(max_length=256)),
                ('description', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('only_following', models.BooleanField(default=True)),
                ('entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='entity.entity')),
                ('medium', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='entity_event.medium')),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='entity_event.source')),
                ('sub_entity_kind', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='entity.entitykind')),
            ],
        ),
        migrations.CreateModel(
            name='Unsubscription',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='entity.entity')),
                ('medium', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='entity_event.medium')),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='entity_event.source')),
            ],
        ),
        migrations.AddField(
            model_name='source',
            name='group',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='entity_event.sourcegroup'),
        ),
        migrations.AddField(
            model_name='medium',
            name='rendering_style',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='entity_event.renderingstyle'),
        ),
        migrations.CreateModel(
            name='EventSeen',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time_seen', models.DateTimeField(default=datetime.datetime.utcnow)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='entity_event.event')),
                ('medium', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='entity_event.medium')),
            ],
            options={
                'unique_together': {('event', 'medium')},
            },
        ),
        migrations.AddField(
            model_name='event',
            name='source',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='entity_event.source'),
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
        migrations.AddField(
            model_name='medium',
            name='time_created',
            field=models.DateTimeField(auto_now_add=True, default=datetime.datetime(2017, 5, 24, 18, 7, 45, 987701)),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='event',
            name='uuid',
            field=models.CharField(max_length=512, unique=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='context',
            field=models.JSONField(encoder=django.core.serializers.json.DjangoJSONEncoder),
        ),
        migrations.AlterField(
            model_name='medium',
            name='additional_context',
            field=models.JSONField(default=None, encoder=django.core.serializers.json.DjangoJSONEncoder, null=True),
        ),
        migrations.CreateModel(
            name='ContextRenderer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256, unique=True)),
                ('text_template_path', models.CharField(default='', max_length=256)),
                ('html_template_path', models.CharField(default='', max_length=256)),
                ('text_template', models.TextField(default='')),
                ('html_template', models.TextField(default='')),
                ('context_hints', models.JSONField(default=None, encoder=django.core.serializers.json.DjangoJSONEncoder, null=True)),
                ('rendering_style', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='entity_event.renderingstyle')),
                ('source', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='entity_event.source')),
                ('source_group', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='entity_event.sourcegroup')),
            ],
            options={
                'unique_together': {('source', 'rendering_style')},
            },
        ),
        migrations.AlterField(
            model_name='medium',
            name='display_name',
            field=models.CharField(max_length=256),
        ),
        migrations.AlterField(
            model_name='medium',
            name='name',
            field=models.CharField(max_length=256, unique=True),
        ),
        migrations.AlterField(
            model_name='source',
            name='display_name',
            field=models.CharField(max_length=256),
        ),
        migrations.AlterField(
            model_name='source',
            name='name',
            field=models.CharField(max_length=256, unique=True),
        ),
    ]
