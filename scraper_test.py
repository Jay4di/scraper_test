import streamlit as st
import json
import time
import urllib.parse
from urllib.parse import urlparse
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import locale
import random
from streamlit_option_menu import option_menu




# Optional: Selenium only if selected
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# ================================
# FUNCTION ZONE
# ================================

def format_boolean_query(query):
    token_pattern = r'(\bAND\b|\bOR\b|\bNOT\b|\(|\)|"[^"]+"|\S+)'
    tokens = re.findall(token_pattern, query, flags=re.IGNORECASE)

    def parse_tokens(tokens):
        output = []
        i = 0
        while i < len(tokens):
            token = tokens[i].upper()

            if token == "AND":
                i += 1
                continue
            elif token == "OR":
                output.append("OR")
            elif token == "NOT":
                i += 1
                if i < len(tokens):
                    next_token = tokens[i]
                    if next_token.startswith("("):
                        group_tokens = []
                        paren_count = 1
                        i += 1
                        while i < len(tokens) and paren_count > 0:
                            if tokens[i] == "(":
                                paren_count += 1
                            elif tokens[i] == ")":
                                paren_count -= 1
                            if paren_count > 0:
                                group_tokens.append(tokens[i])
                            i += 1
                        group_query = parse_tokens(group_tokens)
                        output.append(f'-({group_query})')
                        i -= 1
                    else:
                        output.append(f'-{next_token}')
            else:
                output.append(tokens[i])
            i += 1
        return " ".join(output)

    return parse_tokens(tokens)


# Set locale (fallback ke C jika id_ID tidak tersedia)
try:
    locale.setlocale(locale.LC_TIME, "id_ID.utf8")
except:
    locale.setlocale(locale.LC_TIME, "C")

def convert_relative_date(text):
    text = text.lower().strip()
    today = datetime.today()
    text = text.replace("yang", "").replace("  ", " ").strip()
    date_obj = None

    if "hari lalu" in text:
        match = re.search(r"(\d+)\s+hari", text)
        if match:
            date_obj = today - timedelta(days=int(match.group(1)))

    elif "jam lalu" in text:
        match = re.search(r"(\d+)\s+jam", text)
        if match:
            date_obj = today - timedelta(hours=int(match.group(1)))

    elif "menit lalu" in text:
        date_obj = today

    elif "kemarin" in text:
        date_obj = today - timedelta(days=1)

    elif "minggu lalu" in text:
        match = re.search(r"(\d+)\s+minggu", text)
        if match:
            date_obj = today - timedelta(weeks=int(match.group(1)))

    elif "bulan lalu" in text:
        match = re.search(r"(\d+)\s+bulan", text)
        if match:
            date_obj = today - timedelta(days=int(match.group(1)) * 30)

    elif "tahun lalu" in text:
        match = re.search(r"(\d+)\s+tahun", text)
        if match:
            date_obj = today - timedelta(days=int(match.group(1)) * 365)

    elif re.match(r"\d{1,2}\s+\w+", text):
        try:
            date_obj = datetime.strptime(text + f" {today.year}", "%d %B %Y")
        except:
            return text

    if date_obj:
        return date_obj.strftime("%d %b %Y").lstrip("0")

    return text

# Fungsi untuk mengekstrak domain dari URL
def extract_domain_from_url(url):
    parsed_url = urlparse(url)
    netloc = parsed_url.netloc
    # Buang www. kalau ada, tapi simpan subdomain lainnya
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc



# Ubah fungsi scrape_with_bs4
def scrape_with_bs4(base_url, headers=None):
    news_results = []
    page = 0

    while True:
        start = page * 10
        url = f"{base_url}&start={start}"
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, "html.parser")
        results_on_page = 0

        for el in soup.select("div.SoaBEf"):
            try:
                news_results.append({
                    "Link": el.find("a")["href"],
                    "Judul": el.select_one("div.MBeuO").get_text(),
                    "Snippet": el.select_one(".GI74Re").get_text(),
                    "Tanggal": convert_relative_date(el.select_one(".LfVVr").get_text()),
                    "Sumber": extract_domain_from_url(el.find("a")["href"])

                })
                results_on_page += 1
            except:
                continue

        if results_on_page == 0:
            break

        page += 1
        time.sleep(random.uniform(1.5, 20.0))  # Waktu tunggu lebih pendek, bisa disesuaikan

    return news_results

# Ubah fungsi scrape_with_selenium
def scrape_with_selenium(base_url):
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    news_results = []
    page = 0

    while True:
        start = page * 10
        url = f"{base_url}&start={start}"
        driver.get(url)
        time.sleep(random.uniform(1.5, 20.0))

        elements = driver.find_elements(By.CSS_SELECTOR, "div.SoaBEf")
        if not elements:
            break

        for el in elements:
            try:
                link = el.find_element(By.TAG_NAME, "a").get_attribute("href")
                title = el.find_element(By.CSS_SELECTOR, "div.MBeuO").text
                snippet = el.find_element(By.CSS_SELECTOR, ".GI74Re").text
                date = convert_relative_date(el.find_element(By.CSS_SELECTOR, ".LfVVr").text)
                source = el.find_element(By.CSS_SELECTOR, ".NUnG9d span").text

                news_results.append({
                    "Link": link,
                    "Judul": title,
                    "Snippet": snippet,
                    "Tanggal": date,
                    "Sumber": extract_domain_from_url(el.find_element(By.TAG_NAME, "a").get_attribute("href"))

                })
            except:
                continue

        page += 1

    driver.quit()
    return news_results


# Ubah get_news_data untuk menghapus max_pages
def get_news_data(method, start_date, end_date, keyword_query):
    headers = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36"
    }

    keyword_query = format_boolean_query(keyword_query)
    if isinstance(end_date, datetime):
        end_date = end_date.date()

    end_date_plus_one = end_date + timedelta(days=1)
    full_query = f"{keyword_query} after:{start_date} before:{end_date_plus_one}"
    encoded_query = urllib.parse.quote(full_query)

    base_url = f"https://www.google.com/search?q={encoded_query}&gl=id&hl=id&lr=lang_id&tbm=nws&num=10"

    if method == "BeautifulSoup":
        return scrape_with_bs4(base_url, headers)
    elif method == "Selenium-only for local use":
        return scrape_with_selenium(base_url)
    else:
        raise ValueError("Invalid method")

# ================================
# STREAMLIT UI
# ================================
st.set_page_config(page_title="Burson News Scraper", layout="centered")
# Sidebar Navigation
with st.sidebar:
    menu = option_menu(
        menu_title = "Main Menu",
        options=["Scrape", "How to use", "About"],
        icons=["house", "filter-circle", "diagram-3"],
        menu_icon="cast",  # optional
        default_index=0,  # optional
        styles={

                "icon": {"color": "orange"},
                "nav-link": {
                    "--hover-color": "#eee",
                },
                "nav-link-selected": {"background-color": "green"},
            },
        )



if menu == "Scrape":
    st.title("📰 Burson News Scraper - v0.0.2")
    st.markdown("Scrape berita berdasarkan **Boolean Keyword** dan input tanggal, lalu simpan ke Excel.")

    with st.form("scrape_form"):
        keyword = st.text_input("Masukkan keyword (gunakan AND, OR, NOT):", value="")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Tanggal mulai")
        with col2:
            end_date = st.date_input("Tanggal akhir")

        method = st.radio("Metode Scraping:", ["BeautifulSoup", "Selenium-only for local use"])
        submitted = st.form_submit_button("Mulai Scrape")

    if submitted:
        with st.spinner("Sedang scraping berita..."):
            results = get_news_data(method, start_date, end_date, keyword)
            df = pd.DataFrame(results)

            if df.empty:
                st.warning("Tidak ada hasil ditemukan.")
            else:
                st.success(f"{len(df)} berita berhasil di-scrape!")
                st.dataframe(df)

                filename = f"hasil_berita_{start_date}_to_{end_date}.xlsx"
                df.to_excel(filename, index=False)

                with open(filename, "rb") as f:
                    st.download_button("📥 Download Excel", f, file_name=filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

elif menu == "How to use":
    st.title("📖 How to Use")
    st.markdown("""
### Petunjuk Penggunaan

1. Masukkan **keyword pencarian** menggunakan format Boolean (misal: `"kebijakan" AND "pemerintah" NOT "ekonomi"`).
2. Pilih **tanggal mulai dan akhir** berita yang ingin diambil.
3. Pilih metode scraping:
   - **BeautifulSoup**: tanpa browser, lebih cepat, tapi tidak bisa render halaman dinamis.
   - **Selenium**: menggunakan browser headless, cocok untuk halaman dinamis.
4. Klik **Mulai Scrape**, tunggu hingga proses selesai.
5. Jika berhasil, hasil scraping bisa langsung diunduh dalam format **Excel**.

Tips:
- Gunakan tanda kutip `"` untuk frase.
- Gunakan `()` untuk mengelompokkan logika query.
""")

elif menu == "About":
    st.title("ℹ️ About")
    st.markdown("""
### Burson News Scraper v0.0.2

**Release Note:**
- ✅ Fix bug error
- ✅ Fix Boolean search error
- ✅ Auto-randomize delay scraping
- ✅ Auto scrape seluruh halaman
- ✅ Fix error pada format tanggal/waktu
- ✅ New side menu

---

**Made by**: Jay ✨
""")
