-- Clean HTML entities from vessels table
-- This script replaces common HTML entities with their actual characters

-- Backup recommendation: Create a backup before running
-- CREATE TABLE vessels_backup AS SELECT * FROM vessels;

-- Clean owner column
UPDATE vessels
SET owner = REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
    owner,
    '&amp;', '&'),
    '&lt;', '<'),
    '&gt;', '>'),
    '&quot;', '"'),
    '&#39;', "'"),
    '&nbsp;', ' ')
WHERE owner LIKE '%&%';

-- Clean manager column
UPDATE vessels
SET manager = REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
    manager,
    '&amp;', '&'),
    '&lt;', '<'),
    '&gt;', '>'),
    '&quot;', '"'),
    '&#39;', "'"),
    '&nbsp;', ' ')
WHERE manager LIKE '%&%';

-- Check for any remaining HTML entities
SELECT
    'owner' as column_name,
    id,
    imo,
    owner as value
FROM vessels
WHERE owner LIKE '%&%'
UNION ALL
SELECT
    'manager' as column_name,
    id,
    imo,
    manager as value
FROM vessels
WHERE manager LIKE '%&%';
