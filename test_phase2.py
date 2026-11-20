from app import create_app
app = create_app()
tests = [
    ("/", 200, "Homepage"),
    ("/shop", 200, "Shop listing"),
    ("/shop?category=womens-fashion", 200, "Category filter"),
    ("/shop?sale=1", 200, "Sale filter"),
    ("/shop?sort=popular", 200, "Sort popular"),
    ("/product/linen-summer-dress", 200, "Product detail"),
    ("/product/vitamin-c-glow-serum", 200, "Product detail 2"),
    ("/product/nonexistent", 404, "404 page"),
    ("/api/search?q=dress", 200, "Search API"),
    ("/api/cart/count", 200, "Cart count API"),
    ("/about", 200, "About"),
    ("/faq", 200, "FAQ"),
    ("/contact", 200, "Contact"),
    ("/account/login", 200, "Login"),
]
all_ok = True
with app.test_client() as c:
    for route, expected, label in tests:
        r = c.get(route)
        ok = r.status_code == expected
        if not ok:
            all_ok = False
        status = "OK" if ok else "FAIL"
        print(status + "  " + str(r.status_code) + "  " + label)
print("")
print("Phase 2 ALL PASS" if all_ok else "Some routes FAILED")
