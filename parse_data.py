import re
import sqlite3

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


def extract_news(soup_article):
    date, article_content = (
        soup_article.find("div", {"id": "nContent"}).find("p").children
    )
    # берём часть текста до перечисления трудных слов
    article_text = article_content.text.split("Difficult words:")[0].strip()
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


def create_textinlevels_table(conn, cur, table_name):
    cur.execute(
        f"""CREATE TABLE {table_name} (date date, heading text, article_text text, level int,
        UNIQUE(date, article_text) ON CONFLICT REPLACE)"""
    )
    conn.commit()


def parse_data(kind_of_data, extract_function, conn, cur, headers):
    data = []

    for level in range(1, 4):  # проходим по номерам уровней
        url_page = f"https://www.{kind_of_data}.com/level/level-{level}/"
        page = requests.get(url_page, headers=headers)
        soup_page = BeautifulSoup(page.text, "html.parser")

        pagination = soup_page.find("ul", {"class": "pagination"})
        last_article_link = pagination.find_all(href=True)[-1].get("href")
        # определим номер самой последней страницы, содержащей тексты этого уровня
        last_page_num = int(re.findall("(?<=/page/)\d+(?=/)", last_article_link)[0])

        # проходим по номерам страниц для каждого уровня
        for page_num in tqdm(range(1, last_page_num + 1)):
            url_page = (
                f"https://www.{kind_of_data}.com/level/level-{level}/page/{page_num}/"
            )
            page = requests.get(url_page, headers=headers)
            soup_page = BeautifulSoup(page.text, "html.parser")
            blocks_with_links = soup_page.find_all("div", {"class": "title"})

            # собираем заголовки статей с этой страницы
            # заголовок имеет вид "заголовок - level <номер уровня>"
            # используем split по тире и берём нулевой элемент, чтобы убрать упоминание уровня
            headings_page = tuple(
                (
                    re.split("[–-] level \d", block.text)[0].strip()
                    for block in blocks_with_links
                )
            )
            links = tuple((block.find("a").get("href") for block in blocks_with_links))

            # проходим по ссылкам на статьи, которые даны на этой странице
            for i, link in enumerate(links):
                article = requests.get(link, headers=headers)
                soup_article = BeautifulSoup(article.text, "html.parser")
                date, article_text = extract_function(soup_article)
                data.append((date, headings_page[i], article_text, level))

        cur.executemany(f"""INSERT INTO {kind_of_data} VALUES(?,?,?,?)""", data)
        conn.commit()


if __name__ == "__main__":
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36"
    }
    conn = sqlite3.connect("english_levels.db")
    cur = conn.cursor()
    create_textinlevels_table(conn, cur, "newsinlevels")
    parse_data("newsinlevels", extract_news, conn, cur, headers)
    create_textinlevels_table(conn, cur, "daysinlevels")
    parse_data("daysinlevels", extract_days, conn, cur, headers)
    conn.close()
