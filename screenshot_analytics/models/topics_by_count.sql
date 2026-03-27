select
    screen_type,
    application,
    count(*) as screenshot_count
from {{ ref('stg_enriched_screenshots') }}
group by screen_type, application
order by screenshot_count desc