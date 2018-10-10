# Generated by Django 2.1 on 2018-09-26 14:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0002_lab_description'),
    ]

    operations = [
        migrations.CreateModel(
            name='PublicNetwork',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vlan', models.IntegerField()),
                ('in_use', models.BooleanField(default=False)),
                ('cidr', models.CharField(default='0.0.0.0/0', max_length=50)),
                ('gateway', models.CharField(default='0.0.0.0', max_length=50)),
                ('lab', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='account.Lab')),
            ],
        ),
    ]
