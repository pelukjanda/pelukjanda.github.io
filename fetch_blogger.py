import requests
import os
import re
import json
import random
from html.parser import HTMLParser
from datetime import datetime, timezone

# === Konfigurasi ===
API_KEY = os.environ.get('BLOGGER_API_KEY')
BLOG_ID = os.environ.get('BLOG_ID')
DATA_DIR = 'data'
POST_DIR = 'posts' # Ini adalah folder tempat artikel akan disimpan
LABEL_DIR = 'labels'
POSTS_JSON = os.path.join(DATA_DIR, 'posts.json')
POSTS_PER_PAGE = 10
BASE_URL = 'https://pelukjanda.github.io' # GANTI DENGAN URL GITHUB PAGES ANDA! Contoh: 'https://username.github.io/repository-name'

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(POST_DIR, exist_ok=True)
os.makedirs(LABEL_DIR, exist_ok=True)

# === Utilitas ===
class ImageExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.thumbnail = None

    def handle_starttag(self, tag, attrs):
        if tag == 'img' and not self.thumbnail:
            for attr in attrs:
                if attr[0] == 'src':
                    self.thumbnail = attr[1]

def extract_thumbnail(html):
    parser = ImageExtractor()
    parser.feed(html)
    return parser.thumbnail or 'https://pelukjanda.github.io/tema/no-thumbnail.jpg' # Ganti jika Anda punya thumbnail default sendiri

def strip_html_and_divs(html):
    # Hapus semua tag HTML, termasuk div, tapi pertahankan isinya
    return re.sub(r'</?div[^>]*>', '', re.sub('<[^<]+?>', '', html))

def remove_anchor_tags(html_content):
    return re.sub(r'<a[^>]*>(.*?)<\/a>', r'\1', html_content)

def sanitize_filename(title):
    # Membersihkan judul untuk digunakan sebagai nama file
    return re.sub(r'\W+', '-', title.lower()).strip('-')

def render_labels(labels):
    if not labels:
        return ""
    html = ''
    for label in labels:
        filename = sanitize_filename(label)
        html += f'<span><a href="/labels/{filename}-1.html">{label}</a></span> '
    return html

def load_template(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def render_template(template, **context):
    for key, value in context.items():
        template = template.replace(f'{{{{ {key} }}}}', str(value))
    return template

def paginate(total_items, per_page):
    total_pages = (total_items + per_page - 1) // per_page
    return total_pages

def generate_pagination_links(base_url, current, total):
    html = '<div class="pagination-container">'
    
    # Previous Posts Link (Newer Page)
    if current > 1:
        prev_page_suffix = "" if current - 1 == 1 and "index" in base_url else f"-{current - 1}"
        prev_page_full_url = f"/{base_url}{prev_page_suffix}.html"
        html += f'<span class="pagination-link older-posts"><a href="{prev_page_full_url}">Previous Posts</a></span>'

    # Load More Link (Next Page)
    if current < total:
        next_page_suffix = f"-{current + 1}"
        next_page_full_url = f"/{base_url}{next_page_suffix}.html"
        html += f'<span class="pagination-link load-more"><a href="{next_page_full_url}">Load More</a></span>'
    
    html += '<span style="clear:both;"></span>'
    html += '</div>'
    return html

# === Komponen Custom (Head, Header, Sidebar, Footer) ===
def safe_load(path):
    return load_template(path) if os.path.exists(path) else ""

# CSS_FOR_RELATED_POSTS dan CSS_FOR_PAGE_NAVIGATION dihapus sepenuhnya
CSS_FOR_RELATED_POSTS = "" 
CSS_FOR_PAGE_NAVIGATION = ""

CUSTOM_HEAD_CONTENT = safe_load("custom_head.html")
CUSTOM_JS = safe_load("custom_js.html")
CUSTOM_HEADER = safe_load("custom_header.html")
CUSTOM_SIDEBAR = safe_load("custom_sidebar.html")
CUSTOM_FOOTER = safe_load("custom_footer.html")

CUSTOM_HEAD_FULL = CUSTOM_HEAD_CONTENT + CUSTOM_JS

# === Ambil semua postingan dari Blogger ===
def fetch_posts():
    all_posts = []
    page_token = ''
    while True:
        url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts?key={API_KEY}&maxResults=50"
        if page_token:
            url += f"&pageToken={page_token}"
        res = requests.get(url)
        if res.status_code != 200:
            raise Exception(f"Gagal fetch: {res.status_code} {res.text}")
        data = res.json()
        items = data.get("items", [])
        all_posts.extend(items)
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    with open(POSTS_JSON, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, ensure_ascii=False, indent=2)
    return all_posts

# === Template ===
POST_TEMPLATE = load_template("post_template.html")
INDEX_TEMPLATE = load_template("index_template.html")
LABEL_TEMPLATE = load_template("label_template.html")

# === Halaman per postingan ===
def generate_post_page(post, all_posts):
    filename_without_path = f"{sanitize_filename(post['title'])}.html"
    filepath = os.path.join(POST_DIR, filename_without_path)

    eligible_related = [p for p in all_posts if p['id'] != post['id'] and 'content' in p]
    num_related_posts = min(5, len(eligible_related))
    related_sample = random.sample(eligible_related, num_related_posts) if num_related_posts > 0 else []

    related_items_html = []
    for p_related in related_sample:
        related_post_absolute_link = f"/posts/{sanitize_filename(p_related['title'])}.html"
        
        related_post_content = p_related.get('content', '')
        thumb = extract_thumbnail(related_post_content)
        snippet = strip_html_and_divs(related_post_content)
        snippet = snippet[:100] + "..." if len(snippet) > 100 else snippet

        first_label_html = ""
        if p_related.get('labels'):
            label_name = p_related['labels'][0]
            sanitized_label_name = sanitize_filename(label_name)
            first_label_html = f'<span class="category testing"><a href="/labels/{sanitized_label_name}-1.html">{label_name}</a></span>'

        related_items_html.append(f"""
            <div class="post-card">
                <img class="post-image" src="{thumb}" alt="{p_related["title"]}">
                <div class="post-content">
                    <div class="post-meta">
                        {first_label_html}
                    </div>
                    <h2 class="post-title"><a href="{related_post_absolute_link}">{p_related["title"]}</a></h2>
                    <p class="post-author">By Om Sugeng · <a href="{related_post_absolute_link}">Baca Cerita</a></p>
                </div>
            </div>
        """)
    
    related_html = f"""
    <main class="container">
        <div class="post-list">
            {"".join(related_items_html)}
        </div>
    </main>
    """ if related_items_html else "<p>No related posts found.</p>"

    processed_content = remove_anchor_tags(post.get('content', ''))
    html = render_template(POST_TEMPLATE,
        title=post['title'],
        content=processed_content,
        labels=render_labels(post.get("labels", [])),
        related=related_html,
        custom_head=CUSTOM_HEAD_FULL,
        custom_header=CUSTOM_HEADER,
        custom_sidebar=CUSTOM_SIDEBAR,
        custom_footer=CUSTOM_FOOTER
    )
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    return filename_without_path

# === Halaman index beranda ===
def generate_index(posts):
    total_pages = paginate(len(posts), POSTS_PER_PAGE)
    for page in range(1, total_pages + 1):
        start = (page - 1) * POSTS_PER_PAGE
        end = start + POSTS_PER_PAGE
        items = posts[start:end]

        items_html = ""
        for post in items:
            post_filename = generate_post_page(post, posts)
            post_absolute_link = f"/posts/{post_filename}"
            
            snippet = strip_html_and_divs(post.get('content', ''))[:100]
            thumb = extract_thumbnail(post.get('content', ''))

            first_label_html = ""
            if post.get('labels'):
                label_name = post['labels'][0]
                sanitized_label_name = sanitize_filename(label_name)
                first_label_html = f'<span class="category testing"><a href="/labels/{sanitized_label_name}-1.html">{label_name}</a></span>'
            
            items_html += f"""
<main class="container">
    <div class="post-list">
        <div class="post-card">
            <img class="post-image" src="{thumb}" alt="thumbnail">
            <div class="post-content">
                <div class="post-meta">
                    {first_label_html}
                </div>
                <h2 class="post-title"><a href="{post_absolute_link}">{post['title']}</a></h2>
                <p class="post-author">By Om Sugeng · <a href="{post_absolute_link}">Baca Cerita</a></p>
            </div>
        </div>
    </div>
</main>
"""
        pagination = generate_pagination_links("index", page, total_pages)
        html = render_template(INDEX_TEMPLATE,
            items=items_html,
            pagination=pagination,
            custom_head=CUSTOM_HEAD_FULL,
            custom_header=CUSTOM_HEADER,
            custom_sidebar=CUSTOM_SIDEBAR,
            custom_footer=CUSTOM_FOOTER
        )
        output_file = f"index.html" if page == 1 else f"index-{page}.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

# === Halaman per label ===
def generate_label_pages(posts):
    label_map = {}
    for post in posts:
        if 'labels' in post:
            for label in post['labels']:
                label_map.setdefault(label, []).append(post)

    for label, label_posts in label_map.items():
        total_pages = paginate(len(label_posts), POSTS_PER_PAGE)
        for page in range(1, total_pages + 1):
            start = (page - 1) * POSTS_PER_PAGE
            end = start + POSTS_PER_PAGE
            items = label_posts[start:end]

            items_html = ""
            for post in items:
                post_filename = generate_post_page(post, posts)
                post_absolute_link = f"/posts/{post_filename}"
                
                snippet = strip_html_and_divs(post.get('content', ''))[:100]
                thumb = extract_thumbnail(post.get('content', ''))

                first_label_html = ""
                if post.get('labels'):
                    label_name = post['labels'][0]
                    sanitized_label_name = sanitize_filename(label_name)
                    first_label_html = f'<span class="category testing"><a href="/labels/{sanitized_label_name}-1.html">{label_name}</a></span>'

                items_html += f"""
<main class="container">
    <div class="post-list">
        <div class="post-card">
            <img class="post-image" src="{thumb}" alt="thumbnail">
            <div class="post-content">
                <div class="post-meta">
                    {first_label_html}
                </div>
                <h2 class="post-title"><a href="{post_absolute_link}">{post['title']}</a></h2>
                <p class="post-author">By Om Sugeng · <a href="{post_absolute_link}">Baca Cerita</a></p>
            </div>
        </div>
    </div>
</main>
"""
            pagination = generate_pagination_links(
                f"labels/{sanitize_filename(label)}", page, total_pages
            )
            html = render_template(LABEL_TEMPLATE,
                label=label,
                items=items_html,
                pagination=pagination,
                custom_head=CUSTOM_HEAD_FULL,
                custom_header=CUSTOM_HEADER,
                custom_sidebar=CUSTOM_SIDEBAR,
                custom_footer=CUSTOM_FOOTER
            )
            output_file = os.path.join(LABEL_DIR, f"{sanitize_filename(label)}-{page}.html")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html)

def parse_blogger_timestamp(timestamp_str):
    """
    Parses Blogger API timestamp strings into datetime objects.
    Handles different formats Blogger might return.
    """
    try:
        # Try parsing with timezone information
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except ValueError:
        # Fallback for older/different formats, e.g., 'YYYY-MM-DDTHH:MM:SS.fffZ'
        # This will assume UTC if 'Z' is present but doesn't have offset
        if timestamp_str.endswith('Z'):
            timestamp_str = timestamp_str[:-1] # Remove 'Z'
            try:
                return datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%f').replace(tzinfo=timezone.utc)
            except ValueError:
                return datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
        raise ValueError(f"Unknown datetime format: {timestamp_str}")


# === Fungsi Baru untuk Feed XML ===
def generate_feed_xml(posts):
    feed_entries = []
    # Batasi jumlah entri di feed, misalnya 10 atau 20 postingan terbaru
    # Sort posts by 'updated' or 'published' date in descending order
    sorted_posts = sorted(posts, key=lambda p: p.get('updated', p.get('published', '')), reverse=True)

    for post in sorted_posts[:20]: # Ambil 20 postingan terbaru
        title = post['title']
        link = f"{BASE_URL}/posts/{sanitize_filename(title)}.html"
        
        updated_date_str = post.get('updated', post.get('published'))
        if not updated_date_str: # Skip if no valid date
            continue
        
        try:
            dt_object = parse_blogger_timestamp(updated_date_str)
            formatted_date = dt_object.isoformat(timespec='seconds').replace('+00:00', 'Z') # Ensure 'Z' for Atom feed
        except ValueError as e:
            print(f"Warning: Could not parse date for post '{title}': {e}. Skipping feed entry.")
            continue

        # Ambil ringkasan konten (misalnya 200 karakter pertama setelah strip HTML)
        summary = strip_html_and_divs(post.get('content', ''))
        summary = summary[:200] + "..." if len(summary) > 200 else summary

        feed_entries.append(f"""
    <entry>
        <title>{title}</title>
        <link href="{link}"/>
        <updated>{formatted_date}</updated>
        <id>{link}</id>
        <content type="html"><![CDATA[{summary}]]></content>
    </entry>"""
        )

    # Get the latest updated date from all posts for the feed's updated tag
    latest_updated = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    if posts:
        # Find the actual latest updated post among all fetched posts
        latest_post_data = sorted(posts, key=lambda p: p.get('updated', p.get('published', '')), reverse=True)
        if latest_post_data:
            latest_updated_str = latest_post_data[0].get('updated', latest_post_data[0].get('published'))
            try:
                latest_dt_obj = parse_blogger_timestamp(latest_updated_str)
                latest_updated = latest_dt_obj.isoformat(timespec='seconds').replace('+00:00', 'Z')
            except ValueError as e:
                print(f"Warning: Could not parse latest blog update date: {e}. Using current time.")

    feed_content = f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Peluk Janda</title> <link href="{BASE_URL}/feed.xml" rel="self"/>
  <link href="{BASE_URL}/"/>
  <updated>{latest_updated}</updated>
  <id>{BASE_URL}/</id>
  <author>
    <name>Om Sugeng</name> </author>
{chr(10).join(feed_entries)}
</feed>"""

    with open('feed.xml', 'w', encoding='utf-8') as f:
        f.write(feed_content)
    print("✅ feed.xml berhasil dibuat.")

# === Fungsi Baru untuk Sitemap XML ===
def generate_sitemap_xml(posts):
    urls = []
    # Add homepage
    urls.append(f"""
  <url>
    <loc>{BASE_URL}/</loc>
    <lastmod>{datetime.now(timezone.utc).isoformat(timespec='seconds')}+00:00</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>""")

    # Add posts
    for post in posts:
        title = post['title']
        link = f"{BASE_URL}/posts/{sanitize_filename(title)}.html"
        
        lastmod_date_str = post.get('updated', post.get('published'))
        if not lastmod_date_str:
            continue

        try:
            dt_object = parse_blogger_timestamp(lastmod_date_str)
            formatted_lastmod = dt_object.isoformat(timespec='seconds').replace('Z', '+00:00') # Ensure +00:00 for sitemap
        except ValueError as e:
            print(f"Warning: Could not parse date for post '{title}': {e}. Skipping sitemap entry for this post.")
            continue

        urls.append(f"""
  <url>
    <loc>{link}</loc>
    <lastmod>{formatted_lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>""")

    # Add index pagination pages
    total_index_pages = paginate(len(posts), POSTS_PER_PAGE)
    for page in range(2, total_index_pages + 1): # Start from page 2 as page 1 is homepage
        index_page_link = f"{BASE_URL}/index-{page}.html"
        urls.append(f"""
  <url>
    <loc>{index_page_link}</loc>
    <lastmod>{datetime.now(timezone.utc).isoformat(timespec='seconds')}+00:00</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>""")


    # Add label pages
    label_map = {}
    for post in posts:
        if 'labels' in post:
            for label in post['labels']:
                label_map.setdefault(label, []).append(post)

    for label in label_map.keys():
        total_label_pages = paginate(len(label_map[label]), POSTS_PER_PAGE)
        for page in range(1, total_label_pages + 1):
            label_page_link = f"{BASE_URL}/labels/{sanitize_filename(label)}-{page}.html"
            urls.append(f"""
  <url>
    <loc>{label_page_link}</loc>
    <lastmod>{datetime.now(timezone.utc).isoformat(timespec='seconds')}+00:00</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>""")

    sitemap_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>"""

    with open('sitemap.xml', 'w', encoding='utf-8') as f:
        f.write(sitemap_content)
    print("✅ sitemap.xml berhasil dibuat.")

# === Eksekusi ===
if __name__ == '__main__':
    print("📥 Mengambil artikel...")
    posts = fetch_posts()
    print(f"✅ Artikel diambil: {len(posts)}")
    
    print("🔄 Membuat halaman HTML...")
    generate_index(posts)
    generate_label_pages(posts)
    print("✅ Halaman index, label, dan artikel selesai dibuat.")

    print("📝 Membuat feed.xml...")
    generate_feed_xml(posts)

    print("🗺️ Membuat sitemap.xml...")
    generate_sitemap_xml(posts)
    
    print("🎉 Proses selesai!")
