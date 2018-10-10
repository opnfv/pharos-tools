# Generated by Django 2.1 on 2018-09-14 14:48

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('account', '0001_initial'),
        ('resource_inventory', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='Booking',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('start', models.DateTimeField()),
                ('end', models.DateTimeField()),
                ('reset', models.BooleanField(default=False)),
                ('jira_issue_id', models.IntegerField(blank=True, null=True)),
                ('jira_issue_status', models.CharField(blank=True, max_length=50)),
                ('purpose', models.CharField(max_length=300)),
                ('ext_count', models.IntegerField(default=2)),
                ('project', models.CharField(blank=True, default='', max_length=100, null=True)),
                ('collaborators', models.ManyToManyField(related_name='collaborators', to=settings.AUTH_USER_MODEL)),
                ('config_bundle', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='resource_inventory.ConfigBundle')),
                ('lab', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='account.Lab')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owner', to=settings.AUTH_USER_MODEL)),
                ('resource', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='resource_inventory.ResourceBundle')),
            ],
            options={
                'db_table': 'booking',
            },
        ),
        migrations.CreateModel(
            name='Installer',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=30)),
            ],
        ),
        migrations.CreateModel(
            name='Opsys',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('sup_installers', models.ManyToManyField(blank=True, to='booking.Installer')),
            ],
        ),
        migrations.CreateModel(
            name='Scenario',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=300)),
            ],
        ),
        migrations.AddField(
            model_name='installer',
            name='sup_scenarios',
            field=models.ManyToManyField(blank=True, to='booking.Scenario'),
        ),
    ]
