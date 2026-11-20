import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import sqlite3

url = "https://github.com/orgs/google/repositories"

pending = [url]
visited = set()

data = {}

while pending:
    current_url = pending.pop(0)

    if current_url in visited:
        continue

    time.sleep(1)
    res = requests.get(current_url)
    for retry in range(5):
        if res.status_code != 429:
            break
        print("アクセス制限のため60秒待って再取得します", flush=True)
        time.sleep(60)
        res = requests.get(current_url)

    res.raise_for_status()
    visited.add(current_url)

    html_soup = BeautifulSoup(res.content, "html.parser")

    rows = html_soup.select('li:has(h3 a[href^="/google/"])')

    print(f"{current_url} で{len(rows)}件見つかりました", flush=True)
    for row in rows:
        name_tag = row.select_one('h3 a[href^="/google/"]')
        language_tag = row.select_one('span[class*="PrimaryLanguageName"]')
        stars_tag = row.select_one('a[href$="/stargazers"]')

        name = name_tag.get_text(strip=True)
        language = None
        if language_tag is not None:
            language = language_tag.get_text(strip=True)
        stars = stars_tag.get_text(strip=True)

        data[name] = (name, language, stars)

    next_tag = html_soup.find("a", rel="next", href=True)
    if next_tag is not None:
        next_href = next_tag.get("href")
        if next_href.startswith("#"):
            next_url = url + "?page=" + next_href[1:]
        else:
            next_url = urljoin(current_url, next_href)

        if next_url not in visited:
            pending.append(next_url)

con = sqlite3.connect("repositories.sqlite")
cur = con.cursor()

sql_create = """
CREATE TABLE IF NOT EXISTS repositories (
    name TEXT PRIMARY KEY,
    language TEXT,
    stars TEXT
);
"""
cur.execute(sql_create)

sql_insert_many = "INSERT OR REPLACE INTO repositories VALUES (?, ?, ?);"
cur.executemany(sql_insert_many, data.values())
con.commit()

sql_select = "SELECT name, language, stars FROM repositories;"
res = cur.execute(sql_select)

for row in res:
    print(row[0], row[1], row[2])

con.close()
