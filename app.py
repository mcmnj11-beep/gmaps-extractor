# =============================================================================
# GOOGLE MAPS DATA EXTRACTOR  —  app.py
# =============================================================================
#
# INSTALLATION
# ------------
# pip install streamlit requests beautifulsoup4 pandas openpyxl lxml
#
# RUN LOCALLY
# -----------
# streamlit run app.py
#
# GOOGLE PLACES API KEY
# ---------------------
# 1. Go to https://console.cloud.google.com/
# 2. Create a project and enable "Places API" (legacy) under APIs & Services.
# 3. Create an API key under "Credentials".
# 4. (Recommended) Restrict the key to Places API only.
#
# =============================================================================

import time
import re
import io

import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Google Maps Data Extractor",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS  —  industrial / utilitarian aesthetic with accent green
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }

    /* Main background */
    .stApp {
        background-color: #0d0f12;
        color: #d4d8de;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #13171d;
        border-right: 1px solid #2a2f38;
    }
    [data-testid="stSidebar"] * { color: #c8cdd6 !important; }
    [data-testid="stSidebar"] .stTextInput input,
    [data-testid="stSidebar"] .stTextInput textarea {
        background: #0d0f12 !important;
        border: 1px solid #2e3540 !important;
        color: #e0e4ea !important;
        border-radius: 4px !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.82rem !important;
    }
    [data-testid="stSidebar"] .stTextInput input:focus {
        border-color: #39d98a !important;
        box-shadow: 0 0 0 2px rgba(57,217,138,0.15) !important;
    }

    /* Sidebar button */
    [data-testid="stSidebar"] .stButton > button {
        background: #39d98a !important;
        color: #0d0f12 !important;
        border: none !important;
        border-radius: 4px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        letter-spacing: 0.04em !important;
        padding: 0.6rem 1rem !important;
        width: 100% !important;
        transition: background 0.2s !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: #2fbf77 !important;
    }

    /* Header */
    .main-header {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.7rem;
        font-weight: 600;
        color: #39d98a;
        letter-spacing: -0.02em;
        margin-bottom: 0.1rem;
    }
    .main-sub {
        font-size: 0.85rem;
        color: #5a6373;
        margin-bottom: 1.5rem;
        font-family: 'IBM Plex Mono', monospace;
    }

    /* Metric cards */
    .metric-row {
        display: flex;
        gap: 12px;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #13171d;
        border: 1px solid #2a2f38;
        border-radius: 6px;
        padding: 14px 20px;
        flex: 1;
        text-align: center;
    }
    .metric-card .val {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.7rem;
        font-weight: 600;
        color: #39d98a;
        line-height: 1;
    }
    .metric-card .lbl {
        font-size: 0.72rem;
        color: #5a6373;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 4px;
    }

    /* Status pill */
    .status-pill {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    .pill-ok   { background: rgba(57,217,138,0.12); color: #39d98a; border: 1px solid #39d98a44; }
    .pill-warn { background: rgba(255,193,7,0.12);  color: #ffc107; border: 1px solid #ffc10744; }
    .pill-err  { background: rgba(255,82,82,0.12);  color: #ff5252; border: 1px solid #ff525244; }

    /* Download buttons row */
    .dl-row { display: flex; gap: 10px; margin-top: 1rem; }

    /* Dataframe styling override */
    .stDataFrame { border: 1px solid #2a2f38; border-radius: 6px; overflow: hidden; }

    /* Divider */
    hr { border-color: #2a2f38 !important; margin: 1.5rem 0 !important; }

    /* Info / warning boxes */
    .stAlert { border-radius: 6px !important; font-size: 0.85rem !important; }

    /* Progress bar */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #39d98a, #25c073) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
PLACES_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAILS_URL     = "https://maps.googleapis.com/maps/api/place/details/json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

# Domains that are almost certainly not real business emails
SPAM_DOMAINS = {
    "example.com", "domain.com", "email.com", "yoursite.com",
    "sentry.io", "wixpress.com", "squarespace.com", "wordpress.com",
    "amazonaws.com", "cloudfront.net", "googleapis.com",
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPER  —  Email scraper
# ─────────────────────────────────────────────────────────────────────────────
def scrape_email(url: str, timeout: int = 8) -> str:
    """
    Visit a business website and extract the first plausible email address.

    Strategy:
      1. Fetch homepage HTML.
      2. Try <a href="mailto:..."> links first (highest accuracy).
      3. Fall back to regex scan of the entire page text.
      4. Filter out placeholder / CDN / framework email addresses.
    """
    if not url:
        return ""
    # Ensure the URL has a scheme
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        resp = requests.get(
            url,
            headers=HEADERS,
            timeout=timeout,
            allow_redirects=True,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # --- Strategy 1: mailto links ---
        for tag in soup.find_all("a", href=True):
            href: str = tag["href"]
            if href.lower().startswith("mailto:"):
                candidate = href[7:].split("?")[0].strip()
                if _valid_email(candidate):
                    return candidate

        # --- Strategy 2: regex over page text ---
        text = soup.get_text(separator=" ")
        matches = EMAIL_REGEX.findall(text)
        filtered = [m for m in matches if _valid_email(m)]
        if filtered:
            # Deduplicate while preserving order
            seen: set[str] = set()
            unique = []
            for m in filtered:
                if m.lower() not in seen:
                    seen.add(m.lower())
                    unique.append(m)
            return ", ".join(unique[:3])  # return up to 3 emails

    except requests.exceptions.Timeout:
        return "Timeout"
    except requests.exceptions.TooManyRedirects:
        return "Redirect loop"
    except requests.exceptions.ConnectionError:
        return "Connection error"
    except requests.exceptions.HTTPError as exc:
        return f"HTTP {exc.response.status_code}"
    except Exception:
        return "Scrape error"
    return ""


def _valid_email(email: str) -> bool:
    """Return True if the email looks like a real business contact address."""
    if not email or "@" not in email:
        return False
    domain = email.split("@")[-1].lower()
    # Reject obvious non-email patterns (e.g. image filenames caught by regex)
    if any(domain.endswith(ext) for ext in (".png", ".jpg", ".gif", ".svg", ".webp")):
        return False
    if domain in SPAM_DOMAINS:
        return False
    # Must have at least one dot in domain
    if "." not in domain:
        return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# HELPER  —  Google Places API
# ─────────────────────────────────────────────────────────────────────────────
def fetch_places(api_key: str, query: str, location: str) -> list[dict]:
    """
    Call the Places Text Search endpoint and paginate up to 60 results.
    Returns a list of raw place dicts from the API.
    """
    full_query = f"{query} in {location}"
    params = {"query": full_query, "key": api_key}
    places: list[dict] = []

    for page in range(3):  # max 3 pages × 20 results = 60
        try:
            resp = requests.get(PLACES_TEXT_SEARCH_URL, params=params, timeout=15)
            data = resp.json()
        except Exception as exc:
            st.error(f"Network error while calling Places API: {exc}")
            break

        status = data.get("status", "")
        if status == "REQUEST_DENIED":
            st.error(
                "❌ API request denied. Check that your API key is valid "
                "and that the **Places API** is enabled in your Google Cloud project."
            )
            return []
        if status == "INVALID_REQUEST":
            st.error("❌ Invalid request. Please check your search query.")
            return []
        if status not in ("OK", "ZERO_RESULTS"):
            st.warning(f"Unexpected API status: {status}")
            break

        results = data.get("results", [])
        places.extend(results)

        next_token = data.get("next_page_token")
        if not next_token or len(results) == 0:
            break

        # Google requires a short delay before the next page token is valid
        time.sleep(2.2)
        params = {"pagetoken": next_token, "key": api_key}

    return places


def fetch_place_details(api_key: str, place_id: str) -> dict:
    """
    Call the Place Details endpoint to get phone number and website.
    Returns the 'result' dict or empty dict on failure.
    """
    params = {
        "place_id": place_id,
        "fields": "formatted_phone_number,website",
        "key": api_key,
    }
    try:
        resp = requests.get(PLACES_DETAILS_URL, params=params, timeout=10)
        data = resp.json()
        if data.get("status") == "OK":
            return data.get("result", {})
    except Exception:
        pass
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# CORE PIPELINE
# ─────────────────────────────────────────────────────────────────────────────
def run_extraction(api_key: str, query: str, location: str) -> pd.DataFrame:
    """
    Full pipeline:
      1. Text Search  →  list of places
      2. Place Details  →  phone + website per place
      3. Web scrape  →  email per website
    Returns a tidy DataFrame.
    """
    # ── Step 1: Fetch places ──────────────────────────────────────────────
    with st.spinner("🔍 Searching Google Maps…"):
        places = fetch_places(api_key, query, location)

    if not places:
        st.warning("No results found. Try a different query or location.")
        return pd.DataFrame()

    total = len(places)
    st.markdown(
        f'<div style="margin-bottom:0.8rem;font-family:\'IBM Plex Mono\',monospace;'
        f'font-size:0.82rem;color:#5a6373;">Found <span style="color:#39d98a;font-weight:600;">'
        f'{total}</span> places — fetching details & scraping emails…</div>',
        unsafe_allow_html=True,
    )

    # ── Step 2 + 3: Details & email scraping ─────────────────────────────
    progress_bar = st.progress(0, text="Starting…")
    placeholder   = st.empty()   # live-updating dataframe

    rows: list[dict] = []

    for i, place in enumerate(places):
        name      = place.get("name", "N/A")
        address   = place.get("formatted_address", "N/A")
        rating    = place.get("rating", "N/A")
        n_reviews = place.get("user_ratings_total", "N/A")
        place_id  = place.get("place_id", "")

        # Details call (phone + website)
        details  = fetch_place_details(api_key, place_id) if place_id else {}
        phone    = details.get("formatted_phone_number", "N/A")
        website  = details.get("website", "")

        # Email scrape
        email = scrape_email(website) if website else ""

        rows.append(
            {
                "Business Name": name,
                "Address":       address,
                "Phone":         phone,
                "Website":       website or "N/A",
                "Email":         email or "N/A",
                "Rating":        rating,
                "Reviews":       n_reviews,
            }
        )

        # Live update
        pct  = (i + 1) / total
        progress_bar.progress(pct, text=f"Processing {i+1}/{total}: {name[:45]}")
        placeholder.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

        # Polite delay to avoid rate limits
        time.sleep(0.3)

    progress_bar.progress(1.0, text="✅ Done!")
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def df_to_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def df_to_excel(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Results")
        ws = writer.sheets["Results"]
        # Auto-fit columns
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col) + 4
            ws.column_dimensions[col[0].column_letter].width = min(max_len, 60)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR  —  Inputs
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="font-family:\'IBM Plex Mono\',monospace;font-size:1.05rem;'
        'font-weight:600;color:#39d98a;margin-bottom:0.2rem;">⚙ Configuration</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:0.72rem;color:#5a6373;margin-bottom:1.2rem;">'
        'Powered by Google Places API + BeautifulSoup</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    api_key  = st.text_input("Google Maps API Key", type="password",
                              placeholder="AIza…",
                              help="Enable 'Places API' in your Google Cloud project.")
    query    = st.text_input("Search Query",
                              placeholder="e.g. Interior Designers",
                              help="Business type or keyword to search for.")
    location = st.text_input("Location",
                              placeholder="e.g. Bangalore",
                              help="City, neighbourhood, or region.")

    st.markdown("<br>", unsafe_allow_html=True)
    search_clicked = st.button("🔎  Search", use_container_width=True)

    st.divider()
    st.markdown(
        '<div style="font-size:0.7rem;color:#3d4552;line-height:1.6;">'
        '⚠ This tool uses the <b>Places API (legacy)</b>.<br>'
        'Ensure billing is enabled on your GCP project.<br><br>'
        '📧 Email scraping depends on each website\'s structure — results may vary.'
        '</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PANEL
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="main-header">🗺 Google Maps Data Extractor</div>'
    '<div class="main-sub">// Text Search · Place Details · Email Scraper · CSV/Excel Export</div>',
    unsafe_allow_html=True,
)
st.divider()

# ── Session state ─────────────────────────────────────────────────────────────
if "result_df" not in st.session_state:
    st.session_state.result_df = pd.DataFrame()

# ── Run pipeline on button click ──────────────────────────────────────────────
if search_clicked:
    # Input validation
    if not api_key.strip():
        st.error("Please enter your Google Maps API key in the sidebar.")
    elif not query.strip():
        st.error("Please enter a search query.")
    elif not location.strip():
        st.error("Please enter a location.")
    else:
        df = run_extraction(api_key.strip(), query.strip(), location.strip())
        st.session_state.result_df = df

# ── Display results ───────────────────────────────────────────────────────────
df = st.session_state.result_df

if not df.empty:
    # Metrics row
    emails_found = (df["Email"] != "N/A").sum()
    phones_found = (df["Phone"] != "N/A").sum()
    sites_found  = (df["Website"] != "N/A").sum()
    avg_rating   = df[df["Rating"] != "N/A"]["Rating"].astype(float).mean()

    st.markdown(
        f"""
        <div class="metric-row">
            <div class="metric-card">
                <div class="val">{len(df)}</div>
                <div class="lbl">Businesses</div>
            </div>
            <div class="metric-card">
                <div class="val">{emails_found}</div>
                <div class="lbl">Emails Found</div>
            </div>
            <div class="metric-card">
                <div class="val">{phones_found}</div>
                <div class="lbl">Phone Numbers</div>
            </div>
            <div class="metric-card">
                <div class="val">{sites_found}</div>
                <div class="lbl">Websites</div>
            </div>
            <div class="metric-card">
                <div class="val">{avg_rating:.1f}⭐</div>
                <div class="lbl">Avg Rating</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Final dataframe
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("### 📥 Export Results")

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="⬇️  Download as CSV",
            data=df_to_csv(df),
            file_name=f"gmaps_extract_{query}_{location}.csv".replace(" ", "_"),
            mime="text/csv",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            label="⬇️  Download as Excel",
            data=df_to_excel(df),
            file_name=f"gmaps_extract_{query}_{location}.xlsx".replace(" ", "_"),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

else:
    # Empty state
    st.markdown(
        """
        <div style="
            background:#13171d;
            border:1px dashed #2a2f38;
            border-radius:8px;
            padding:3rem 2rem;
            text-align:center;
            margin-top:1rem;
        ">
            <div style="font-size:2.5rem;margin-bottom:0.8rem;">🗺️</div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:0.95rem;
                        color:#39d98a;font-weight:600;margin-bottom:0.4rem;">
                Ready to extract
            </div>
            <div style="font-size:0.82rem;color:#5a6373;max-width:380px;margin:0 auto;line-height:1.7;">
                Enter your API key, a business type, and a city in the sidebar,
                then hit <strong style="color:#c8cdd6;">Search</strong> to begin.
                <br><br>
                Results appear live as each business is processed.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
