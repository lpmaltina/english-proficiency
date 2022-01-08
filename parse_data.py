import re
import sqlite3

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


conn_newsinlevels = sqlite3.connect("english_levels.db")
cursor_newsinlevels = conn_newsinlevels.cursor()
cursor_newsinlevels.execute(
    """CREATE TABLE newsinlevels (publication_date date, heading text, article_text text, level int)"""
)
conn_newsinlevels.commit()


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36"
}

data = []

for level in range(1, 4):  # проходим по номерам уровней
    url_page = f"https://www.newsinlevels.com/level/level-{level}/"
    page = requests.get(url_page, headers=headers)
    soup_page = BeautifulSoup(page.text, "html.parser")

    pagination = soup_page.find("ul", {"class": "pagination"})
    last_article_link = pagination.find_all(href=True)[-1].get("href")
    # определим номер самой последней страницы, содержащей тексты этого уровня
    last_page_num = int(re.findall("(?<=/page/)\d+(?=/)", last_article_link)[0])

    for page_num in tqdm(
        range(1, last_page_num + 1)
    ):  # проходим по номерам страниц для каждого уровня
        url_page = f"https://www.newsinlevels.com/level/level-{level}/page/{page_num}/"
        page = requests.get(url_page, headers=headers)
        soup_page = BeautifulSoup(page.text, "html.parser")
        blocks_with_links = soup_page.find_all("div", {"class": "title"})

        # собираем заголовки статей с этой страницы
        # заголовок имеет вид "заголовок - level <номер уровня>"
        # используем split по тире и берём нулевой элемент, чтобы убрать упоминание уровня
        headings_page = tuple(
            (re.split("[–-]", block.text)[0].strip() for block in blocks_with_links)
        )
        links = tuple((block.find("a").get("href") for block in blocks_with_links))

        for i, link in enumerate(
            links
        ):  # проходим по ссылкам на статьи, которые даны на этой странице
            article = requests.get(link, headers=headers)
            soup_article = BeautifulSoup(article.text, "html.parser")
            date, article_content = (
                soup_article.find("div", {"id": "nContent"}).find("p").children
            )
            # берём часть текста до перечисления трудных слов
            article_text = article_content.text.split("Difficult words:")[0].strip()
            data.append((date, headings_page[i], article_text, level))

    conn_newsinlevels.executemany("""INSERT INTO newsinlevels VALUES(?,?,?,?)""", data)
    conn_newsinlevels.commit()
