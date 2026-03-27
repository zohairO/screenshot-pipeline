select
    id,
    source,
    confidence,
    screen_type,
    application,
    key_content,
    entities,
    created_at,
    cast(created_at as date) as screenshot_date
from enriched_screenshots
where screen_type is not null