# Generated by Django 2.1 on 2019-01-15 17:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0002_booking_pdf'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='installer',
            name='sup_scenarios',
        ),
        migrations.RemoveField(
            model_name='opsys',
            name='sup_installers',
        ),
        migrations.DeleteModel(
            name='Installer',
        ),
        migrations.DeleteModel(
            name='Opsys',
        ),
        migrations.DeleteModel(
            name='Scenario',
        ),
    ]
