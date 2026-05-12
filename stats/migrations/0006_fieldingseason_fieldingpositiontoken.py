from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('players', '0005_player_primary_position'),
        ('stats', '0005_add_statcast_zone_bucket'),
    ]

    operations = [
        migrations.CreateModel(
            name='FieldingSeason',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.SmallIntegerField(db_index=True)),
                ('stint', models.SmallIntegerField(default=1)),
                ('team', models.CharField(max_length=4)),
                ('league', models.CharField(max_length=3, null=True)),
                ('age', models.SmallIntegerField(null=True)),
                ('games', models.SmallIntegerField(null=True)),
                ('games_started', models.SmallIntegerField(null=True)),
                ('complete_games', models.SmallIntegerField(null=True)),
                ('innings_outs', models.IntegerField(null=True)),
                ('chances', models.SmallIntegerField(null=True)),
                ('putouts', models.SmallIntegerField(null=True)),
                ('assists', models.SmallIntegerField(null=True)),
                ('errors', models.SmallIntegerField(null=True)),
                ('double_plays', models.SmallIntegerField(null=True)),
                ('fielding_pct', models.FloatField(null=True)),
                ('rtot', models.SmallIntegerField(null=True)),
                ('rtot_per_year', models.SmallIntegerField(null=True)),
                ('rdrs', models.SmallIntegerField(null=True)),
                ('rdrs_per_year', models.SmallIntegerField(null=True)),
                ('range_factor_per_nine', models.FloatField(null=True)),
                ('league_range_factor_per_nine', models.FloatField(null=True)),
                ('range_factor_per_game', models.FloatField(null=True)),
                ('league_range_factor_per_game', models.FloatField(null=True)),
                ('passed_balls', models.SmallIntegerField(null=True)),
                ('wild_pitches', models.SmallIntegerField(null=True)),
                ('stolen_bases', models.SmallIntegerField(null=True)),
                ('caught_stealing', models.SmallIntegerField(null=True)),
                ('caught_stealing_pct', models.FloatField(null=True)),
                ('pickoffs', models.SmallIntegerField(null=True)),
                ('positions_raw', models.CharField(blank=True, max_length=30, null=True)),
                ('player', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fielding_seasons', to='players.player')),
            ],
            options={
                'indexes': [models.Index(fields=['year'], name='stats_field_year_72b434_idx'), models.Index(fields=['player', 'year'], name='stats_field_player__1bff96_idx'), models.Index(fields=['positions_raw'], name='stats_field_positio_e51132_idx')],
                'unique_together': {('player', 'year', 'stint', 'team')},
            },
        ),
        migrations.CreateModel(
            name='FieldingPositionToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rank', models.SmallIntegerField()),
                ('position', models.CharField(max_length=5)),
                ('is_primary_marker', models.BooleanField(default=False)),
                ('is_minor_marker', models.BooleanField(default=False)),
                ('is_career_major_marker', models.BooleanField(default=False)),
                ('is_career_minor_marker', models.BooleanField(default=False)),
                ('reported_games', models.SmallIntegerField(null=True)),
                ('fielding_season', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='position_tokens', to='stats.fieldingseason')),
            ],
            options={
                'ordering': ['rank'],
                'indexes': [models.Index(fields=['position'], name='stats_field_positio_5d5aff_idx'), models.Index(fields=['fielding_season', 'position'], name='stats_field_fieldin_c87919_idx')],
                'unique_together': {('fielding_season', 'rank')},
            },
        ),
    ]
