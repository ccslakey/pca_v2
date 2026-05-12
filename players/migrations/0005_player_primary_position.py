from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('players', '0004_birthdate_and_remove_year_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='player',
            name='primary_position',
            field=models.CharField(db_index=True, max_length=3, null=True),
        ),
    ]
