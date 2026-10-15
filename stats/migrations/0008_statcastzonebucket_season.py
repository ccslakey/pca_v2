from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('players', '0008_methodology_bge_small'),
        ('stats', '0007_jamesscore'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='statcastzonebucket',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='statcastzonebucket',
            name='season',
            field=models.PositiveSmallIntegerField(null=True),
        ),
        migrations.AlterUniqueTogether(
            name='statcastzonebucket',
            unique_together={('player', 'role', 'season', 'outcome', 'plate_x', 'plate_z')},
        ),
    ]
