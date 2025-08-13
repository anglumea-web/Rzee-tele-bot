import os
import re
import requests
from bs4 import BeautifulSoup
from groq import Groq
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ========== CONFIG (set di Railway sebagai Environment Variable) ==========
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")        # BotFather token
GENIUS_TOKEN = os.getenv("GENIUS_TOKEN")            # optional
GROQ_API_KEY = os.getenv("GROQ_API_KEY")            # ganti OpenAI
# ==========================================================================

# HTML template (tetap sama seperti sebelumnya)
HTML_TEMPLATE = """<!-- Judul Post -->
<h2 style="text-align: center; font-size: 28px; margin-bottom: 15px;">
  {post_title}
</h2>
<!-- Gambar Utama -->
<div style="text-align: center; margin-bottom: 20px;">
  <img src="{image_url}" alt="Deskripsi Gambar" title="{post_title}" style="max-width: 100%; border-radius: 12px;">
</div>
<!-- Informasi Detail -->
<details class="spoiler" open="">
  <summary><h4 style="text-align: left;">📌 Informasi Lengkap</h4></summary>
  <div class="table" style="overflow-x:auto;">
    <table style="width: 100%; border-collapse: collapse; font-size: 15px;">
      <tbody>
        <tr><td>Kategori</td><td>{category}</td></tr>
        <tr><td>Judul</td><td>{title}</td></tr>
        <tr><td>Pencipta / Artist</td><td>{artist}</td></tr>
        <tr><td>Tanggal Rilis</td><td>{release_date}</td></tr>
        <tr><td>Durasi / Panjang</td><td>{duration}</td></tr>
        <tr><td>Bahasa</td><td>{language}</td></tr>
        <tr><td>Link Resmi</td>
          <td><a href="{source_url}" target="_blank" rel="noopener noreferrer">Klik di sini</a></td>
        </tr>
      </tbody>
    </table>
  </div>
</details>
<hr style="margin: 20px 0;">
<!-- Deskripsi Singkat -->
<h3>📖 Deskripsi</h3>
<p style="text-align: justify;">{description}</p>
<!-- Lirik / Konten Utama -->
<h3>🎵 Lirik / Konten Utama</h3>
<pre style="background: #f4f4f4; padding: 15px; border-radius: 8px; font-size: 14px; white-space: pre-wrap; word-wrap: break-word;">
{content_main}
</pre>
<!-- Fakta Menarik -->
<h3>💡 Fakta Menarik</h3>
<ul>{facts}</ul>
<!-- Embed Video / Audio -->
<h3>▶ Video / Audio</h3>
<div style="text-align: center; margin-top: 15px;">
  <iframe width="100%" height="315" src="https://www.youtube.com/embed/{youtube_id}" 
    title="YouTube video player" frameborder="0" allowfullscreen></iframe>
</div>
<!-- Sumber Referensi -->
<h3>🔗 Sumber</h3>
<ol>{sources}</ol>
<!-- Tag SEO -->
<div style="display:none;">Tag SEO: {tags}</div>
"""

# ----------------- Helper functions -----------------

def split_artist_title(text: str):
    if " - " in text:
        left, right = text.split(" - ", 1)
        return left.strip(), right.strip()
    return None, text.strip()

def genius_search(query: str):
    if not GENIUS_TOKEN:
        return None
    url = "https://api.genius.com/search"
    headers = {"Authorization": f"Bearer {GENIUS_TOKEN}"}
    try:
        r = requests.get(url, headers=headers, params={"q": query}, timeout=8)
        if r.status_code != 200:
            return None
        hits = r.json().get("response", {}).get("hits", [])
        if not hits:
            return None
        top = hits[0]["result"]
        return {
            "title": top.get("title"),
            "artist": top.get("primary_artist", {}).get("name"),
            "url": top.get("url"),
            "image": top.get("header_image_thumbnail_url") or "",
        }
    except Exception:
        return None

def scrape_page(url: str):
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=8)
        if r.status_code != 200:
            return {}
        s = BeautifulSoup(r.text, "html.parser")
        meta = {}
        og_title = s.find("meta", property="og:title")
        og_desc = s.find("meta", property="og:description")
        og_image = s.find("meta", property="og:image")
        meta["title"] = og_title["content"] if og_title and og_title.get("content") else ""
        meta["description_meta"] = og_desc["content"] if og_desc and og_desc.get("content") else ""
        meta["image"] = og_image["content"] if og_image and og_image.get("content") else ""
        possible = s.find_all(["p","div","span"], limit=40)
        excerpt = ""
        for el in possible:
            txt = el.get_text(" ", strip=True)
            if 40 <= len(txt) <= 300 and "copyright" not in txt.lower():
                excerpt = txt[:90]
                break
        meta["excerpt"] = excerpt
        date_meta = s.find("meta", property="music:release_date") or s.find("meta", attrs={"name":"release_date"})
        meta["release_date"] = date_meta["content"] if date_meta and date_meta.get("content") else ""
        return meta
    except Exception:
        return {}

# 🔹 Fungsi AI Description (pakai Groq)
def ai_generate_description(query: str, source: str = None):
    if not GROQ_API_KEY:
        return "Deskripsi otomatis tidak tersedia (Groq API key belum diset)."
    
    client = Groq(api_key=GROQ_API_KEY)
    prompt = (
        f"Buat deskripsi ringkas (2-3 kalimat) tentang lagu atau konten berikut: '{query}'. "
        "Jangan tulis lirik lengkap. Sebutkan tema/nuansa lagu jika memungkinkan. Sertakan sumber jika ada."
    )
    if source:
        prompt += f" Sumber: {source}"
    try:
        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=130,
            temperature=0.6
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"(AI gagal: {e})"

def build_html(data: dict):
    facts_html = "".join(f"  <li>{f}</li>\n" for f in data.get("facts", []))
    sources_html = "".join(f"  <li><a href=\"{s}\">{s}</a></li>\n" for s in data.get("sources", []))
    youtube_id = ""
    if data.get("youtube"):
        m = re.search(r"(?:v=|embed/|youtu\.be/)([A-Za-z0-9_-]{6,})", data["youtube"])
        if m:
            youtube_id = m.group(1)
    return HTML_TEMPLATE.format(
        post_title = data.get("post_title", data.get("title","Untitled")),
        image_url = data.get("image_url","URL_GAMBAR.jpg"),
        category = data.get("category","Musik"),
        title = data.get("title","Unknown"),
        artist = data.get("artist","Unknown"),
        release_date = data.get("release_date","DD/MM/YYYY"),
        duration = data.get("duration","00:00"),
        language = data.get("language","Unknown"),
        source_url = data.get("source",""),
        description = data.get("description",""),
        content_main = data.get("content_main","[Konten utama tidak disertakan karena hak cipta]"),
        facts = facts_html,
        youtube_id = youtube_id,
        sources = sources_html,
        tags = ", ".join(data.get("tags", []))
    )

# -------------- Telegram handler -----------------
async def lirik_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Kirim: /lirik <artist> <judul> — contoh: /lirik Isyana Sarasvati My Mystery")
        return
    query = " ".join(args)
    await update.message.reply_text(f"🔎 Mencari: {query}\n(Ini akan menampilkan sumber, potongan singkat, dan deskripsi — bukan lirik penuh)")

    maybe_artist, maybe_title = split_artist_title(query)
    search_q = f"{maybe_artist} {maybe_title}" if maybe_title and maybe_artist else query

    genius = genius_search(search_q)
    source = ""
    image = ""
    scraped = {}
    if genius:
        source = genius.get("url","")
        image = genius.get("image","")
        title = genius.get("title") or maybe_title or query
        artist = genius.get("artist") or maybe_artist or ""
    else:
        title = maybe_title or query
        artist = maybe_artist or ""

    if source:
        scraped = scrape_page(source)
    else:
        try:
            ddg = requests.get("https://html.duckduckgo.com/html/", params={"q": search_q + " lyrics"}, timeout=6, headers={"User-Agent":"Mozilla/5.0"})
            s = BeautifulSoup(ddg.text, "html.parser")
            a = s.find("a", {"class":"result__a"})
            if a and a.get("href"):
                source = a.get("href")
                scraped = scrape_page(source)
        except Exception:
            scraped = {}

    excerpt = scraped.get("excerpt","")
    if excerpt and len(excerpt) > 90:
        excerpt = excerpt[:90]

    ai_desc = ai_generate_description(search_q, source)

    data = {
        "post_title": f"{title} — {artist}" if artist else title,
        "image_url": image or "URL_GAMBAR.jpg",
        "category": "Musik",
        "title": title,
        "artist": artist,
        "release_date": scraped.get("release_date","DD/MM/YYYY"),
        "duration": scraped.get("duration","00:00"),
        "language": "Indonesia/English",
        "source": source or "",
        "description": ai_desc or scraped.get("description_meta","Deskripsi singkat tidak tersedia."),
        "content_main": excerpt or "[Tidak menyertakan lirik lengkap. Hanya potongan singkat atau ringkasan.]",
        "facts": [f"Penelusuran untuk: {search_q}", f"Sumber utama: {source or 'Tidak ditemukan'}"],
        "sources": [source] if source else [],
        "youtube": "",
        "tags": [artist, title]
    }

    summary_txt = f"Judul: {data['title']}\nPenyanyi: {data['artist']}\nSumber: {data['source'] or '[Tidak ditemukan]'}\n\nPotongan singkat (≤90 chars):\n{data['content_main']}\n\nDeskripsi singkat:\n{data['description'][:400]}"
    await update.message.reply_text(summary_txt)

    html = build_html(data)
    fname = re.sub(r"[^\w\-_. ]", "_", f"{data['post_title']}.html")[:120]
    with open("result.html","w",encoding="utf-8") as fh:
        fh.write(html)

    await update.message.reply_document(document=InputFile("result.html"), filename=fname)
    await update.message.reply_text("✅ HTML hasil telah dikirim. Jika perlu, kamu bisa paste ke Blogger (ingat aturan hak cipta).")

# --------------- main ---------------
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("lirik", lirik_handler))
    print("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()