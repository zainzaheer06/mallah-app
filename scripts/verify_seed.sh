#!/bin/bash
# Catalog seed verification — runs a series of queries to confirm everything
# seeded correctly and to give you a feel for what the data looks like.
#
# Run with:
#   ./tests/verify_seed.sh

set -e

PSQL="docker compose exec -T postgres psql -U mallah -d mallah -A"

hr() { echo; echo "── $1 ──"; }

hr "Counts by table"
$PSQL <<'SQL'
SELECT 'sources'           AS tbl, COUNT(*) FROM sources
UNION ALL SELECT 'cuisines',          COUNT(*) FROM cuisines
UNION ALL SELECT 'restaurant_groups', COUNT(*) FROM restaurant_groups
UNION ALL SELECT 'restaurants',       COUNT(*) FROM restaurants
UNION ALL SELECT 'menu_sections',     COUNT(*) FROM menu_sections
UNION ALL SELECT 'menu_items',        COUNT(*) FROM menu_items
UNION ALL SELECT 'normalized_items',  COUNT(*) FROM normalized_items
UNION ALL SELECT 'item_mappings',     COUNT(*) FROM item_mappings
ORDER BY tbl;
SQL

hr "Restaurants per source"
$PSQL <<'SQL'
SELECT s.display_name, COUNT(*) AS restaurants
FROM restaurants r JOIN sources s ON s.id = r.source_id
GROUP BY s.display_name
ORDER BY restaurants DESC;
SQL

hr "Restaurants per district"
$PSQL <<'SQL'
SELECT district, COUNT(*) AS restaurants
FROM restaurants
GROUP BY district
ORDER BY restaurants DESC;
SQL

hr "Sample 5 restaurants (bilingual names)"
$PSQL <<'SQL'
SELECT name_en, name_ar, district, ROUND(rating::numeric, 1) AS rating, delivery_fee
FROM restaurants
ORDER BY rating DESC
LIMIT 5;
SQL

hr "Top 10 most popular menu items by price"
$PSQL <<'SQL'
SELECT name_en, name_ar, price, currency, is_popular
FROM menu_items
WHERE is_popular = true
ORDER BY price DESC
LIMIT 10;
SQL

hr "Items currently on discount"
$PSQL <<'SQL'
SELECT
  name_en,
  price AS regular,
  discounted_price AS discounted,
  ROUND(((price - discounted_price) / price * 100)::numeric, 0) AS percent_off
FROM menu_items
WHERE discounted_price IS NOT NULL
ORDER BY percent_off DESC
LIMIT 10;
SQL

hr "Comparison demo — Big Mac across sources"
$PSQL <<'SQL'
SELECT
  s.display_name AS source,
  mi.name_en,
  mi.price,
  r.district
FROM normalized_items ni
JOIN item_mappings im ON im.normalized_item_id = ni.id
JOIN menu_items mi ON mi.id = im.menu_item_id
JOIN sources s ON s.id = mi.source_id
JOIN restaurants r ON r.id = mi.restaurant_id
WHERE ni.slug = 'seed_mcdonalds-big-mac'
ORDER BY mi.price ASC;
SQL

hr "Comparison demo — Quarter Chicken across sources"
$PSQL <<'SQL'
SELECT
  s.display_name AS source,
  mi.name_ar,
  mi.price,
  r.district
FROM normalized_items ni
JOIN item_mappings im ON im.normalized_item_id = ni.id
JOIN menu_items mi ON mi.id = im.menu_item_id
JOIN sources s ON s.id = mi.source_id
JOIN restaurants r ON r.id = mi.restaurant_id
WHERE ni.slug = 'seed_tazaj-quarter-chicken'
ORDER BY mi.price ASC;
SQL

hr "Cuisines (with emoji + bilingual)"
$PSQL <<'SQL'
SELECT slug, emoji, name_en, name_ar, display_order
FROM cuisines
ORDER BY display_order;
SQL

echo
echo "✅ Seed verification complete"