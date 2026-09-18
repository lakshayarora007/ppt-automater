from app.crawler import _clean_candidates, _normalise_url, _page_type


def test_normalise_url_adds_scheme():
    assert _normalise_url("attrangi.in/") == "https://attrangi.in"


def test_page_type_classifies_storefront_routes():
    assert _page_type("https://shop.test/products/dress") == "pdp"
    assert _page_type("https://shop.test/collections/new") == "collection"
    assert _page_type("https://shop.test/cart") == "cart"


def test_candidate_cleaner_ignores_fragments_accounts_and_external_links():
    links = ["#top", "/collections/new", "/account", "https://other.test/products/a", "/products/a"]
    assert _clean_candidates(links, "https://shop.test", 5) == [
        "https://shop.test/collections/new", "https://shop.test/products/a"
    ]
