# Generated by Django 3.0 on 2019-12-14 04:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='doctor',
            name='channel',
            field=models.CharField(max_length=100, unique=True),
        ),
        migrations.AlterField(
            model_name='patient',
            name='channel',
            field=models.CharField(max_length=100, unique=True),
        ),
    ]