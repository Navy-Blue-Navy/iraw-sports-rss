import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin
import re

URL = "https://iraw.rcc.jp/topics/categories/3"
OUTPUT = Path(__file__).parent / "iraw_sports.xml"

# IRAWのスポーツ一覧を取得
response = requests.get(URL, timeout=30)
response.raise_for_status()
response.encoding = response.apparent_encoding

soup = BeautifulSoup(response.text, "html.parser")

new_items = []
seen_urls = set()

for a in soup.find_all("a", href=True):
    href = a["href"]

    if "/topics/articles/" not in href:
        continue

    article_url = urljoin(URL, href)

    if article_url in seen_urls:
        continue

    full_text = a.get_text(" ", strip=True)

    if not full_text:
        continue

    # 掲載日時を取得
    date_match = re.search(
        r"(\d{4})\.(\d{2})\.(\d{2})\s+(\d{2}):(\d{2})",
        full_text
    )

    if date_match:
        year, month, day, hour, minute = date_match.groups()
        date_text = f"{year}.{month}.{day} {hour}:{minute}"

        # 「スポーツ」以降をタイトルから除去
        title = full_text[:date_match.start()]

        # タイトル末尾のカテゴリ名を除去
        title = re.sub(r"\s+スポーツ(?:\s+高校生スポーツ)?\s*$", "", title)

        pub_date = f"{year}-{month}-{day}T{hour}:{minute}:00+09:00"
    else:
        title = full_text
        date_text = ""
        pub_date = ""

    seen_urls.add(article_url)

    new_items.append({
        "title": title.strip(),
        "link": article_url,
        "description": f"IRAW by RCC スポーツ　{date_text}",
        "date": pub_date,
        "guid": article_url
    })

# 以前のRSSを読み込む
old_items = []

if OUTPUT.exists():
    try:
        old_tree = ET.parse(OUTPUT)
        old_root = old_tree.getroot()

        for item in old_root.findall("./channel/item"):
            old_items.append({
                "title": item.findtext("title", ""),
                "link": item.findtext("link", ""),
                "description": item.findtext("description", ""),
                "date": item.findtext("pubDate", ""),
                "guid": item.findtext("guid", "")
            })
    except Exception:
        old_items = []

# 新着＋過去記事を合体して重複除去
all_items = []
seen = set()

for item in new_items + old_items:
    if item["guid"] in seen:
        continue

    seen.add(item["guid"])
    all_items.append(item)

# 最大300記事保存
all_items = all_items[:300]

# RSS作成
rss = ET.Element("rss", version="2.0")
channel = ET.SubElement(rss, "channel")

ET.SubElement(channel, "title").text = "IRAW by RCC スポーツ"
ET.SubElement(channel, "link").text = URL
ET.SubElement(channel, "description").text = "IRAW by RCC スポーツの記事"
ET.SubElement(channel, "language").text = "ja"

for item in all_items:
    element = ET.SubElement(channel, "item")

    ET.SubElement(element, "title").text = item["title"]
    ET.SubElement(element, "link").text = item["link"]
    ET.SubElement(element, "description").text = item["description"]
    ET.SubElement(element, "pubDate").text = item["date"]

    guid_element = ET.SubElement(element, "guid")
    guid_element.set("isPermaLink", "false")
    guid_element.text = item["guid"]

tree = ET.ElementTree(rss)
ET.indent(tree, space="  ")

tree.write(
    OUTPUT,
    encoding="utf-8",
    xml_declaration=True
)

print("RSS作成成功")
print("今回取得:", len(new_items), "件")
print("RSS保存件数:", len(all_items), "件")
print("保存先:", OUTPUT)

print()
print("最新5件:")
for item in new_items[:5]:
    print(item["date"], item["title"])