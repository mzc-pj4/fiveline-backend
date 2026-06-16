"""
무신사 상품 크롤링 → JSON 저장 (DB 불필요).
사용법: python scripts/crawl_musinsa.py [--out products.json]
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

CATEGORIES = [
    ("상의",         "001", 2000),
    ("하의",         "003", 2000),
    ("아우터",       "002", 1500),
    ("원피스/스커트", "100", 1500),
    ("신발",         "103", 1000),
    ("가방",         "004", 1000),
    ("소품",         "101", 1000),
]


def parse_goods(goods_list: list, category: str) -> list[dict]:
    items = []
    for g in goods_list:
        try:
            name = g.get("goodsName") or g.get("name") or g.get("title") or ""
            brand_raw = g.get("brand") or {}
            brand = (
                g.get("brandName")
                or (brand_raw.get("name") if isinstance(brand_raw, dict) else str(brand_raw))
                or "MUSINSA"
            )
            price = int(g.get("price") or g.get("salePrice") or g.get("finalPrice") or 0)
            normal_price = int(
                g.get("normalPrice") or g.get("originalPrice") or g.get("consumerPrice") or 0
            )
            image_url = (
                g.get("thumbnail") or g.get("imageUrl") or g.get("img") or g.get("image") or ""
            )
            if image_url.startswith("//"):
                image_url = "https:" + image_url
            if image_url.startswith("http://"):
                image_url = image_url.replace("http://", "https://", 1)
            if not name or price == 0 or not image_url:
                continue
            original_price = normal_price if normal_price > price else None
            items.append({
                "name": name,
                "brand": brand,
                "price": price,
                "original_price": original_price,
                "image_url": image_url,
                "category": category,
                "stock_quantity": random.randint(10, 200),
            })
        except Exception:
            continue
    return items


def fetch_category(cat_code: str, target: int, category: str, browser) -> list[dict]:
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1920, "height": 1080},
        locale="ko-KR",
    )
    page = context.new_page()
    captured: list = []

    def on_response(resp):
        if "api2/dp/v2/plp/goods" in resp.url and resp.status == 200:
            try:
                data = resp.json()
                lst = data.get("data", {}).get("list") or data.get("list") or []
                captured.extend(lst)
            except Exception:
                pass

    page.on("response", on_response)

    url = f"https://www.musinsa.com/category/{cat_code}/goods?gf=A"
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
    except Exception as e:
        print(f"  페이지 로드 실패: {e}")
        context.close()
        return []

    prev_count = 0
    no_new_streak = 0

    while len(captured) < target:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1500)

        current_count = len(captured)
        print(f"  스크롤: {current_count}개 수집 중... (목표 {target}개)")

        if current_count == prev_count:
            no_new_streak += 1
            if no_new_streak >= 3:
                print("  더 이상 새 상품 없음. 종료.")
                break
        else:
            no_new_streak = 0

        prev_count = current_count

    context.close()
    items = parse_goods(captured, category)
    print(f"  파싱 완료: {len(items)}개")
    return items[:target]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="products.json")
    args = parser.parse_args()

    all_items: list[dict] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)

        for category, cat_code, target in CATEGORIES:
            print(f"\n[{category}] 수집 중... (목표: {target}개)")
            result = fetch_category(cat_code, target, category, browser)
            all_items.extend(result)
            print(f"  → {len(result)}개 수집 완료")

        browser.close()

    # 이름 기준 중복 제거
    seen: set[str] = set()
    unique_items: list[dict] = []
    for item in all_items:
        key = item["name"].strip().lower()
        if key not in seen:
            seen.add(key)
            unique_items.append(item)

    out_path = Path(args.out)
    out_path.write_text(json.dumps(unique_items, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n수집 {len(all_items)}개 → 중복 제거 후 {len(unique_items)}개")
    print(f"저장 완료: {out_path.resolve()}")
    for cat, _, _ in CATEGORIES:
        cnt = sum(1 for i in unique_items if i["category"] == cat)
        print(f"  {cat}: {cnt}개")


if __name__ == "__main__":
    raise SystemExit(main())
