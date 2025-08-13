import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import asyncio
import httpx

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GENIUS_API_TOKEN = os.getenv("GENIUS_API_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_BOT_TOKEN or not GENIUS_API_TOKEN or not GROQ_API_KEY:
raise ValueError("Pastikan TELEGRAM_BOT_TOKEN, GENIUS_API_TOKEN, dan GROQ_API_KEY sudah di .env!")

=== Scraper Functions with error handling and timeout ===

def scrape_genius(song_title):
try:
headers = {"Authorization": f"Bearer {GENIUS_API_TOKEN}"}
search_url = "https://api.genius.com/search"
response = requests.get(search_url, headers=headers, params={"q": song_title}, timeout=10)
response.raise_for_status()
hits = response.json().get("response", {}).get("hits", [])
if not hits:
return None

song_data = hits[0]["result"]  
    song_url = song_data["url"]  

    page = requests.get(song_url, timeout=10)  
    soup = BeautifulSoup(page.text, "html.parser")  

    lyrics_divs = soup.find_all("div", {"data-lyrics-container": "true"})  
    lyrics = "\n".join([div.get_text(separator="\n") for div in lyrics_divs]).strip()  

    artist = song_data["primary_artist"]["name"]  
    cover_image = song_data.get("song_art_image_url") or ""  

    album = "-"  
    release_date = "-"  
    label = "-"  
    composer = "-"  
    arranger = "-"  

    return {  
        "source": "Genius",  
        "song_url": song_url,  
        "artist": artist,  
        "song_title": song_title,  
        "album": album,  
        "release_date": release_date,  
        "label": label,  
        "composer": composer,  
        "arranger": arranger,  
        "cover_image": cover_image,  
        "lyrics": lyrics,  
    }  
except Exception as e:  
    print(f"Genius scraping error: {e}")  
    return None

def scrape_azlyrics(song_title):
try:
search_url = f"https://search.azlyrics.com/search.php?q={song_title.replace(' ', '+')}"
res = requests.get(search_url, timeout=10)
res.raise_for_status()
soup = BeautifulSoup(res.text, "html.parser")
table = soup.find("td", class_="text-left visitedlyr")
if not table:
return None

first_link = table.find("a")  
    if not first_link:  
        return None  

    song_url = first_link["href"]  
    song_page = requests.get(song_url, timeout=10)  
    song_page.raise_for_status()  
    song_soup = BeautifulSoup(song_page.text, "html.parser")  

    divs = song_soup.find_all("div", attrs={"class": None, "id": None})  
    lyrics = divs[0].get_text("\n").strip() if divs else None  

    return {  
        "source": "AZLyrics",  
        "song_url": song_url,  
        "artist": "-",  
        "song_title": song_title,  
        "album": "-",  
        "release_date": "-",  
        "label": "-",  
        "composer": "-",  
        "arranger": "-",  
        "cover_image": "https://via.placeholder.com/320",  
        "lyrics": lyrics,  
    }  
except Exception as e:  
    print(f"AZLyrics scraping error: {e}")  
    return None

def scrape_lyricsfreak(song_title):
try:
search_url = f"https://www.lyricsfreak.com/search.php?a=search&type=song&q={song_title.replace(' ', '+')}"
res = requests.get(search_url, timeout=10)
res.raise_for_status()
soup = BeautifulSoup(res.text, "html.parser")
results = soup.select("div.song > a")
if not results:
return None

first_link = results[0]["href"]  
    if not first_link.startswith("http"):  
        first_link = "https://www.lyricsfreak.com" + first_link  

    song_page = requests.get(first_link, timeout=10)  
    song_page.raise_for_status()  
    song_soup = BeautifulSoup(song_page.text, "html.parser")  

    lyrics_div = song_soup.find("div", class_="lyrics")  
    lyrics = lyrics_div.get_text("\n").strip() if lyrics_div else None  

    artist_tag = song_soup.find("a", class_="artist")  
    artist = artist_tag.text.strip() if artist_tag else "-"  

    return {  
        "source": "LyricsFreak",  
        "song_url": first_link,  
        "artist": artist,  
        "song_title": song_title,  
        "album": "-",  
        "release_date": "-",  
        "label": "-",  
        "composer": "-",  
        "arranger": "-",  
        "cover_image": "https://via.placeholder.com/320",  
        "lyrics": lyrics,  
    }  
except Exception as e:  
    print(f"LyricsFreak scraping error: {e}")  
    return None

def scrape_lyricscom(song_title):
try:
search_url = f"https://www.lyrics.com/serp.php?st={song_title.replace(' ', '+')}&qtype=2"
res = requests.get(search_url, timeout=10)
res.raise_for_status()
soup = BeautifulSoup(res.text, "html.parser")
first_link_tag = soup.select_one("td.tal.qx > a")
if not first_link_tag:
return None

song_url = "https://www.lyrics.com" + first_link_tag.get("href", "")  
    song_page = requests.get(song_url, timeout=10)  
    song_page.raise_for_status()  
    song_soup = BeautifulSoup(song_page.text, "html.parser")  

    lyrics_div = song_soup.find("pre", id="lyric-body-text")  
    lyrics = lyrics_div.get_text("\n").strip() if lyrics_div else None  

    artist_tag = song_soup.find("h3", class_="lyric-artist")  
    artist = artist_tag.text.strip() if artist_tag else "-"  

    cover_image_tag = song_soup.select_one("div.lyric-meta > img")  
    cover_image = cover_image_tag["src"] if cover_image_tag else "https://via.placeholder.com/320"  

    return {  
        "source": "Lyrics.com",  
        "song_url": song_url,  
        "artist": artist,  
        "song_title": song_title,  
        "album": "-",  
        "release_date": "-",  
        "label": "-",  
        "composer": "-",  
        "arranger": "-",  
        "cover_image": cover_image,  
        "lyrics": lyrics,  
    }  
except Exception as e:  
    print(f"Lyrics.com scraping error: {e}")  
    return None

=== Groq Integration ===

async def merge_and_clean_with_groq(data_list):
prompt = f"""
Berikut ini adalah beberapa data lirik dan metadata lagu dari berbagai sumber berbeda:

{data_list}

Tolong gabungkan dan rapikan menjadi satu data lengkap dengan format ini:

Artist: ...
Song: ...
Label: ...
Release Date: ...
Album/Single: ...
Arranger: ...
Composer: ...
Cover Image URL: ...
Lyrics: ...

Buat hasil yang paling lengkap dan rapi berdasarkan data di atas.
"""

headers = {  
    "Authorization": f"Bearer {GROQ_API_KEY}",  
    "Content-Type": "application/json",  
}  
payload = {  
    "prompt": prompt,  
    "max_tokens": 800,  
    "temperature": 0.2,  
}  

async with httpx.AsyncClient() as client:  
    resp = await client.post("https://api.groq.ai/v1/generate", headers=headers, json=payload)  
    if resp.status_code == 200:  
        result = resp.json()  
        return result.get("choices", [{}])[0].get("text", "").strip()  
    else:  
        print(f"Groq API error: {resp.status_code} - {resp.text}")  
        return None

=== Helper buat parse hasil Groq jadi dict sederhana ===

def parse_groq_output(text):
data = {}
for line in text.splitlines():
if ':' in line:
k, v = line.split(':', 1)
data[k.strip().lower().replace(' ', '_')] = v.strip()
return data

=== Generate HTML sesuai format yang kamu mau ===

def generate_html(data):
artist = data.get("artist", "-")
song = data.get("song", "-")
label = data.get("label", "-")
release_date = data.get("release_date", "-")
album_single = data.get("album/single", data.get("album_single", "-"))
arranger = data.get("arranger", "-")
composer = data.get("composer", "-")
cover_image = data.get("cover_image_url", data.get("cover_image", "https://via.placeholder.com/320"))
lyrics = data.get("lyrics", "-")

html = f"""

<details class="spoiler" open="">  
  <summary><h4 style="text-align: left;">Informasi</h4></summary>  
  <div class="table">  
    <table style="text-align: left;">  
      <tbody>  
        <tr>  
          <td>Artist</td>  
          <td>{artist}</td>  
        </tr>  
        <tr>  
          <td>Song</td>  
          <td>{song}</td>  
        </tr>  
        <tr>  
          <td>Label</td>  
          <td>{label}</td>  
        </tr>  
        <tr>  
          <td>Release Date</td>  
          <td>{release_date}</td>  
        </tr>  
        <tr>  
          <td>Album/Single</td>  
          <td>{album_single}</td>  
        </tr>  
        <tr>  
          <td>Arranger:</td>  
          <td>{arranger}</td>  
        </tr>  
        <tr>  
          <td>Composer</td>  
          <td>{composer}</td>  
        </tr>  
      </tbody>  
    </table>  
  </div>  
</details>  <table align="center" cellpadding="0" cellspacing="0" class="tr-caption-container" style="margin-left: auto; margin-right: auto;">  
  <tbody>  
    <tr>  
      <td style="text-align: center;">  
        <a href="{cover_image}" style="margin-left: auto; margin-right: auto;">  
          <img border="0" height="320" src="{cover_image}" width="320" />  
        </a>  
      </td>  
    </tr>  
    <tr>  
      <td class="tr-caption" style="text-align: center;">  
        Cover Image  
      </td>  
    </tr>  
  </tbody>  
</table>  
<br />  <details class="spoiler" open="">  
  <summary><h4 style="text-align: left;">Lirik</h4></summary>  
  <div style="background: #fff; padding: 15px; border-radius: 8px;">  
    <pre style="white-space: pre-wrap; font-family: Arial, sans-serif;">{lyrics}</pre>  
  </div>  
</details>  
"""  
    return html  === Helper async functions for Telegram command ===

async def fetch_lyrics_from_sources(song_title):
loop = asyncio.get_event_loop()
raw_data = await loop.run_in_executor(None, lambda: [
f for f in [
scrape_genius(song_title),
scrape_azlyrics(song_title),
scrape_lyricsfreak(song_title),
scrape_lyricscom(song_title)
] if f
])
return raw_data

async def process_with_groq(raw_data):
merged_text = await merge_and_clean_with_groq(raw_data)
return merged_text

async def send_raw_lyrics(update, raw_data):
combined_lyrics = "\n\n---\n\n".join(d.get("lyrics", "") for d in raw_data if d.get("lyrics"))
combined_lyrics = combined_lyrics[:4000] + ("...\n[Lirik terpotong]" if len(combined_lyrics) > 4000 else "")
await update.message.reply_text(combined_lyrics)

async def send_html_file(update, parsed_data, song_title):
html_content = generate_html(parsed_data)
file_name = f"{song_title}.html"
with open(file_name, "w", encoding="utf-8") as f:
f.write(html_content)
await update.message.reply_text("Berhasil mendapatkan data. Mengirim file HTML...")
await update.message.reply_document(document=open(file_name, "rb"), filename=file_name)

=== Telegram Command Handler ===

async def lirik_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
try:
if not context.args:
await update.message.reply_text("Gunakan format: /lirik <judul lagu>")
return

song_title = " ".join(context.args)  
    await update.message.reply_text(f"Mencari lirik dan info lagu: {song_title} ...")  

    raw_data = await fetch_lyrics_from_sources(song_title)  
    if not raw_data:  
        await update.message.reply_text("Lirik tidak ditemukan dari semua sumber.")  
        return  

    await update.message.reply_text("Menggabungkan dan merapikan data dengan AI...")  

    merged_text = await process_with_groq(raw_data)  
    if not merged_text:  
        await update.message.reply_text("Gagal memproses data dengan AI, mengirim data mentah...")  
        await send_raw_lyrics(update, raw_data)  
        return  

    parsed_data = parse_groq_output(merged_text)  
    if not parsed_data.get("lyrics"):  
        await update.message.reply_text("Lirik tidak ditemukan setelah pemrosesan AI.")  
        return  

    await send_html_file(update, parsed_data, song_title)  

except Exception as e:  
    error_msg = f"Terjadi kesalahan: {e}"  
    print(error_msg)  
    await update.message.reply_text(error_msg)

=== Main Telegram Bot Setup ===

def main():
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("lirik", lirik_command))
print("Bot berjalan...")
app.run_polling()

if name == "main":
main()

