select
    date_trunc('week', screenshot_date) as week,
    screen_type,
    application,
    count(*) as screenshot_count
from {{ ref('stg_enriched_screenshots') }}
group by week, screen_type, application
order by week desc, screenshot_count desc