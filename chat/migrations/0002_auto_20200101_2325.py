# Generated by Django 3.0 on 2020-01-01 23:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PatientQueue',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('browser', models.CharField(max_length=100, unique=True)),
                ('channel', models.CharField(max_length=100, unique=True)),
                ('state', models.CharField(choices=[('QUEUED', 'Queued'), ('RESERVED', 'Reserved'), ('CHAT', 'Chat')], default='QUEUED', max_length=10)),
                ('status', models.CharField(choices=[('QUEUED', 'Queued'), ('RESERVED', 'Reserved'), ('CHAT', 'Chat')], default='ACTIVE', max_length=10)),
            ],
        ),
        migrations.AddField(
            model_name='doctor',
            name='browser',
            field=models.CharField(default=None, max_length=100, unique=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='doctor',
            name='status',
            field=models.CharField(choices=[('QUEUED', 'Queued'), ('RESERVED', 'Reserved'), ('CHAT', 'Chat')], default='ACTIVE', max_length=10),
        ),
        migrations.AlterField(
            model_name='doctor',
            name='patient',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='chat.PatientQueue'),
        ),
        migrations.DeleteModel(
            name='Patient',
        ),
    ]
