from dagster import Definitions, load_assets_from_modules, ScheduleDefinition, define_asset_job
from pipeline import assets

all_assets = load_assets_from_modules([assets])

daily_pipeline_job = define_asset_job(
    name="daily_pipeline_job",
    selection="*",
)

daily_schedule = ScheduleDefinition(
    job=daily_pipeline_job,
    cron_schedule="0 8 * * *",  # Every day at 8am
)

defs = Definitions(
    assets=all_assets,
    schedules=[daily_schedule],
)