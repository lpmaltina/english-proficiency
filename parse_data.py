import re
import sqlite3

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36"
}


class TextinlevelsDB:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(f"{db_name}.db")
        self.cur = self.conn.cursor()

    def create_table(self, table_name):
        self.cur.execute(
            f"""CREATE TABLE {table_name} (date date, heading text, article_text text, level int,
            UNIQUE(article_text) ON CONFLICT IGNORE)"""
        )
        self.conn.commit()

    def fill_table(self, table_name, extract_function):
        for level in range(1, 4):  # проходим по номерам уровней
            soup_page = get_soup(
                link=f"https://www.{table_name}.com/level/level-{level}/"
            )
            pagination = soup_page.find("ul", {"class": "pagination"})
            last_article_link = pagination.find_all(href=True)[-1].get("href")
            # определим номер самой последней страницы, содержащей тексты этого уровня
            last_page_num = int(
                re.findall(r"(?<=/page/)\d+(?=/)", last_article_link)[0]
            )

            # проходим по номерам страниц для каждого уровня
            for page_num in tqdm(range(1, last_page_num + 1)):
                data = []
                soup_page = get_soup(
                    link=f"https://www.{table_name}.com/level/level-{level}/page/{page_num}/"
                )
                blocks_with_links = soup_page.find_all("div", {"class": "title"})

                # собираем заголовки статей с этой страницы
                # заголовок имеет вид "заголовок - level <номер уровня>"
                # убираем из заголовка упоминание уровня
                headings_page = tuple(
                    (
                        re.split(r"[–-] level \d", block.text)[0].strip()
                        for block in blocks_with_links
                    )
                )
                links = tuple(
                    (block.find("a").get("href") for block in blocks_with_links)
                )

                # проходим по ссылкам на статьи, которые даны на этой странице
                for i, link in enumerate(links):
                    soup_article = get_soup(link=link)
                    date, article_text = extract_function(soup_article)
                    data.append((date, headings_page[i], article_text, level))

                self.cur.executemany(
                    f"""INSERT INTO {table_name} VALUES(?,?,?,?)""", data
                )
                self.conn.commit()

    def create_and_fill_table(self, table_name, extract_function):
        self.create_table(table_name)
        self.fill_table(table_name, extract_function)

    def __del__(self):
        self.conn.close()


def get_soup(link):
    response = requests.get(link, headers=HEADERS)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def extract_news(soup_article):
    article_content = soup_article.find("div", {"id": "nContent"})
    article_content_list = []

    for el in article_content.find_all(text=True):
        if el.startswith("Difficult words:"):
            break
        article_content_list.append(el)

    date = article_content_list[0]
    article_text = "".join(article_content_list[1:])
    return date, article_text


def extract_days(soup_article):
    article_content = soup_article.find("div", {"id": "nContent"})
    article_content_list = []

    for el in article_content.find_all(text=True):
        if el.startswith("Difficult words:"):
            break
        article_content_list.append(el)

    article_text = "".join(article_content_list).strip()
    article_text_list = article_text.split("\n")
    date = article_text_list[0]
    article_text = "\n".join(article_text_list[1:])
    return date, article_text


if __name__ == "__main__":
    textsinlevels = TextinlevelsDB(db_name="textsinlevels")
    textsinlevels.create_and_fill_table(
        table_name="daysinlevels", extract_function=extract_days
    )
    textsinlevels.create_and_fill_table(
        table_name="newsinlevels", extract_function=extract_news
    )
    del textsinlevels
