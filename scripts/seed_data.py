"""
Seed realistic Saudi market test data.

Idempotent — safe to run multiple times. Skips existing rows.

Usage (from inside the api container):
    docker compose exec api python scripts/seed_data.py
"""
import asyncio
import json
import sys
from datetime import date
from decimal import Decimal
from uuid import uuid4

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, "/app")

from app.core.config import settings
from app.modules.auth.models import AuthProvider, Gender, User, UserAddress
from app.core.security import hash_password

logger = structlog.get_logger()

USERS = [
    {
        "email": "test_consumer@mallah.dev",
        "password": "consumer_pw_123",
        "display_name": "Abdul Aziz Al-Otaibi",
        "phone_number": "+966501234567",
        "language": "ar",
        "default_city": "Riyadh",
        "gender": Gender.MALE,
        "date_of_birth": date(1990, 3, 15),
        "auth_provider": AuthProvider.EMAIL,
    },
    {
        "email": "test_user2@mallah.dev",
        "password": "user2_pw_123",
        "display_name": "Fatima Al-Saud",
        "phone_number": "+966509876543",
        "language": "en",
        "default_city": "Jeddah",
        "gender": Gender.FEMALE,
        "date_of_birth": date(1995, 7, 22),
        "auth_provider": AuthProvider.EMAIL,
    },
    {
        "email": "test_admin@mallah.dev",
        "password": "admin_pw_123",
        "display_name": "Admin User",
        "language": "en",
        "auth_provider": AuthProvider.EMAIL,
        "is_admin": True,
    },
]

ADDRESSES = [
    {
        "user_email": "test_consumer@mallah.dev",
        "label": "Home",
        "address_line": "Al Olaya District, King Fahd Road, Building 21",
        "city": "Riyadh",
        "district": "Al Olaya",
        "latitude": 24.7136,
        "longitude": 46.6753,
        "is_default": True,
    },
    {
        "user_email": "test_consumer@mallah.dev",
        "label": "Office",
        "address_line": "King Abdullah Financial District, Tower B",
        "city": "Riyadh",
        "district": "KAFD",
        "latitude": 24.7639,
        "longitude": 46.6390,
        "is_default": False,
    },
    {
        "user_email": "test_user2@mallah.dev",
        "label": "Home",
        "address_line": "Al Hamra District, Prince Sultan Road",
        "city": "Jeddah",
        "district": "Al Hamra",
        "latitude": 21.5810,
        "longitude": 39.1653,
        "is_default": True,
    },
]

SOURCES = [
    {"name": "hungerstation", "display_name": "HungerStation", "source_type": "aggregator"},
    {"name": "jahez", "display_name": "Jahez", "source_type": "aggregator"},
    {"name": "keeta", "display_name": "Keeta", "source_type": "aggregator"},
    {"name": "albaik", "display_name": "Al Baik", "source_type": "standalone"},
    {"name": "kudu", "display_name": "Kudu", "source_type": "standalone"},
]

RESTAURANTS = [
    {
        "source_name": "hungerstation",
        "external_id": "hs_albaik_olaya",
        "chain_id": "albaik",
        "chain_name": "Al Baik",
        "name_en": "Al Baik - Al Olaya Branch",
        "name_ar": "البيك - فرع العليا",
        "vertical": "restaurants",
        "cuisines": ["Fast Food", "Chicken", "Saudi"],
        "rating": Decimal("4.7"),
        "rate_count": 12450,
        "city": "Riyadh",
        "district": "Al Olaya",
        "latitude": 24.6877,
        "longitude": 46.7219,
        "delivery_fee": Decimal("15.00"),
        "minimum_order_sar": Decimal("25.00"),
        "price_range": 1,
        "eta_min": 30,
        "eta_max": 45,
        "is_most_loved": True,
    },
    {
        "source_name": "hungerstation",
        "external_id": "hs_kudu_olaya",
        "chain_id": "kudu",
        "chain_name": "Kudu",
        "name_en": "Kudu - Tahlia Street",
        "name_ar": "كودو - شارع التحلية",
        "vertical": "restaurants",
        "cuisines": ["Fast Food", "Burgers", "Sandwiches"],
        "rating": Decimal("4.4"),
        "rate_count": 8932,
        "city": "Riyadh",
        "district": "Al Olaya",
        "latitude": 24.6953,
        "longitude": 46.6855,
        "delivery_fee": Decimal("12.00"),
        "minimum_order_sar": Decimal("20.00"),
        "price_range": 2,
        "eta_min": 25,
        "eta_max": 40,
    },
    {
        "source_name": "hungerstation",
        "external_id": "hs_herfy_kafd",
        "chain_id": "herfy",
        "chain_name": "Herfy",
        "name_en": "Herfy - KAFD",
        "name_ar": "هرفي - الرياض المالية",
        "vertical": "restaurants",
        "cuisines": ["Fast Food", "Burgers", "Saudi"],
        "rating": Decimal("4.2"),
        "rate_count": 5621,
        "city": "Riyadh",
        "district": "KAFD",
        "latitude": 24.7642,
        "longitude": 46.6388,
        "delivery_fee": Decimal("10.00"),
        "minimum_order_sar": Decimal("20.00"),
        "price_range": 1,
        "eta_min": 20,
        "eta_max": 35,
    },
    {
        "source_name": "hungerstation",
        "external_id": "hs_mcdonalds_olaya",
        "chain_id": "mcdonalds",
        "chain_name": "McDonald's",
        "name_en": "McDonald's - Olaya",
        "name_ar": "ماكدونالدز - العليا",
        "vertical": "restaurants",
        "cuisines": ["Fast Food", "Burgers", "American"],
        "rating": Decimal("4.3"),
        "rate_count": 14503,
        "city": "Riyadh",
        "district": "Al Olaya",
        "latitude": 24.6892,
        "longitude": 46.7211,
        "delivery_fee": Decimal("15.00"),
        "minimum_order_sar": Decimal("30.00"),
        "price_range": 2,
        "eta_min": 25,
        "eta_max": 45,
        "is_most_loved": True,
    },
    {
        "source_name": "hungerstation",
        "external_id": "hs_cafeboulud_jeddah",
        "chain_id": "cafe_boulud",
        "chain_name": "Café Boulud",
        "name_en": "Café Boulud - Jeddah Corniche",
        "name_ar": "كافيه بولود - كورنيش جدة",
        "vertical": "restaurants",
        "cuisines": ["French", "Cafe", "Desserts"],
        "rating": Decimal("4.8"),
        "rate_count": 3210,
        "city": "Jeddah",
        "district": "Corniche",
        "latitude": 21.5810,
        "longitude": 39.1456,
        "delivery_fee": Decimal("20.00"),
        "minimum_order_sar": Decimal("50.00"),
        "price_range": 3,
        "eta_min": 35,
        "eta_max": 55,
    },
    {
        "source_name": "jahez",
        "external_id": "jz_kfc_olaya",
        "chain_id": "kfc",
        "chain_name": "KFC",
        "name_en": "KFC - Olaya Mall",
        "name_ar": "كنتاكي - مول العليا",
        "vertical": "restaurants",
        "cuisines": ["Fast Food", "Chicken", "American"],
        "rating": Decimal("4.5"),
        "rate_count": 9876,
        "city": "Riyadh",
        "district": "Al Olaya",
        "latitude": 24.6864,
        "longitude": 46.7235,
        "delivery_fee": Decimal("13.00"),
        "minimum_order_sar": Decimal("25.00"),
        "price_range": 2,
        "eta_min": 25,
        "eta_max": 40,
    },
    {
        "source_name": "albaik",
        "external_id": "ab_jeddah_main",
        "chain_id": "albaik",
        "chain_name": "Al Baik",
        "name_en": "Al Baik - Jeddah Original",
        "name_ar": "البيك - الفرع الرئيسي جدة",
        "vertical": "restaurants",
        "cuisines": ["Fast Food", "Chicken", "Saudi"],
        "rating": Decimal("4.9"),
        "rate_count": 42103,
        "city": "Jeddah",
        "district": "Al Hamra",
        "latitude": 21.5790,
        "longitude": 39.1684,
        "delivery_fee": Decimal("0.00"),
        "minimum_order_sar": Decimal("20.00"),
        "price_range": 1,
        "eta_min": 30,
        "eta_max": 50,
        "is_most_loved": True,
    },
]

MENU_ITEMS = {
    "hs_albaik_olaya": {
        "Chicken": [
            {"name_en": "4-piece Chicken Meal", "name_ar": "وجبة دجاج 4 قطع", "base_price": 22.00, "calories": 850, "popularity": "100+ orders"},
            {"name_en": "Broasted Chicken (single)", "name_ar": "دجاج برأستد", "base_price": 6.00, "calories": 220},
            {"name_en": "Filet Sandwich", "name_ar": "سندوتش فيليه", "base_price": 12.00, "calories": 410, "popularity": "50+ orders"},
        ],
        "Sides": [
            {"name_en": "Garlic Sauce", "name_ar": "صلصة الثوم", "base_price": 2.00, "calories": 60},
            {"name_en": "Coleslaw", "name_ar": "كول سلو", "base_price": 5.00, "calories": 120},
        ],
    },
    "hs_kudu_olaya": {
        "Burgers": [
            {"name_en": "Big Kudu Meal", "name_ar": "وجبة كبير كودو", "base_price": 28.00, "list_price": 32.00, "discounted_price": 28.00, "discount_percentage": 12.5, "calories": 920, "popularity": "200+ orders"},
            {"name_en": "Quesadilla Sandwich", "name_ar": "سندوتش كاساديا", "base_price": 21.00, "calories": 580},
        ],
        "Drinks": [
            {"name_en": "Pepsi (regular)", "name_ar": "بيبسي وسط", "base_price": 5.00, "calories": 150},
        ],
    },
    "hs_herfy_kafd": {
        "Burgers": [
            {"name_en": "Super Burger", "name_ar": "سوبر برجر", "base_price": 18.00, "calories": 720},
            {"name_en": "Mexicali Burger", "name_ar": "ميكسيكالي برجر", "base_price": 24.00, "list_price": 30.00, "discounted_price": 24.00, "discount_percentage": 20.0, "calories": 850, "popularity": "150+ orders"},
        ],
    },
    "hs_mcdonalds_olaya": {
        "Burgers": [
            {"name_en": "Big Mac Meal", "name_ar": "وجبة بيج ماك", "base_price": 32.00, "calories": 1040, "popularity": "300+ orders"},
            {"name_en": "McChicken Sandwich", "name_ar": "ماك تشيكن", "base_price": 14.00, "calories": 400},
            {"name_en": "Cheeseburger", "name_ar": "تشيز برجر", "base_price": 9.00, "calories": 300},
        ],
        "Sides": [
            {"name_en": "Large Fries", "name_ar": "بطاطس كبير", "base_price": 11.00, "calories": 510},
        ],
    },
    "hs_cafeboulud_jeddah": {
        "Pastries": [
            {"name_en": "Croissant", "name_ar": "كرواسون", "base_price": 18.00, "calories": 280},
            {"name_en": "Tarte au Chocolat", "name_ar": "تارت الشوكولاتة", "base_price": 35.00, "calories": 420, "popularity": "30+ orders"},
        ],
        "Coffee": [
            {"name_en": "Cappuccino", "name_ar": "كابتشينو", "base_price": 22.00, "calories": 90},
            {"name_en": "Espresso", "name_ar": "اسبريسو", "base_price": 16.00, "calories": 5},
        ],
    },
    "jz_kfc_olaya": {
        "Chicken": [
            {"name_en": "Zinger Meal", "name_ar": "وجبة زنجر", "base_price": 30.00, "calories": 880, "popularity": "250+ orders"},
            {"name_en": "8-piece Bucket", "name_ar": "بكت 8 قطع", "base_price": 65.00, "list_price": 75.00, "discounted_price": 65.00, "discount_percentage": 13.3, "calories": 1820, "popularity": "100+ orders"},
        ],
    },
    "ab_jeddah_main": {
        "Chicken": [
            {"name_en": "4-piece Chicken Meal", "name_ar": "وجبة دجاج 4 قطع", "base_price": 22.00, "calories": 850, "popularity": "1000+ orders"},
            {"name_en": "Shrimp Meal", "name_ar": "وجبة روبيان", "base_price": 28.00, "calories": 720, "popularity": "500+ orders"},
        ],
    },
}

PROMOTIONS = [
    {
        "restaurant_external_id": "hs_albaik_olaya",
        "promo_type": "FREE_DELIVERY",
        "name_en": "Free delivery on orders over 30 SAR",
        "name_ar": "توصيل مجاني للطلبات أكثر من 30 ريال",
        "category": "BLUE",
        "minimum_order_sar": Decimal("30.00"),
        "free_delivery": True,
    },
    {
        "restaurant_external_id": "hs_mcdonalds_olaya",
        "promo_type": "MENU_ITEM_DISCOUNT",
        "name_en": "20% off all burgers",
        "name_ar": "خصم 20% على جميع البرجر",
        "category": "RED",
        "discount_percentage": Decimal("20.00"),
    },
    {
        "restaurant_external_id": "hs_cafeboulud_jeddah",
        "promo_type": "ORDER_PERCENTAGE_CUTBACK",
        "name_en": "15% off entire order",
        "name_ar": "خصم 15% على الطلب",
        "category": "RED",
        "discount_percentage": Decimal("15.00"),
        "minimum_order_sar": Decimal("80.00"),
    },
]


async def seed_users(db):
    user_map = {}
    for u_data in USERS:
        u = u_data.copy()
        existing = (await db.execute(select(User).where(User.email == u["email"]))).scalar_one_or_none()
        if existing:
            user_map[u["email"]] = existing
            print(f"  - User exists: {u['email']}")
            continue
        password = u.pop("password")
        is_admin = u.pop("is_admin", False)
        user = User(**u, hashed_password=hash_password(password), is_admin=is_admin, is_active=True)
        db.add(user)
        await db.flush()
        user_map[user.email] = user
        print(f"  + User created: {user.email}  (password: {password})")
    return user_map


async def seed_addresses(db, user_map):
    for a_data in ADDRESSES:
        user = user_map.get(a_data["user_email"])
        if not user:
            continue
        existing = (await db.execute(
            select(UserAddress).where(UserAddress.user_id == user.id, UserAddress.label == a_data["label"])
        )).scalar_one_or_none()
        if existing:
            print(f"  - Address exists: {user.email} / {a_data['label']}")
            continue
        addr = UserAddress(
            user_id=user.id,
            label=a_data["label"],
            address_line=a_data["address_line"],
            city=a_data["city"],
            district=a_data.get("district"),
            country="SA",
            latitude=a_data["latitude"],
            longitude=a_data["longitude"],
            is_default=a_data["is_default"],
        )
        db.add(addr)
        print(f"  + Address created: {user.email} / {a_data['label']}")


async def seed_sources(db):
    source_map = {}
    for s in SOURCES:
        existing = (await db.execute(text("SELECT id FROM sources WHERE name = :n"), {"n": s["name"]})).scalar_one_or_none()
        if existing:
            source_map[s["name"]] = existing
            print(f"  - Source exists: {s['name']}")
            continue
        result = await db.execute(
            text("INSERT INTO sources (name, display_name, source_type, is_active) VALUES (:name, :display_name, :source_type, true) RETURNING id"),
            s,
        )
        sid = result.scalar_one()
        source_map[s["name"]] = sid
        print(f"  + Source created: {s['name']} (id={sid})")
    return source_map


async def seed_restaurants(db, source_map):
    rest_map = {}
    for r in RESTAURANTS:
        source_id = source_map[r["source_name"]]
        existing = (await db.execute(
            text("SELECT id FROM restaurants WHERE source_id = :sid AND external_id = :eid"),
            {"sid": source_id, "eid": r["external_id"]},
        )).scalar_one_or_none()
        if existing:
            rest_map[r["external_id"]] = existing
            print(f"  - Restaurant exists: {r['name_en']}")
            continue
        rid = uuid4()
        await db.execute(
            text("""
                INSERT INTO restaurants (
                    id, source_id, external_id, chain_id, chain_name,
                    name_en, name_ar, vertical, cuisines,
                    rating, rate_count, latitude, longitude, city, district,
                    delivery_fee, minimum_order_sar, price_range, eta_min, eta_max,
                    is_most_loved, is_active, admin_disabled, supports_pickup
                ) VALUES (
                    :id, :source_id, :external_id, :chain_id, :chain_name,
                    :name_en, :name_ar, :vertical, CAST(:cuisines AS jsonb),
                    :rating, :rate_count, :latitude, :longitude, :city, :district,
                    :delivery_fee, :minimum_order_sar, :price_range, :eta_min, :eta_max,
                    :is_most_loved, true, false, false
                )
            """),
            {
                "id": rid,
                "source_id": source_id,
                "external_id": r["external_id"],
                "chain_id": r.get("chain_id"),
                "chain_name": r.get("chain_name"),
                "name_en": r["name_en"],
                "name_ar": r.get("name_ar"),
                "vertical": r.get("vertical"),
                "cuisines": json.dumps(r.get("cuisines", [])),
                "rating": r.get("rating"),
                "rate_count": r.get("rate_count"),
                "latitude": r.get("latitude"),
                "longitude": r.get("longitude"),
                "city": r.get("city"),
                "district": r.get("district"),
                "delivery_fee": r.get("delivery_fee"),
                "minimum_order_sar": r.get("minimum_order_sar"),
                "price_range": r.get("price_range"),
                "eta_min": r.get("eta_min"),
                "eta_max": r.get("eta_max"),
                "is_most_loved": r.get("is_most_loved", False),
            },
        )
        rest_map[r["external_id"]] = rid
        print(f"  + Restaurant created: {r['name_en']}")
    return rest_map


async def seed_menu(db, rest_map):
    for ext_id, sections in MENU_ITEMS.items():
        rid = rest_map.get(ext_id)
        if not rid:
            continue
        for sort_idx, (section_name, items) in enumerate(sections.items()):
            sid = (await db.execute(
                text("SELECT id FROM menu_sections WHERE restaurant_id = :rid AND name_en = :name"),
                {"rid": rid, "name": section_name},
            )).scalar_one_or_none()
            if not sid:
                sid = uuid4()
                await db.execute(
                    text("INSERT INTO menu_sections (id, restaurant_id, name_en, sort_order) VALUES (:id, :rid, :name, :sort)"),
                    {"id": sid, "rid": rid, "name": section_name, "sort": sort_idx},
                )
            for item in items:
                existing = (await db.execute(
                    text("SELECT id FROM menu_items WHERE section_id = :sid AND name_en = :name"),
                    {"sid": sid, "name": item["name_en"]},
                )).scalar_one_or_none()
                if existing:
                    continue
                await db.execute(
                    text("""
                        INSERT INTO menu_items (
                            id, section_id, restaurant_id, name_en, name_ar,
                            base_price, list_price, discounted_price, discount_percentage,
                            calories, popularity_text, item_type, is_available
                        ) VALUES (
                            :id, :sid, :rid, :name_en, :name_ar,
                            :base_price, :list_price, :discounted_price, :discount_percentage,
                            :calories, :popularity, 'PRODUCT', true
                        )
                    """),
                    {
                        "id": uuid4(),
                        "sid": sid,
                        "rid": rid,
                        "name_en": item["name_en"],
                        "name_ar": item.get("name_ar"),
                        "base_price": item["base_price"],
                        "list_price": item.get("list_price"),
                        "discounted_price": item.get("discounted_price"),
                        "discount_percentage": item.get("discount_percentage"),
                        "calories": item.get("calories"),
                        "popularity": item.get("popularity"),
                    },
                )
        print(f"  + Menu seeded for: {ext_id}")


async def seed_promotions(db, rest_map):
    for p in PROMOTIONS:
        rid = rest_map.get(p["restaurant_external_id"])
        if not rid:
            continue
        existing = (await db.execute(
            text("SELECT id FROM promotions WHERE restaurant_id = :rid AND name_en = :name"),
            {"rid": rid, "name": p["name_en"]},
        )).scalar_one_or_none()
        if existing:
            print(f"  - Promo exists: {p['name_en']}")
            continue
        await db.execute(
            text("""
                INSERT INTO promotions (
                    id, restaurant_id, promo_type, name_en, name_ar, category,
                    minimum_order_sar, discount_percentage, discount_fixed_sar, free_delivery,
                    is_active, starts_at, expires_at
                ) VALUES (
                    :id, :rid, :promo_type, :name_en, :name_ar, :category,
                    :minimum_order_sar, :discount_percentage, :discount_fixed_sar, :free_delivery,
                    true, NOW(), NOW() + INTERVAL '30 days'
                )
            """),
            {
                "id": uuid4(),
                "rid": rid,
                "promo_type": p["promo_type"],
                "name_en": p["name_en"],
                "name_ar": p.get("name_ar"),
                "category": p.get("category"),
                "minimum_order_sar": p.get("minimum_order_sar"),
                "discount_percentage": p.get("discount_percentage"),
                "discount_fixed_sar": p.get("discount_fixed_sar"),
                "free_delivery": p.get("free_delivery", False),
            },
        )
        print(f"  + Promo created: {p['name_en']}")


async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    print("\nSeeding Mallah test data...\n")
    async with SessionLocal() as db:
        print("== Users ==")
        user_map = await seed_users(db)
        print("\n== Addresses ==")
        await seed_addresses(db, user_map)
        print("\n== Sources ==")
        source_map = await seed_sources(db)
        print("\n== Restaurants ==")
        rest_map = await seed_restaurants(db, source_map)
        print("\n== Menus ==")
        await seed_menu(db, rest_map)
        print("\n== Promotions ==")
        await seed_promotions(db, rest_map)
        await db.commit()
    await engine.dispose()
    print("\nSeed complete\n")
    print("Login credentials:")
    print("  test_consumer@mallah.dev  /  consumer_pw_123  (Riyadh, has 2 addresses)")
    print("  test_user2@mallah.dev     /  user2_pw_123     (Jeddah, has 1 address)")
    print("  test_admin@mallah.dev     /  admin_pw_123     (admin flag set)")


if __name__ == "__main__":
    asyncio.run(main())
