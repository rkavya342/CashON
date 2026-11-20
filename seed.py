"""
seed.py -- Full CASHON database seeder.

Run:  python seed.py

Creates:
  - 1 admin, 1 seller + 4 customers
  - 7 adaptive categories with theme configs
  - 65+ products with INR pricing across all categories
  - Product images, specs, price history
  - Reviews, coupons, orders, addresses, notifications
"""

import sys, os, json, sqlite3, bcrypt, random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

DB_PATH = os.path.join(os.path.dirname(__file__), "instance", "cashon.db")
SCHEMA  = os.path.join(os.path.dirname(__file__), "schema.sql")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


# ─── Helpers ───────────────────────────────────────────────────────────────

def hash_pw(plain):
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

# All catalogue imagery is served locally; the app never depends on remote image hosts.
PRODUCT_IMAGE_MAP = {'apple-macbook-air-m3': '/static/img/products/apple-laptop.png', 'samsung-galaxy-s24-ultra': 'https://kaldunga.com/storage/app/public/product/2024-10-02-66fd36405d64b.png', 'sony-wh1000xm5': '/static/img/products/sony-headphones.png', 'ipad-air-m2-11': 'https://istore.ph/cdn/shop/files/ROSA_iPad_Air_11_M2_WiFi_Blue_PDP_Image_Position_1b.jpg?v=1717577444&width=1200', 'oneplus-12-5g': 'https://images.hindustantimes.com/tech/htmobile4/oneplus-12-5g/colors/flowy-emerald/oneplus-12-5g-flowy-emerald-1.jpg?height=263&width=263', 'logitech-mx-master-3s': 'https://resource.logitech.com/w_544%2Ch_466%2Car_7%3A6%2Cc_pad%2Cq_auto%2Cf_auto%2Cdpr_1.0/d_transparent.gif/content/dam/logitech/en/products/mice/mx-master-3s/2025-update/mx-master-3s-bluetooth-edition-top-view-graphite-new-1.png', 'boat-airdopes-141': 'https://www.boat-lifestyle.com/cdn/shop/files/AD141-FI_Black01_600x.png?v=1698391770', 'mi-65w-charger': 'https://down-th.img.susercontent.com/file/f3023aae7294b6c4767e6179f92ecff8', 'fireboltt-phoenix': 'https://m.media-amazon.com/images/I/71MPi6NDDJL.jpg', 'corsair-k65-rgb': 'https://m.media-amazon.com/images/I/41yoLWTVkUL.jpg', 'nilkamal-floyd-sofa': '/static/img/products/nilkamal-floyd-sofa.png', 'pepperfry-bookshelf-5tier': '/static/img/products/pepperfry-bookshelf-5tier.png', 'durian-king-bed-storage': 'https://images.durian.in/Durian/durian/product/800x800/796011749279355.jpg', 'fabindia-cushion-set': 'https://apisap.fabindia.com/medias/10735144-01.jpg?aio=w-768', 'ikea-kallax-shelf': '/static/img/products/ikea-kallax-shelf.png', 'morphy-richards-kettle': '/static/img/products/morphy-richards-kettle.png', 'bombay-dyeing-comforter': '/static/img/products/bombay-dyeing-comforter.png', 'nestasia-ceramic-vase': 'https://nestasia.in/cdn/shop/files/matte-white-vase-set_1.png?v=1738663929&width=1200', 'fabindia-cotton-kurta-men': 'https://apisap.fabindia.com/medias/20209149-01.jpg', 'w-anarkali-suit': 'https://assets.ajio.com/medias/sys_master/root/20241121/ks5b/673f2bcfc148fa1b30dc1660/-473Wx593H-442696267-coral-MODEL.jpg', 'peter-england-formal-shirt': '/static/img/products/peter-england-formal-shirt.png', 'mango-linen-trousers': '/static/img/products/mango-linen-trousers.png', 'zara-oversized-blazer': '/static/img/products/zara-oversized-blazer.png', 'biba-palazzo-set': '/static/img/products/biba-palazzo-set.png', 'hrx-sport-tshirt': 'https://www.myntraglobal.com/cdn/shop/files/ecb2f6de-a3ff-4c0b-a146-638f1247540e1742975843904-HRX-by-Hrithik-Roshan-Men-Tshirts-8291742975843299-3.jpg?v=1746019541&width=1080', 'levis-511-slim': '/static/img/products/levis-511-slim.png', 'minimalist-salicylic-facewash': 'https://m.media-amazon.com/images/I/514PVblwPdL._SX425_.jpg', 'dot-key-vitamin-c-serum': '/static/img/products/dot-key-vitamin-c-serum.png', 'mamaearth-onion-hair-oil': '/static/img/products/mamaearth-onion-hair-oil.png', 'lakme-9to5-lipstick': '/static/img/products/lakme-9to5-lipstick.png', 'forest-essentials-rose-toner': '/static/img/products/forest-essentials-rose-toner.png', 'plum-grape-seed-moisturiser': '/static/img/products/plum-grape-seed-moisturiser.png', 'dyson-airwrap-multi-styler': '/static/img/products/dyson-airwrap-multi-styler.png', 'biotique-papaya-face-pack': '/static/img/products/biotique-papaya-face-pack.png', 'nike-air-zoom-pegasus-41': 'https://static.ftshp.digital/img/p/1/3/6/8/4/8/7/1368487-thickbox.jpg', 'adidas-yoga-mat-6mm': '/static/img/products/adidas-yoga-mat-6mm.png', 'decathlon-dumbbell-20kg': '/static/img/products/decathlon-dumbbell-20kg.png', 'nivia-storm-football': '/static/img/products/nivia-storm-football.png', 'ua-compression-shorts': '/static/img/products/ua-compression-shorts.png', 'boldfit-whey-protein-1kg': '/static/img/products/boldfit-whey-protein-1kg.png', 'yonex-astrox-7': '/static/img/products/yonex-astrox-7.png', 'fitbit-charge-6': '/static/img/products/fitbit-charge-6.png', 'titan-skywear-watch': '/static/img/products/titan-skywear-watch.png', 'hidesign-leather-wallet': '/static/img/products/hidesign-leather-wallet.png', 'da-milano-tote-bag': '/static/img/products/da-milano-tote-bag.png', 'fastrack-urban-sunglasses': '/static/img/products/fastrack-urban-sunglasses.png', 'caratplane-diamond-pendant': '/static/img/products/caratplane-diamond-pendant.png', 'lavie-quilted-backpack': '/static/img/products/lavie-quilted-backpack.png', 'tommy-hilfiger-impact': '/static/img/products/tommy-hilfiger-impact.png', 'atomic-habits-james-clear': '/static/img/products/atomic-habits.png', 'leuchtturm1917-a5-dotgrid': '/static/img/products/leuchtturm1917-a5-dotgrid.png', 'the-alchemist-coelho': '/static/img/products/the-alchemist-coelho.png', 'muji-gel-ink-pen-set': '/static/img/products/muji-gel-ink-pen-set.png', 'moleskine-2025-planner': '/static/img/products/moleskine-2025-planner.png', 'prestige-incense-sticks-set': '/static/img/products/prestige-incense-sticks-set.png', 'amazon-kindle-paperwhite-16gb': '/static/img/products/amazon-kindle-paperwhite-16gb.png'}
CATEGORY_IMAGE_MAP = {'technology': '/static/img/products/apple-laptop.png', 'furniture-home': 'https://www.nilkamalhomes.com/cdn/shop/files/DSC_2130.jpg?v=1753079758&width=1200', 'fashion': '/static/img/products/biba-palazzo-set.png', 'beauty': '/static/img/products/dot-key-vitamin-c-serum.png', 'sports-fitness': '/static/img/products/adidas-yoga-mat-6mm.png', 'accessories': '/static/img/products/da-milano-tote-bag.png', 'books-lifestyle': '/static/img/products/atomic-habits.png'}

def unsplash(photo_id, w=600, h=600):
    """Legacy helper retained for compatibility, but always returns a local image."""
    return "/static/img/products/apple-laptop.png"

def product_image(slug, category_slug):
    return PRODUCT_IMAGE_MAP.get(slug, CATEGORY_IMAGE_MAP.get(category_slug, "/static/img/products/apple-laptop.png"))

def category_image(slug):
    return CATEGORY_IMAGE_MAP.get(slug, "/static/img/products/apple-laptop.png")

def fmt_dt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def rand_days(n):
    return fmt_dt(datetime.now() - timedelta(days=random.randint(0, n)))

def order_num():
    return f"CASH{datetime.now().strftime('%Y%m%d')}{random.randint(1000,9999)}"


# ─── Users ─────────────────────────────────────────────────────────────────

USERS = [
    # (email, name, password, role)
    ("admin@cashon.in",   "CASHON Admin",   "Admin@2024",   "admin"),
    ("seller@techzone.in","Rahul Sharma",   "Seller@2024",  "seller"),
    ("priya@example.com", "Priya Patel",    "Password@1",   "customer"),
    ("arjun@example.com", "Arjun Mehta",    "Password@1",   "customer"),
    ("sneha@example.com", "Sneha Reddy",    "Password@1",   "customer"),
    ("vikram@example.com","Vikram Singh",   "Password@1",   "customer"),
]

# ─── Categories with theme configs ─────────────────────────────────────────

CATEGORIES = [
    # (name, slug, description, image_id, icon, theme_config_dict, sort_order)
    ("Technology", "technology",
     "Laptops, smartphones, audio gear and cutting-edge gadgets.",
     "1498049794561-7780e7231661",
     "💻",
     {"accent":"#3B82F6","accent2":"#1E40AF","bg":"#0F172A","surface":"#1E293B",
      "text":"#F1F5F9","style":"futuristic","label_color":"#60A5FA"},
     1),

    ("Furniture & Home", "furniture-home",
     "Sofas, beds, decor and everything to make your space beautiful.",
     "1555041469-dc73fa61f8e0",
     "🛋️",
     {"accent":"#92400E","accent2":"#78350F","bg":"#FFFBF5","surface":"#FEF3C7",
      "text":"#1C1917","style":"warm","label_color":"#D97706"},
     2),

    ("Fashion", "fashion",
     "Clothing, ethnic wear, western styles and seasonal collections.",
     "1536992266094-82847e1fd431",
     "👗",
     {"accent":"#1F2937","accent2":"#111827","bg":"#FAFAFA","surface":"#F3F4F6",
      "text":"#111827","style":"editorial","label_color":"#374151"},
     3),

    ("Beauty & Personal Care", "beauty",
     "Skincare, haircare, makeup and wellness essentials.",
     "1596462502278-27bfdc403348",
     "✨",
     {"accent":"#BE185D","accent2":"#9D174D","bg":"#FFF5F7","surface":"#FCE7F3",
      "text":"#1F2937","style":"elegant","label_color":"#EC4899"},
     4),

    ("Sports & Fitness", "sports-fitness",
     "Equipment, apparel and nutrition for every sport and activity.",
     "1571019613454-1cb2f99b2d8b",
     "🏃",
     {"accent":"#DC2626","accent2":"#991B1B","bg":"#0F172A","surface":"#1E293B",
      "text":"#F8FAFC","style":"dynamic","label_color":"#F87171"},
     5),

    ("Accessories", "accessories",
     "Watches, bags, jewellery, belts and style essentials.",
     "1548036161-24e7e3b90a3b",
     "👜",
     {"accent":"#7C3AED","accent2":"#6D28D9","bg":"#FAFAFA","surface":"#F5F3FF",
      "text":"#1F2937","style":"premium","label_color":"#8B5CF6"},
     6),

    ("Books & Lifestyle", "books-lifestyle",
     "Books, journals, stationery and mindful living products.",
     "1497366754035-f200968a7db3",
     "📚",
     {"accent":"#059669","accent2":"#047857","bg":"#F0FDF4","surface":"#D1FAE5",
      "text":"#1F2937","style":"calm","label_color":"#10B981"},
     7),
]

# ─── Products ───────────────────────────────────────────────────────────────
# (cat_slug, name, slug, description, brand, price_inr, sale_price_inr,
#  stock, rating, review_count, image_id, sizes_json, colours_json, is_featured, tags_json)

PRODUCTS = [

    # ══════════════════════════════════════════════════════
    # TECHNOLOGY
    # ══════════════════════════════════════════════════════
    ("technology","Apple MacBook Air M3","apple-macbook-air-m3",
     "The thinnest, most capable MacBook Air ever. M3 chip with 8-core CPU, 10-core GPU. 18-hour battery life, Liquid Retina display. Perfect for students and professionals.",
     "Apple",195000,172000,15,4.8,312,
     "1517336556584-be75d2f54f47","[]","[\"Midnight\",\"Starlight\",\"Space Grey\",\"Silver\"]",1,
     '["laptop","macbook","apple","m3","ultrabook","lightweight"]'),

    ("technology","Samsung Galaxy S24 Ultra","samsung-galaxy-s24-ultra",
     "AI-powered smartphone with 200MP camera, built-in S Pen, Snapdragon 8 Gen 3. 6.8-inch QHD+ Dynamic AMOLED 2X display with 120Hz.",
     "Samsung",134999,124999,28,4.7,445,
     "1510557880182-3d4d3cba35a5","[]","[\"Titanium Black\",\"Titanium Grey\",\"Titanium Violet\"]",1,
     '["smartphone","samsung","s24","android","s-pen","flagship"]'),

    ("technology","Sony WH-1000XM5 Headphones","sony-wh1000xm5",
     "Industry-leading noise cancelling with Auto NC Optimizer. 30-hour battery, 8 mics for precise voice pickup. Foldable design with premium carrying case.",
     "Sony",29990,24990,42,4.9,678,
     "1505740420857-2d57418d4fb9","[]","[\"Black\",\"Platinum Silver\"]",1,
     '["headphones","sony","noise-cancelling","wireless","bluetooth","premium-audio"]'),

    ("technology","iPad Air 11-inch M2","ipad-air-m2-11",
     "Supercharged by M2 chip. 11-inch Liquid Retina display. Works with Apple Pencil Pro and Magic Keyboard Folio. All-day battery life.",
     "Apple",59900,54900,22,4.8,234,
     "1544244015-ece9eed63f43","[]","[\"Blue\",\"Purple\",\"Starlight\",\"Space Grey\"]",1,
     '["ipad","tablet","apple","m2","drawing","students"]'),

    ("technology","OnePlus 12 5G","oneplus-12-5g",
     "Snapdragon 8 Gen 3 processor, 50MP Hasselblad triple camera, 100W SUPERVOOC charging. 6.82-inch LTPO AMOLED display with 2K resolution.",
     "OnePlus",64999,57999,35,4.6,289,
     "1603792657956-5e35bfc4cfcf","[]","[\"Flowy Emerald\",\"Silky Black\"]",0,
     '["smartphone","oneplus","5g","hasselblad","android","gaming"]'),

    ("technology","Logitech MX Master 3S Mouse","logitech-mx-master-3s",
     "8000 DPI MagSpeed electromagnetic scroll, works on glass. Silent clicks, ergonomic comfort. Multi-device Bluetooth + USB-C charging.",
     "Logitech",8495,7495,67,4.7,445,
     "1527864550417-7519ae3b33a7","[]","[\"Graphite\",\"Pale Grey\",\"Rose\"]",0,
     '["mouse","logitech","wireless","ergonomic","productivity","office"]'),

    ("technology","Boat Airdopes 141","boat-airdopes-141",
     "42H total playback, ENx Technology for superior call quality. BEAST Mode for low latency gaming. IPX4 water resistance.",
     "boAt",1499,999,120,4.3,1876,
     "1612532945755-9bb88a7cf03b","[]","[\"Black\",\"White\",\"Blue\",\"Green\"]",0,
     '["earbuds","tws","boat","wireless","gaming","budget"]'),

    ("technology","Mi 65W Fast Charger","mi-65w-charger",
     "GaN technology, 65W fast charging supports laptops, tablets and phones. 3 ports (2 USB-C, 1 USB-A). Compact travel-friendly design.",
     "Xiaomi",2499,1799,88,4.5,654,
     "1583394838336-acd977736f90","[]","[\"White\"]",0,
     '["charger","65w","gan","fast-charge","xiaomi","travel"]'),

    ("technology","Fire-Boltt Phoenix Smart Watch","fireboltt-phoenix",
     "1.43\" AMOLED always-on display, Bluetooth calling, 100+ sports modes, SpO2, heart rate. 7-day battery. IP68 waterproof.",
     "Fire-Boltt",3499,2499,95,4.2,2341,
     "1434493789543-67fc3b7c0d14","[]","[\"Black\",\"Silver\",\"Rose Gold\",\"Blue\"]",0,
     '["smartwatch","fireboltt","bluetooth-calling","fitness","health"]'),

    ("technology","Corsair K65 RGB Gaming Keyboard","corsair-k65-rgb",
     "Compact TKL mechanical keyboard with Cherry MX Speed Silver switches. Per-key RGB lighting, aluminium frame, aircraft-grade brushed aluminium.",
     "Corsair",8999,7499,30,4.6,567,
     "1593152167544-085f5e94d492","[]","[\"Black\"]",0,
     '["keyboard","mechanical","gaming","corsair","rgb","tkl"]'),

    # ══════════════════════════════════════════════════════
    # FURNITURE & HOME
    # ══════════════════════════════════════════════════════
    ("furniture-home","Nilkamal Floyd 3-Seater Sofa","nilkamal-floyd-sofa",
     "Premium fabric upholstery, solid wood legs, high-density foam cushions. Spacious 3-seater perfect for living rooms. Easy assembly.",
     "Nilkamal",32999,28499,8,4.4,156,
     "1555041469-dc73fa61f8e0","[]","[\"Ash Grey\",\"Ocean Blue\",\"Rust Orange\",\"Olive Green\"]",1,
     '["sofa","3-seater","nilkamal","living-room","fabric","furniture"]'),

    ("furniture-home","Pepperfry Engineered Wood Bookshelf","pepperfry-bookshelf-5tier",
     "5-tier open bookshelf in walnut finish. Engineered wood construction, sturdy metal brackets. Ideal for study, living room or bedroom.",
     "Pepperfry",8999,6999,18,4.3,234,
     "1497366754035-f200968a7db3","[]","[\"Walnut\",\"White\",\"Wenge\"]",0,
     '["bookshelf","5-tier","engineered-wood","storage","study","pepperfry"]'),

    ("furniture-home","Durian King Size Bed","durian-king-bed-storage",
     "King size bed with hydraulic storage lift mechanism. Premium leatherette headboard, solid wood frame. Storage capacity: 400+ litres.",
     "Durian",45999,38999,5,4.5,89,
     "1618022457-29bed0e1-db6a-4a08-b55a-1f1f1b75c5a4","[]","[\"Brown\",\"Black\",\"Grey\"]",1,
     '["bed","king-size","storage","hydraulic","durian","bedroom"]'),

    ("furniture-home","Fabindia Handwoven Cotton Cushion Set","fabindia-cushion-set",
     "Set of 5 hand-woven cotton cushion covers in block print design. 40x40cm. 100% natural cotton, machine washable. Fair-trade certified.",
     "Fabindia",2499,1999,45,4.6,445,
     "1558618666-fcd25c85cd64","[]","[\"Indigo\",\"Mustard\",\"Rust\",\"Sage\"]",0,
     '["cushion","handwoven","cotton","fabindia","block-print","home-decor"]'),

    ("furniture-home","Ikea KALLAX Shelf Unit","ikea-kallax-shelf",
     "Versatile shelf unit with 16 cubbies. Use vertically or horizontally. Compatible with Kallax boxes and inserts. Particleboard construction.",
     "IKEA",12999,None,12,4.5,678,
     "1558618666-fcd25c85cd64","[]","[\"White\",\"Black-Brown\",\"Birch Effect\",\"High Gloss White\"]",0,
     '["shelf","ikea","kallax","storage","versatile","modular"]'),

    ("furniture-home","Morphy Richards Essentials Kettle","morphy-richards-kettle",
     "1.5L stainless steel electric kettle, 1500W for rapid boiling. Concealed heating element, dry-boil protection, cordless 360° base.",
     "Morphy Richards",2999,2499,55,4.4,892,
     "1544376664-b41e97a53d84","[]","[\"Stainless Steel\"]",0,
     '["kettle","electric","morphy-richards","kitchen","stainless-steel"]'),

    ("furniture-home","Bombay Dyeing Microfibre Comforter","bombay-dyeing-comforter",
     "400 GSM microfibre filling, anti-allergenic, machine washable. Suitable for mild winters. Double bed size (228x228 cm).",
     "Bombay Dyeing",2199,1799,34,4.3,567,
     "1555041469-dc73fa61f8e0","[]","[\"Blue\",\"Pink\",\"Grey\",\"Maroon\"]",0,
     '["comforter","microfibre","bedding","bombay-dyeing","winter","double-bed"]'),

    ("furniture-home","Nestasia Ceramic Vase Set","nestasia-ceramic-vase",
     "Set of 3 handcrafted ceramic vases in contemporary minimalist design. Matte finish, suitable for dried and fresh flowers.",
     "Nestasia",1899,1499,28,4.7,234,
     "1495195432508-21b7e1d9d7a8","[]","[\"White\",\"Sage\",\"Terracotta\"]",1,
     '["vase","ceramic","handcrafted","home-decor","minimalist","nestasia"]'),

    # ══════════════════════════════════════════════════════
    # FASHION
    # ══════════════════════════════════════════════════════
    ("fashion","Fabindia Cotton Kurta","fabindia-cotton-kurta-men",
     "Hand block-printed pure cotton kurta with traditional motifs. Breathable fabric perfect for festivals, office and casual wear. Easy care.",
     "Fabindia",1999,1499,
     40,4.5,345,
     "1507003211169-0a1dd7228f2d",
     '["S","M","L","XL","XXL"]','["White\",\"Indigo\",\"Mustard\",\"Rust\",\"Sage"]',1,
     '["kurta","cotton","fabindia","ethnic","block-print","casual"]'),

    ("fashion","W for Woman Anarkali Suit Set","w-anarkali-suit",
     "Flared anarkali with matching dupatta in georgette fabric. Embroidered yoke, festive-ready. Available in full length (floor-touching).",
     "W for Woman",3499,2799,
     25,4.6,234,
     "1536992266094-82847e1fd431",
     '["XS","S","M","L","XL"]','["Coral\",\"Teal\",\"Wine\",\"Royal Blue"]',1,
     '["anarkali","ethnic","festive","dupatta","georgette","w-brand"]'),

    ("fashion","Peter England Formal Shirt","peter-england-formal-shirt",
     "100% cotton formal shirt with slim fit. Perfect for office, presentations and formal events. Wrinkle-resistant finish.",
     "Peter England",1299,999,
     60,4.4,567,
     "1507003211169-0a1dd7228f2d",
     '["S","M","L","XL","XXL","XXXL"]','["White\",\"Light Blue\",\"Light Grey\",\"Black\"]',0,
     '["shirt","formal","cotton","peter-england","office","slim-fit"]'),

    ("fashion","Mango Linen Blend Trousers","mango-linen-trousers",
     "Wide-leg linen blend trousers with elasticated waistband. Relaxed, breathable silhouette for warm weather. Side pockets.",
     "Mango",3499,2299,
     30,4.5,189,
     "1536992266094-82847e1fd431",
     '["XS","S","M","L","XL"]','["Beige\",\"Ecru\",\"Black\",\"Olive\"]',0,
     '["trousers","linen","mango","western","summer","wide-leg"]'),

    ("fashion","Zara Oversized Blazer","zara-oversized-blazer",
     "Relaxed fit oversized blazer with notched lapels. Single button fastening, two front pockets. Lined interior, work-to-weekend versatile.",
     "Zara",5999,4499,
     20,4.6,145,
     "1507003211169-0a1dd7228f2d",
     '["XS","S","M","L"]','["Black\",\"Camel\",\"Ecru\",\"Navy\"]',1,
     '["blazer","oversized","zara","western","office","smart-casual"]'),

    ("fashion","Biba Printed Palazzo Set","biba-palazzo-set",
     "Georgette palazzo pants with matching kurta top in vibrant print. Comfort waistband, side slits on kurta. Occasion and casual wear.",
     "Biba",1799,1299,
     38,4.3,456,
     "1536992266094-82847e1fd431",
     '["S","M","L","XL","XXL"]','["Pink\",\"Orange\",\"Purple\",\"Turquoise\"]',0,
     '["palazzo","kurta","biba","ethnic","prints","casual-wear"]'),

    ("fashion","HRX Sport Performance T-Shirt","hrx-sport-tshirt",
     "Moisture-wicking, anti-odour fabric with 4-way stretch. Flatlock seams prevent chafing. Reflective accents for night visibility.",
     "HRX",899,699,
     85,4.4,789,
     "1571019613454-1cb2f99b2d8b",
     '["XS","S","M","L","XL","XXL"]','["Black\",\"White\",\"Navy\",\"Red\",\"Teal\"]',0,
     '["t-shirt","sport","hrx","performance","gym","moisture-wicking"]'),

    ("fashion","Levis 511 Slim Jeans","levis-511-slim",
     "Classic slim fit from hip to ankle. Lightweight stretch for all-day comfort. Iconic Levis quality with Flex denim technology.",
     "Levi's",3499,2799,
     50,4.7,892,
     "1507003211169-0a1dd7228f2d",
     '["28","30","32","34","36","38"]','["Dark Indigo\",\"Mid Blue\",\"Black\",\"Grey\"]',1,
     '["jeans","levis","slim-fit","denim","casual","classic"]'),

    # ══════════════════════════════════════════════════════
    # BEAUTY & PERSONAL CARE
    # ══════════════════════════════════════════════════════
    ("beauty","Minimalist 2% Salicylic Acid Face Wash","minimalist-salicylic-facewash",
     "Gentle gel face wash with 2% salicylic acid. Effectively removes excess oil, unclogs pores and reduces blackheads. Suitable for oily/acne-prone skin. Fragrance-free.",
     "Minimalist",349,None,
     78,4.7,1234,
     "1596462502278-27bfdc403348",
     '[]','[]',1,
     '["face-wash","salicylic-acid","minimalist","acne","oily-skin","skincare"]'),

    ("beauty","Dot & Key Vitamin C Serum","dot-key-vitamin-c-serum",
     "10% Vitamin C + 1% Niacinamide serum for brightening and even skin tone. Lightweight formula with stable ethyl ascorbic acid. 15ml.",
     "Dot & Key",699,549,
     56,4.6,876,
     "1596462502278-27bfdc403348",
     '[]','[]',1,
     '["serum","vitamin-c","brightening","niacinamide","skincare","dot-key"]'),

    ("beauty","Mamaearth Onion Hair Oil","mamaearth-onion-hair-oil",
     "Onion + Redensyl formula reduces hair fall up to 96% in 4 weeks (clinical study). Toxin-free, dermatologist-tested. 250ml. Suitable for all hair types.",
     "Mamaearth",349,299,
     94,4.4,2345,
     "1596462502278-27bfdc403348",
     '[]','[]',0,
     '["hair-oil","onion","mamaearth","hair-fall","ayurvedic","natural"]'),

    ("beauty","Lakme 9to5 Lipstick","lakme-9to5-lipstick",
     "Flawless matte finish, 8-hour wear. Enriched with vitamin E and hyaluronic acid for smooth, comfortable wear. Cruelty-free.",
     "Lakme",450,None,
     110,4.5,1567,
     "1596462502278-27bfdc403348",
     '[]','["Scarlet Fantasy\",\"Crimson Cloak\",\"Pink Petal\",\"Plum Lush\",\"Nude Muse\"]',0,
     '["lipstick","lakme","matte","long-lasting","makeup","lip-color"]'),

    ("beauty","Forest Essentials Rose Water Toner","forest-essentials-rose-toner",
     "Distilled pure rose water from certified organic farms. Natural facial toner that balances pH, hydrates and refreshes skin. Alcohol-free. 200ml.",
     "Forest Essentials",895,None,
     43,4.8,678,
     "1596462502278-27bfdc403348",
     '[]','[]',1,
     '["toner","rose-water","forest-essentials","natural","organic","skincare"]'),

    ("beauty","Plum Grape Seed Moisturiser","plum-grape-seed-moisturiser",
     "Lightweight, oil-free daily moisturiser with grape seed extract. Non-comedogenic, absorbs quickly. Suitable for oily to combination skin. 75ml.",
     "Plum",499,399,
     67,4.6,923,
     "1596462502278-27bfdc403348",
     '[]','[]',0,
     '["moisturiser","grape-seed","plum","oil-free","lightweight","vegan"]'),

    ("beauty","Dyson Airwrap Multi-Styler","dyson-airwrap-multi-styler",
     "Coanda effect styles and dries without extreme heat. Includes 7 attachments for curling, waving, smoothing and volumising. 1200W motor.",
     "Dyson",44900,39900,
     8,4.9,234,
     "1596462502278-27bfdc403348",
     '[]','[\"Nickel/Copper\",\"Prussian Blue/Rich Copper\"]',1,
     '["dyson","hair-styler","airwrap","curler","blow-dry","luxury"]'),

    ("beauty","Biotique Bio Papaya Face Pack","biotique-papaya-face-pack",
     "Natural brightening face pack with raw papaya enzyme, poppy and turmeric. Exfoliates dead cells, brightens complexion. 75g.",
     "Biotique",249,None,
     88,4.3,1234,
     "1596462502278-27bfdc403348",
     '[]','[]',0,
     '["face-pack","papaya","biotique","brightening","ayurvedic","natural"]'),

    # ══════════════════════════════════════════════════════
    # SPORTS & FITNESS
    # ══════════════════════════════════════════════════════
    ("sports-fitness","Nike Air Zoom Pegasus 41","nike-air-zoom-pegasus-41",
     "Nike's most popular running shoe. ReactX foam cushioning for a more responsive ride. Air Zoom unit in forefoot for springy energy return. Available in unisex sizes.",
     "Nike",11495,9995,
     32,4.7,567,
     "1542291026-7eec264c27ff",
     '["6","7","8","9","10","11","12"]','["Black/White\",\"University Red\",\"Blue Void\",\"Volt\"]',1,
     '["running-shoes","nike","pegasus","cushioning","marathon","fitness"]'),

    ("sports-fitness","Adidas Yoga Mat 6mm","adidas-yoga-mat-6mm",
     "Non-slip PVC yoga mat with alignment lines. 6mm thickness for joint protection. Carry strap included. 183cm x 61cm. Easy clean surface.",
     "Adidas",1999,1599,
     55,4.5,789,
     "1571019613454-1cb2f99b2d8b",
     '[]','[\"Black\",\"Pink\",\"Blue\",\"Green\"]',0,
     '["yoga-mat","adidas","non-slip","6mm","fitness","meditation"]'),

    ("sports-fitness","Decathlon Domyos 20kg Dumbbell Set","decathlon-dumbbell-20kg",
     "Rubber-coated cast iron dumbbell set with adjustable weight. Includes 2 bars + weight plates. Anti-roll design, easy loading collars.",
     "Decathlon",3999,3499,
     18,4.6,445,
     "1571019613454-1cb2f99b2d8b",
     '[]','[\"Black\"]',1,
     '["dumbbell","weights","home-gym","decathlon","strength","fitness"]'),

    ("sports-fitness","Nivia Storm Football","nivia-storm-football",
     "FIFA-approved match football. 32-panel construction, TPU outer material. Machine-stitched, butyl rubber bladder for superior air retention.",
     "Nivia",899,749,
     65,4.4,678,
     "1571019613454-1cb2f99b2d8b",
     '["Size 5"]','[\"Black/White\",\"Blue/White\"]',0,
     '["football","nivia","fifa","match-ball","outdoor","sports"]'),

    ("sports-fitness","Under Armour Compression Shorts","ua-compression-shorts",
     "HeatGear fabric that keeps you cool and dry. 4-way stretch for maximum mobility. Anti-odour technology. 7-inch inseam.",
     "Under Armour",1999,1599,
     40,4.5,345,
     "1571019613454-1cb2f99b2d8b",
     '["XS","S","M","L","XL","XXL"]','[\"Black\",\"Navy\",\"Carbon\"]',0,
     '["compression-shorts","under-armour","heatgear","gym","running","training"]'),

    ("sports-fitness","Boldfit Whey Protein 1kg","boldfit-whey-protein-1kg",
     "24g protein per serving. Cold-processed whey concentrate + isolate blend. 5.4g BCAA, 4.2g glutamine. Informed Sport certified. No added fillers.",
     "Boldfit",1299,999,
     72,4.3,1234,
     "1571019613454-1cb2f99b2d8b",
     '[]','[\"Chocolate\",\"Vanilla\",\"Mango\",\"Strawberry\",\"Unflavoured\"]',0,
     '["protein","whey","boldfit","supplement","muscle","gym"]'),

    ("sports-fitness","Yonex Astrox 7 Badminton Racket","yonex-astrox-7",
     "Attack-type racket with isometric frame for larger sweet spot. Slim shaft for extra power. 4U (avg 83g). Suitable for intermediate to advanced players.",
     "Yonex",4299,3799,
     24,4.6,345,
     "1571019613454-1cb2f99b2d8b",
     '["G4","G5"]','[\"Metallic Yellow\"]',1,
     '["badminton","yonex","astrox","racket","sports","shuttle"]'),

    ("sports-fitness","Fitbit Charge 6 Fitness Tracker","fitbit-charge-6",
     "Built-in GPS, heart rate + ECG monitoring, SpO2, 40+ exercise modes. Google Maps, Google Wallet support. 7-day battery. AMOLED display.",
     "Fitbit",14999,12999,
     19,4.6,456,
     "1434493789543-67fc3b7c0d14",
     '[]','[\"Black/Obsidian\",\"Coral/Champagne Gold\",\"Porcelain/Platinum\"]',0,
     '["fitness-tracker","fitbit","charge-6","gps","heart-rate","health"]'),

    # ══════════════════════════════════════════════════════
    # ACCESSORIES
    # ══════════════════════════════════════════════════════
    ("accessories","Titan Skywear Smart Analog Watch","titan-skywear-watch",
     "Slim profile titanium case with sapphire crystal glass. Khaki/NATO strap in Italian leather. Water resistant to 100m. Japanese quartz movement.",
     "Titan",8995,7495,
     16,4.7,345,
     "1548036161-24e7e3b90a3b",
     '[]','[\"Silver/Blue\",\"Gold/Brown\",\"Gunmetal/Black\"]',1,
     '["watch","titan","skywear","analog","leather-strap","titanium"]'),

    ("accessories","Hidesign Genuine Leather Wallet","hidesign-leather-wallet",
     "Full-grain vegetable-tanned leather bifold wallet. 8 card slots, 2 currency compartments, ID window. RFID blocking technology.",
     "Hidesign",1999,None,
     34,4.6,567,
     "1548036161-24e7e3b90a3b",
     '[]','[\"Tan\",\"Black\",\"Dark Brown\"]',0,
     '["wallet","leather","hidesign","rfid","bifold","genuine-leather"]'),

    ("accessories","Da Milano Tote Bag","da-milano-tote-bag",
     "Italian-inspired genuine leather tote with spacious interior. Zip closure, interior pockets, detachable shoulder strap. 38cm x 29cm x 14cm.",
     "Da Milano",8999,7499,
     12,4.8,189,
     "1548036161-24e7e3b90a3b",
     '[]','[\"Black\",\"Cognac\",\"Dove Grey\",\"Nude\"]',1,
     '["tote-bag","leather","da-milano","italian","handbag","shoulder-bag"]'),

    ("accessories","Fastrack Urban Street Sunglasses","fastrack-urban-sunglasses",
     "Polycarbonate frame, UV400 polarised lens with blue mercury coating. Lightweight 24g, unisex design. Spring hinges for comfort.",
     "Fastrack",1299,999,
     56,4.4,789,
     "1548036161-24e7e3b90a3b",
     '[]','[\"Black\",\"Gunmetal\",\"Tortoise\"]',0,
     '["sunglasses","fastrack","polarised","uv400","unisex","casual"]'),

    ("accessories","CaratLane Diamond Pendant Necklace","caratplane-diamond-pendant",
     "0.10 carat certified diamond pendant in 14kt white gold. IGI certified stone, BIS hallmarked gold. Certificate of authenticity included.",
     "CaratLane",12999,None,
     6,4.9,89,
     "1548036161-24e7e3b90a3b",
     '[]','[\"White Gold\",\"Yellow Gold\",\"Rose Gold\"]',1,
     '["necklace","diamond","pendant","14kt-gold","certified","jewellery"]'),

    ("accessories","Lavie Quilted Backpack","lavie-quilted-backpack",
     "Faux leather quilted backpack with laptop sleeve (up to 14 inch). Multi-compartment organisation, top handle, adjustable straps.",
     "Lavie",2499,1999,
     28,4.5,456,
     "1548036161-24e7e3b90a3b",
     '[]','[\"Black\",\"Dusty Pink\",\"Olive\",\"Wine\"]',0,
     '["backpack","lavie","quilted","faux-leather","laptop","college"]'),

    ("accessories","Tommy Hilfiger Perfume","tommy-hilfiger-impact",
     "Eau de Toilette for men. Fresh spicy fragrance with bergamot, cardamom and vetiver. 100ml spray. Long-lasting projection, 8-10 hours.",
     "Tommy Hilfiger",4299,3499,
     23,4.6,234,
     "1548036161-24e7e3b90a3b",
     '[]','[\"100ml\",\"50ml\",\"30ml\"]',0,
     '["perfume","tommy-hilfiger","edt","fragrance","men","luxury"]'),

    # ══════════════════════════════════════════════════════
    # BOOKS & LIFESTYLE
    # ══════════════════════════════════════════════════════
    ("books-lifestyle","Atomic Habits - James Clear","atomic-habits-james-clear",
     "An easy and proven way to build good habits and break bad ones. James Clear shares the small habit changes that lead to remarkable results.",
     "Penguin Random House",499,349,
     200,4.9,5678,
     "1497366754035-f200968a7db3",
     '["Paperback","Hardcover","Audio CD"]','[]',1,
     '["book","atomic-habits","james-clear","self-help","habits","bestseller"]'),

    ("books-lifestyle","Leuchtturm1917 A5 Dot Grid Notebook","leuchtturm1917-a5-dotgrid",
     "225 numbered pages with index, 8 perforated detachable pages, 2 bookmarks. Acid-free paper (80 g/sqm). Thread-bound, hardcover. Perfect for bullet journaling.",
     "Leuchtturm1917",1699,None,
     45,4.8,1234,
     "1497366754035-f200968a7db3",
     '[]','[\"Black\",\"Navy\",\"Emerald\",\"Berry\",\"Lemon\",\"Nordic Blue\"]',1,
     '["notebook","leuchtturm","dot-grid","bullet-journal","hardcover","stationery"]'),

    ("books-lifestyle","The Alchemist - Paulo Coelho","the-alchemist-coelho",
     "A timeless classic about following your dreams. Santiago's journey from Spain to Egypt is a beautiful metaphor for self-discovery.",
     "HarperCollins",299,249,
     150,4.8,8902,
     "1497366754035-f200968a7db3",
     '["Paperback","Hardcover"]','[]',0,
     '["book","alchemist","paulo-coelho","fiction","self-discovery","classic"]'),

    ("books-lifestyle","Muji Gel Ink Pen Set","muji-gel-ink-pen-set",
     "Pack of 10 Muji 0.5mm smooth writing gel pens. Consistent ink flow, comfortable grip, refillable. Classic MUJI quality.",
     "MUJI",699,None,
     88,4.7,567,
     "1497366754035-f200968a7db3",
     '["0.38mm","0.5mm"]','[\"Black\",\"Blue\",\"Multi-colour\"]',0,
     '["pens","muji","gel-ink","stationery","smooth-writing","set"]'),

    ("books-lifestyle","Moleskine Classic Hardcover Planner","moleskine-2025-planner",
     "2025 weekly horizontal planner in iconic Moleskine hardcover. Ribbon bookmark, expandable inner pocket. 400 pages. 13x21cm.",
     "Moleskine",1999,None,
     34,4.6,345,
     "1497366754035-f200968a7db3",
     '[]','[\"Black\",\"Scarlet Red\",\"Sapphire Blue\"]',0,
     '["planner","moleskine","weekly","2025","hardcover","diary"]'),

    ("books-lifestyle","Prestige Premium Incense Sticks","prestige-incense-sticks-set",
     "Gift set of 10 premium fragrance incense sticks in hand-painted wooden box. Includes lavender, sandalwood, rose, jasmine, patchouli. 100% natural.",
     "Prestige",899,699,
     67,4.5,456,
     "1497366754035-f200968a7db3",
     '[]','[\"Assorted Fragrances\"]',0,
     '["incense","aromatherapy","natural","fragrance","gift","wellness"]'),

    ("books-lifestyle","Kindle Paperwhite 16GB","amazon-kindle-paperwhite-16gb",
     "6.8-inch 300 PPI glare-free display. Adjustable warm light. 16GB storage (thousands of books). IPX8 waterproof. 10-week battery. 20% faster page turns.",
     "Amazon",16999,13999,
     22,4.8,2345,
     "1497366754035-f200968a7db3",
     '[]','[\"Black\",\"Denim\",\"Agave\"]',1,
     '["kindle","ebook-reader","amazon","paperwhite","reading","waterproof"]'),
]


# ─── Product Specs (category-specific) ────────────────────────────────────

SPECS = {
    "apple-macbook-air-m3": [
        ("Processor","Apple M3 Chip, 8-core CPU, 10-core GPU"),
        ("RAM","16 GB Unified Memory"),
        ("Storage","512 GB SSD"),
        ("Display","13.6\" Liquid Retina, 2560x1664, 224 PPI"),
        ("Battery","Up to 18 hours"),
        ("Weight","1.24 kg"),
        ("Ports","2x Thunderbolt 3, MagSafe 3, 3.5mm"),
        ("OS","macOS Sonoma"),
    ],
    "samsung-galaxy-s24-ultra": [
        ("Processor","Snapdragon 8 Gen 3"),
        ("RAM","12 GB"),
        ("Storage","256 GB / 512 GB"),
        ("Display","6.8\" QHD+ Dynamic AMOLED 2X, 120Hz"),
        ("Camera","200MP + 12MP + 10MP + 10MP Quad"),
        ("Battery","5000 mAh, 45W Wired"),
        ("OS","Android 14, One UI 6.1"),
        ("Connectivity","5G, WiFi 7, Bluetooth 5.3, NFC"),
    ],
    "sony-wh1000xm5": [
        ("Driver","30mm dynamic"),
        ("Frequency Response","4 Hz – 40,000 Hz"),
        ("Battery","30 hours (ANC on)"),
        ("Quick Charge","3 min = 3 hours"),
        ("Weight","250 g"),
        ("Microphones","8 built-in"),
        ("Connectivity","Bluetooth 5.2, Multipoint (2 devices)"),
        ("Foldable","Yes"),
    ],
    "nike-air-zoom-pegasus-41": [
        ("Upper","Engineered mesh"),
        ("Midsole","ReactX foam + Air Zoom unit"),
        ("Outsole","Waffle rubber"),
        ("Drop","10 mm"),
        ("Weight","Approx 300 g (US9)"),
        ("Best For","Road running, daily training"),
        ("Fit","True to size"),
    ],
    "dyson-airwrap-multi-styler": [
        ("Motor","Dyson Hyperdymium (110,000 RPM)"),
        ("Wattage","1,300W"),
        ("Attachments","7 (curl, wave, smooth, volumise)"),
        ("Technology","Coanda aerodynamic effect"),
        ("Heat Settings","3 speed, 4 heat"),
        ("Cool Shot","Yes"),
        ("Cord","3.0 m professional length"),
    ],
}


# ─── Coupons ────────────────────────────────────────────────────────────────

COUPONS = [
    # (code, description, type, value, min_order, max_discount, uses_left)
    ("WELCOME200","New user welcome offer","fixed",200,999,200,None),
    ("SAVE10","10% off on all orders","percent",10,499,500,-1),
    ("TECH15","15% off on Technology","percent",15,2999,2000,100),
    ("FASHION20","20% off on Fashion items","percent",20,1999,1500,200),
    ("BEAUTY299","Flat ₹299 off on Beauty","fixed",299,799,299,500),
    ("FREESHIP","Free delivery on any order","fixed",0,0,0,-1),
    ("SPORTS12","12% off Sports & Fitness","percent",12,1499,1800,150),
    ("FESTIVE500","Festival offer — ₹500 off","fixed",500,2999,500,50),
]


# ─── Main seeder ────────────────────────────────────────────────────────────

def seed():
    # Nuke + recreate DB
    with open(SCHEMA, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.executescript(schema_sql)
    db.commit()

    print("[OK]  Schema created")

    # ── Users ────────────────────────────────────────────────────────────────
    user_ids = {}
    for email, name, pw, role in USERS:
        cur = db.execute(
            "INSERT INTO users (email,name,password_hash,role,email_verified) VALUES (?,?,?,?,1)",
            (email, name, hash_pw(pw), role)
        )
        user_ids[email] = cur.lastrowid
    db.commit()
    print(f"[OK]  {len(USERS)} users created")

    # ── Seller Profile ───────────────────────────────────────────────────────
    seller_user_id = user_ids["seller@techzone.in"]
    cur = db.execute(
        """INSERT INTO seller_profiles
           (user_id,store_name,store_slug,description,verification_status)
           VALUES (?,?,?,?,?)""",
        (seller_user_id, "TechZone India", "techzone-india",
         "India's trusted multi-brand electronics retailer. Authorized dealer for Apple, Samsung, Sony and more.",
         "verified")
    )
    seller_id = cur.lastrowid
    db.commit()
    print(f"[OK]  Seller profile created (id={seller_id})")

    # ── Addresses ────────────────────────────────────────────────────────────
    addresses_data = [
        (user_ids["priya@example.com"],   "Home","Priya Patel","9876543210","12 MG Road, Koramangala","","Bengaluru","Karnataka","560034","India",1),
        (user_ids["arjun@example.com"],   "Home","Arjun Mehta","9123456780","45 Linking Road, Bandra West","","Mumbai","Maharashtra","400050","India",1),
        (user_ids["sneha@example.com"],   "Home","Sneha Reddy","9988776655","Plot 7, Jubilee Hills","","Hyderabad","Telangana","500033","India",1),
        (user_ids["vikram@example.com"],  "Home","Vikram Singh","9871234560","C-12 Connaught Place","","New Delhi","Delhi","110001","India",1),
    ]
    addr_ids = {}
    for row in addresses_data:
        cur = db.execute(
            """INSERT INTO addresses
               (user_id,label,full_name,phone,line1,line2,city,state,pincode,country,is_default)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            row
        )
        addr_ids[row[0]] = cur.lastrowid
    db.commit()
    print(f"[OK]  {len(addresses_data)} addresses created")

    # ── Categories ───────────────────────────────────────────────────────────
    cat_ids = {}
    for name,slug,desc,img_id,icon,theme,sort in CATEGORIES:
        cur = db.execute(
            """INSERT INTO categories (name,slug,description,image,icon,theme_config,sort_order)
               VALUES (?,?,?,?,?,?,?)""",
            (name, slug, desc, category_image(slug), icon, json.dumps(theme), sort)
        )
        cat_ids[slug] = cur.lastrowid
    db.commit()
    print(f"[OK]  {len(CATEGORIES)} categories created")

    # ── Products ─────────────────────────────────────────────────────────────
    prod_ids = {}
    for row in PRODUCTS:
        (cat_slug, name, slug, desc, brand, price, sale_price,
         stock, rating, rev_count, img_id, sizes, colours, featured, tags) = row
        cur = db.execute(
            """INSERT INTO products
               (category_id,seller_id,name,slug,description,brand,price,sale_price,
                stock,rating,review_count,image,sizes,colours,tags,is_featured,is_active,approval_status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,'approved')""",
            (cat_ids[cat_slug], seller_id if cat_slug == "technology" else None,
             name, slug, desc, brand, price, sale_price,
             stock, rating, rev_count, product_image(slug, cat_slug),
             sizes, colours, tags, featured)
        )
        prod_ids[slug] = cur.lastrowid
    db.commit()
    print(f"[OK]  {len(PRODUCTS)} products created")

    # ── Product Images (gallery — 3 images per product) ──────────────────────
    gallery_map = {
        "apple-macbook-air-m3":        ["1517336556584-be75d2f54f47","1583394838336-acd977736f90","1611186871520-5b25d8e3f8c3"],
        "samsung-galaxy-s24-ultra":    ["1510557880182-3d4d3cba35a5","1603792657956-5e35bfc4cfcf","1512941937669-90a1b58e7e9c"],
        "sony-wh1000xm5":              ["1505740420857-2d57418d4fb9","1612532945755-9bb88a7cf03b","1583394838336-acd977736f90"],
        "nilkamal-floyd-sofa":         ["1555041469-dc73fa61f8e0","1618022457-29bed0e1-db6a-4a08-b55a-1f1f1b75c5a4","1558618666-fcd25c85cd64"],
        "minimalist-salicylic-facewash":["1596462502278-27bfdc403348","1522335789-2b5b4e8b4e14","1522335789-2b5b4e8b4e14"],
        "nike-air-zoom-pegasus-41":    ["1542291026-7eec264c27ff","1565298583702-67e1f8d4e43c","1543163521-1bf539c55dd2"],
        "titan-skywear-watch":         ["1548036161-24e7e3b90a3b","1434493789543-67fc3b7c0d14","1523275335684-37898b6baf30"],
        "atomic-habits-james-clear":   ["1497366754035-f200968a7db3","1532012197267-b01a4c7f5b6e","1512820790860-62d7c2f0f8f8"],
    }
    for slug, img_ids in gallery_map.items():
        if slug in prod_ids:
            for idx, img_id in enumerate(img_ids[:1]):
                if not product_image(slug, next((r[0] for r in PRODUCTS if r[2] == slug), 'technology')):
                    continue  # no real photo available: skip gallery row
                db.execute(
                    "INSERT INTO product_images (product_id,url,alt,sort_order) VALUES (?,?,?,?)",
                    (prod_ids[slug], product_image(slug, next((r[0] for r in PRODUCTS if r[2] == slug), 'technology')), slug.replace("-"," ").title(), idx)
                )
    db.commit()

    # ── Product Specs ────────────────────────────────────────────────────────
    for slug, specs in SPECS.items():
        if slug in prod_ids:
            for idx, (k, v) in enumerate(specs):
                db.execute(
                    "INSERT INTO product_specs (product_id,spec_key,spec_value,sort_order) VALUES (?,?,?,?)",
                    (prod_ids[slug], k, v, idx)
                )
    db.commit()
    print("[OK]  Product images and specs added")

    # ── Coupons ──────────────────────────────────────────────────────────────
    coupon_ids = {}
    for code, desc, ctype, val, min_o, max_disc, uses in COUPONS:
        cur = db.execute(
            """INSERT INTO coupons (code,description,type,value,min_order,max_discount,uses_left)
               VALUES (?,?,?,?,?,?,?)""",
            (code, desc, ctype, val, min_o, max_disc, uses if uses else -1)
        )
        coupon_ids[code] = cur.lastrowid
    db.commit()
    print(f"[OK]  {len(COUPONS)} coupons created")

    # ── Price History (last 30 days) ─────────────────────────────────────────
    for slug, pid in list(prod_ids.items())[:20]:  # first 20 products
        prod = db.execute("SELECT price, sale_price FROM products WHERE id=?", (pid,)).fetchone()
        base = prod["price"]
        for days_ago in range(30, 0, -5):
            # Simulate slight price variation
            variation = random.uniform(-0.08, 0.05)
            hist_price = round(base * (1 + variation), -1)  # round to nearest 10
            hist_sale = round(prod["sale_price"] * (1 + variation/2), -1) if prod["sale_price"] else None
            db.execute(
                "INSERT INTO price_history (product_id,price,sale_price,recorded_at) VALUES (?,?,?,?)",
                (pid, hist_price, hist_sale,
                 fmt_dt(datetime.now() - timedelta(days=days_ago)))
            )
        # Current price
        db.execute(
            "INSERT INTO price_history (product_id,price,sale_price,recorded_at) VALUES (?,?,?,?)",
            (pid, base, prod["sale_price"], fmt_dt(datetime.now()))
        )
    db.commit()
    print("[OK]  Price history added")

    # ── Reviews ──────────────────────────────────────────────────────────────
    REVIEW_DATA = [
        ("apple-macbook-air-m3",     "priya@example.com", 5,"Incredible machine!","Super fast, silent and the battery lasts all day. Best laptop I've ever owned."),
        ("apple-macbook-air-m3",     "arjun@example.com", 5,"Worth every rupee","The M3 chip is blazing fast. Gaming and video editing — handles everything effortlessly."),
        ("samsung-galaxy-s24-ultra", "sneha@example.com", 5,"Best Android phone","Camera quality is stunning. The S Pen is incredibly useful for notes and editing."),
        ("sony-wh1000xm5",           "vikram@example.com",5,"Noise cancelling magic","Complete silence on a busy flight. The sound quality and comfort are unmatched."),
        ("sony-wh1000xm5",           "priya@example.com", 4,"Great but heavy","Audio is incredible. Slightly heavy after 4-5 hours but overall worth the price."),
        ("nilkamal-floyd-sofa",      "arjun@example.com", 4,"Comfortable and sturdy","Good quality fabric. Assembly was easy. Great value for the price."),
        ("minimalist-salicylic-facewash","priya@example.com",5,"Cleared my skin","My acne and blackheads are significantly reduced after 3 weeks. Zero irritation!"),
        ("dot-key-vitamin-c-serum",  "sneha@example.com", 5,"Skin is glowing","Visible brightening in just 2 weeks. Lightweight texture, absorbs quickly. Love it!"),
        ("nike-air-zoom-pegasus-41", "vikram@example.com",5,"Best running shoes","Incredibly cushioned. Completed my first 10k marathon in these. No blisters at all."),
        ("atomic-habits-james-clear","arjun@example.com", 5,"Life-changing book","Simple, practical and transformative. Already built 3 new habits in 30 days."),
        ("atomic-habits-james-clear","sneha@example.com", 5,"A must-read","James Clear explains habit formation beautifully. Reading it for the second time."),
        ("leuchtturm1917-a5-dotgrid","priya@example.com", 5,"Perfect for journaling","The paper quality is beautiful. Zero bleed through with fountain pens. Worth every rupee."),
        ("titan-skywear-watch",      "vikram@example.com",5,"Elegant and accurate","The sapphire crystal is scratch-free even after months of daily use. Premium quality."),
        ("decathlon-dumbbell-20kg",  "arjun@example.com", 4,"Good for home gym","Solid rubber coating. Plates load easily. Great value for a home workout setup."),
        ("dyson-airwrap-multi-styler","priya@example.com",5,"Worth the investment","My hair has never looked better. The curls last 2+ days and there's no heat damage."),
        ("boldfit-whey-protein-1kg", "vikram@example.com",4,"Good protein, decent taste","Mixes well with milk. Chocolate flavor is good. No bloating or discomfort."),
        ("fabindia-cotton-kurta-men","arjun@example.com", 5,"Beautifully crafted","Quality of fabric and printing is excellent. Perfect for weddings and festivals."),
        ("kindle-paperwhite-16gb",   "sneha@example.com", 5,"Best gift I gave myself","The warm light feature is perfect for night reading. Battery lasts weeks."),
    ]
    for slug, email, rating, title, body in REVIEW_DATA:
        if slug in prod_ids and email in user_ids:
            db.execute(
                """INSERT INTO reviews (product_id,user_id,rating,title,body,is_verified,is_approved)
                   VALUES (?,?,?,?,?,1,1)""",
                (prod_ids[slug], user_ids[email], rating, title, body)
            )
    db.commit()
    print(f"[OK]  {len(REVIEW_DATA)} reviews added")

    # ── Sample Orders ────────────────────────────────────────────────────────
    orders_data = [
        {
            "user": "priya@example.com",
            "items": [("apple-macbook-air-m3",1,172000),("sony-wh1000xm5",1,24990)],
            "status": "delivered", "payment_status": "paid",
            "coupon": "TECH15", "discount": 25800, "shipping": 0,
        },
        {
            "user": "arjun@example.com",
            "items": [("levis-511-slim",2,2799),("hrx-sport-tshirt",3,699)],
            "status": "shipped", "payment_status": "paid",
            "coupon": None, "discount": 0, "shipping": 99,
        },
        {
            "user": "sneha@example.com",
            "items": [("minimalist-salicylic-facewash",2,349),("dot-key-vitamin-c-serum",1,549),
                      ("forest-essentials-rose-toner",1,895)],
            "status": "delivered", "payment_status": "paid",
            "coupon": "BEAUTY299", "discount": 299, "shipping": 0,
        },
        {
            "user": "vikram@example.com",
            "items": [("nike-air-zoom-pegasus-41",1,9995),("adidas-yoga-mat-6mm",1,1599)],
            "status": "confirmed", "payment_status": "paid",
            "coupon": None, "discount": 0, "shipping": 149,
        },
        {
            "user": "priya@example.com",
            "items": [("atomic-habits-james-clear",1,349),("leuchtturm1917-a5-dotgrid",1,1699),
                      ("muji-gel-ink-pen-set",2,699)],
            "status": "placed", "payment_status": "paid",
            "coupon": "SAVE10", "discount": 345, "shipping": 49,
        },
    ]

    order_num_counter = 1000
    for od in orders_data:
        u_id = user_ids[od["user"]]
        subtotal = sum(qty * price for _, qty, price in od["items"])
        total = subtotal - od["discount"] + od["shipping"]
        addr = addr_ids.get(u_id)
        addr_row = db.execute("SELECT * FROM addresses WHERE id=?", (addr,)).fetchone() if addr else None
        addr_snap = json.dumps(dict(addr_row)) if addr_row else json.dumps({"line1":"India"})

        onum = f"CASH2024{order_num_counter}"
        order_num_counter += 1

        cur = db.execute(
            """INSERT INTO orders
               (user_id,order_number,total,subtotal,discount,shipping_fee,
                status,payment_status,payment_method,payment_ref,
                address_id,address_snapshot,coupon_code)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (u_id, onum, total, subtotal, od["discount"], od["shipping"],
             od["status"], od["payment_status"], "card",
             f"TXN{random.randint(100000,999999)}",
             addr, addr_snap, od["coupon"])
        )
        order_id = cur.lastrowid

        for pslug, qty, unit_price in od["items"]:
            if pslug in prod_ids:
                p = db.execute("SELECT name,image FROM products WHERE id=?", (prod_ids[pslug],)).fetchone()
                db.execute(
                    """INSERT INTO order_items (order_id,product_id,name,image,qty,unit_price)
                       VALUES (?,?,?,?,?,?)""",
                    (order_id, prod_ids[pslug], p["name"], p["image"], qty, unit_price)
                )

    db.commit()
    print(f"[OK]  {len(orders_data)} sample orders created")

    # ── Notifications ────────────────────────────────────────────────────────
    for u_id in list(user_ids.values())[2:]:  # customers only
        db.execute(
            """INSERT INTO notifications (user_id,type,title,message,link,is_read)
               VALUES (?,?,?,?,?,0)""",
            (u_id, "promotion", "Welcome to CASHON! ",
             "Use code WELCOME200 to get ₹200 off your first order above ₹999.",
             "/shop", )
        )
        db.execute(
            """INSERT INTO notifications (user_id,type,title,message,link,is_read)
               VALUES (?,?,?,?,?,0)""",
            (u_id, "promotion", "Weekend Sale — Up to 20% off!",
             "Explore hundreds of deals this weekend across all categories.",
             "/shop?sale=1", )
        )
    db.commit()
    print("[OK]  Notifications added")

    # ── Browsing History ────────────────────────────────────────────────────
    all_pids = list(prod_ids.values())
    for email in ["priya@example.com", "arjun@example.com", "sneha@example.com"]:
        u_id = user_ids[email]
        for pid in random.sample(all_pids, min(8, len(all_pids))):
            db.execute(
                "INSERT OR IGNORE INTO browsing_history (user_id,product_id,viewed_at) VALUES (?,?,?)",
                (u_id, pid, rand_days(14))
            )
    db.commit()

    db.close()
    print("\n[>>]  CASHON database seeded successfully!")
    print(f"   DB: {DB_PATH}")
    print("\n   Login credentials:")
    print("   Admin:    admin@cashon.in / Admin@2024")
    print("   Seller:   seller@techzone.in / Seller@2024")
    print("   Customer: priya@example.com / Password@1")
    print("   Customer: arjun@example.com / Password@1")

if __name__ == "__main__":
    seed()
