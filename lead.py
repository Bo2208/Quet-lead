import io
import random
import re
import subprocess
import time
import urllib.parse
from datetime import datetime
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# 1. Kiểm tra Chromium trên Server
try:
    subprocess.run(["playwright", "install", "chromium"], check=True)
except Exception:
    pass

# 2. KHỞI TẠO SESSION STATE LƯU VẾT CHỐNG TRÙNG LẮP
if "history_mst_links" not in st.session_state:
    st.session_state.history_mst_links = set()

if "history_gmaps_urls" not in st.session_state:
    st.session_state.history_gmaps_urls = set()

# 3. CẤU HÌNH TRANG & CSS GIAO DIỆN TRUNG THU (ĐÃ ẨN NÚT ĐỔI SÁNG/TỐI)
st.set_page_config(
    page_title="Multi-Source Scraper - Hội Mùa Trăng",
    page_icon="🌕",
    layout="wide",
)

mid_autumn_tabs_css = """
    <style>
    /* NỀN TỔNG THỂ VÀ CUỘN TRANG */
    html, body, .stApp, [data-testid="stAppViewContainer"] {
        background: linear-gradient(180deg, #090e17 0%, #0f1c2e 60%, #16273e 100%) !important;
        overflow-y: auto !important;
    }
    
    /* MẶT TRĂNG GÓC TRÊN */
    [data-testid="stAppViewContainer"]::before {
        content: "";
        position: fixed;
        top: 25px;
        right: 45px;
        width: 85px;
        height: 85px;
        border-radius: 50%;
        background-color: #f6e58d;
        background-image: 
            radial-gradient(circle at 30% 30%, rgba(220, 190, 100, 0.4) 12%, transparent 13%),
            radial-gradient(circle at 65% 45%, rgba(210, 180, 90, 0.35) 18%, transparent 19%),
            radial-gradient(circle at 45% 70%, rgba(220, 190, 100, 0.3) 10%, transparent 11%);
        box-shadow: 0 0 25px rgba(246, 229, 141, 0.6);
        z-index: 1 !important;
        pointer-events: none;
    }

    /* KHUNG GIAO DIỆN CHÍNH */
    [data-testid="stMainBlockContainer"] {
        background-color: rgba(15, 28, 46, 0.92) !important;
        border: 1px solid rgba(246, 229, 141, 0.35) !important;
        border-radius: 16px !important;
        padding: 30px !important;
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.6) !important;
        margin-top: 20px !important;
        margin-bottom: 50px !important;
    }

    /* TÙY CHỈNH THẺ TABS */
    button[data-baseweb="tab"] {
        background-color: rgba(6, 13, 23, 0.7) !important;
        border: 1px solid rgba(246, 229, 141, 0.3) !important;
        border-radius: 10px 10px 0 0 !important;
        color: #ffffff !important;
        font-weight: bold !important;
        padding: 10px 20px !important;
    }

    button[aria-selected="true"] {
        background-color: #e63946 !important;
        color: #ffffff !important;
        border-color: #ffeaa7 !important;
    }

    /* MÀU CHỮ VÀ KHUNG INPUT / SELECTBOX */
    h1, h2, h3, h4, h5, h6, p, label, span, div, .stMarkdown, [data-testid="stWidgetLabel"] {
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    h1 {
        color: #f6e58d !important;
        font-weight: 800 !important;
    }

    div[data-baseweb="input"], 
    div[data-baseweb="select"],
    [data-testid="stTextInput"] input, 
    [data-testid="stNumberInput"] input,
    div[data-baseweb="select"] > div {
        background-color: #060d17 !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    div[data-baseweb="input"], div[data-baseweb="select"] {
        border: 2px solid #f6e58d !important;
    }

    /* DROPDOWN MENU KHI XỔ XUỐNG */
    div[role="listbox"], ul[role="listbox"] {
        background-color: #060d17 !important;
        border: 1.5px solid #f6e58d !important;
        border-radius: 8px !important;
    }

    div[role="option"], li[role="option"] {
        background-color: #060d17 !important;
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    div[role="option"]:hover, li[role="option"]:hover,
    div[aria-selected="true"], li[aria-selected="true"] {
        background-color: #e63946 !important;
        color: #ffffff !important;
    }

    /* NÚT BẤM */
    [data-testid="stDownloadButton"] button, div.stButton > button {
        background: linear-gradient(90deg, #e63946 0%, #ff4d6d 100%) !important;
        color: #ffffff !important;
        font-weight: bold !important;
        border-radius: 18px !important;
        border: 1.5px solid #ffeaa7 !important;
        padding: 10px 24px !important;
    }

    [data-testid="stDownloadButton"] button *, div.stButton > button * {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    /* BẢNG DỮ LIỆU DATAFRAME */
    [data-testid="stDataFrame"] {
        background-color: #060d17 !important;
        border: 1px solid #f6e58d !important;
        border-radius: 10px !important;
    }
    [data-testid="stDataFrame"] div[role="gridcell"], [data-testid="stDataFrame"] div[role="columnheader"] {
        background-color: #0c1a2c !important;
        color: #ffffff !important;
    }

    /* THANH TOOLBAR DATAFRAME */
    [data-testid="stElementToolbar"],
    [data-testid="stDataFrameToolbar"],
    div[data-testid="stElementToolbar"] > div {
        background-color: #060d17 !important;
        border: 1px solid #f6e58d !important;
        border-radius: 8px !important;
    }

    [data-testid="stElementToolbar"] button,
    [data-testid="stDataFrameToolbar"] button {
        background-color: #060d17 !important;
        color: #f6e58d !important;
        border: none !important;
    }

    [data-testid="stElementToolbar"] svg,
    [data-testid="stDataFrameToolbar"] svg {
        fill: #f6e58d !important;
        color: #f6e58d !important;
    }

    /* MENU CÀI ĐẶT POPOVER (DẤU 3 CHẤM GÓC TRÊN BÊN PHẢI) */
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] > div,
    [data-testid="stMainMenu"] ul,
    div[data-baseweb="menu"] {
        background-color: #060d17 !important;
        border: 1.5px solid #f6e58d !important;
        border-radius: 12px !important;
        color: #ffffff !important;
    }

    div[data-baseweb="popover"] button,
    div[data-baseweb="popover"] li,
    div[data-baseweb="popover"] label,
    div[data-baseweb="popover"] span {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        font-weight: 600 !important;
    }

    div[data-baseweb="popover"] svg {
        fill: #f6e58d !important;
        color: #f6e58d !important;
    }

    /* ẨN NÚT CHỌN GIAO DIỆN SÁNG/TỐI (SYSTEM / LIGHT / DARK) */
    div[data-baseweb="segmented-control"],
    [data-testid="stMainMenu"] ul li:has(div[data-baseweb="segmented-control"]) {
        display: none !important;
    }

    /* Ẩn nút GitHub thừa */
    a[href*="github"], [data-testid="stHeaderActionElements"] > a, button[title*="Edit"] {
        display: none !important;
    }
    </style>
"""
st.markdown(mid_autumn_tabs_css, unsafe_allow_html=True)

st.title("🥮 Multi-Source Auto Scraper 🌕")
st.caption("✨ Hệ thống cào Lead đa kênh chuyên nghiệp: Mã Số Thuế & Google Maps")

# HÀM CHUẨN HÓA SỐ ĐIỆN THOẠI CHUYỂN +84 THÀNH ĐẦU 0
def normalize_phone_number(raw_phone):
    if not raw_phone or raw_phone == "Không có":
        return "Không có"
    digits = re.sub(r"[^\d]", "", raw_phone)
    if digits.startswith("84"):
        digits = "0" + digits[2:]
    elif not digits.startswith("0") and len(digits) >= 9:
        digits = "0" + digits
    if len(digits) in [10, 11]:
        return digits
    return raw_phone

# TẠO 2 TAB CHỨC NĂNG
tab1, tab2 = st.tabs(["🏛️ Cào Mã Số Thuế (MaSoThue)", "📍 Cào Google Maps Lead"])

# ==========================================
# TAB 1: MASOTHUE.COM
# ==========================================
with tab1:
    st.subheader("Tra cứu thông tin từ masothue.com")
    url_input = st.text_input(
        "Dán URL cần cào:",
        value="https://masothue.com/tra-cuu-ma-so-thue-theo-tinh/ho-chi-minh-23",
        key="mst_url",
    )
    
    col_m1, col_m2 = st.columns([3, 1], vertical_alignment="bottom")
    with col_m1:
        max_pages = st.number_input(
            "Số lượng trang muốn quét (Tối đa 10 trang):",
            min_value=1,
            max_value=10,
            value=3,
            key="mst_pages",
        )
    with col_m2:
        if st.button("🔄 Reset lịch sử cào MST", key="reset_mst", use_container_width=True):
            st.session_state.history_mst_links.clear()
            st.success("Đã xóa bộ nhớ tạm!")

    start_mst_button = st.button("🚀 Bắt đầu cào Mã Số Thuế", type="primary", key="btn_mst")

    def clean_text(text):
        return re.sub(r"\s+", " ", text).strip() if text else "N/A"

    def extract_phone_accurate(soup):
        system_hotlines = ["0169764112", "039764112", "0901234567"]
        main_table = soup.select_one("table.table-taxinfo, div.tax-listing, main")
        target_area = main_table if main_table else soup

        for row in target_area.find_all(["tr", "li", "p", "div"]):
            row_text = row.get_text()
            if any(k in row_text for k in ["Điện thoại", "SĐT", "Telephone", "Mobile"]):
                cols = row.find_all("td")
                phone_text = cols[-1].get_text() if cols else row_text
                raw_digits = re.sub(r"[^\d+]", "", phone_text)
                match = re.search(r"(?:\+84|0)\d{8,10}\b", raw_digits)
                if match:
                    phone_number = normalize_phone_number(match.group(0))
                    if phone_number not in system_hotlines:
                        return phone_number
        return "Không có"

    if start_mst_button and url_input:
        all_data = []
        status_text = st.empty()

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    viewport={"width": 1920, "height": 1080},
                )
                page = context.new_page()
                page.route("**/*.{png,jpg,jpeg,svg,woff,woff2,mp4}", lambda route: route.abort())

                current_url = url_input

                for page_idx in range(1, max_pages + 1):
                    status_text.text(f"⏳ Đang tải trang {page_idx}/{max_pages}: {current_url}")
                    try:
                        page.goto(current_url, wait_until="networkidle", timeout=45000)
                        time.sleep(2)
                    except Exception:
                        st.error(f"Không thể mở trang {page_idx}.")
                        break

                    soup = BeautifulSoup(page.content(), "html.parser")
                    detail_links = []
                    anchors = soup.select("div.tax-listing h3 a, div.table-tax-listing h3 a, main h3 a")

                    for a_tag in anchors:
                        href = a_tag.get("href", "")
                        full_url = f"https://masothue.com{href}" if href.startswith("/") else href
                        if (
                            "masothue.com/" in full_url 
                            and re.search(r"/\d{9,13}", full_url) 
                            and full_url not in st.session_state.history_mst_links
                        ):
                            detail_links.append(full_url)
                            st.session_state.history_mst_links.add(full_url)

                    if not detail_links:
                        st.warning(f"Trang {page_idx} không tìm thấy đơn vị mới nào (hoặc đã cào trước đó).")
                        break

                    for idx, link in enumerate(detail_links, 1):
                        status_text.text(f"⚡ MST Trang {page_idx}/{max_pages} - Đang kiểm tra SĐT [{idx}/{len(detail_links)}]")
                        try:
                            page.goto(link, wait_until="domcontentloaded", timeout=30000)
                            time.sleep(random.uniform(1.0, 1.8))
                            detail_soup = BeautifulSoup(page.content(), "html.parser")

                            phone = extract_phone_accurate(detail_soup)
                            if phone == "Không có" or not phone:
                                continue

                            title = detail_soup.find(["h1", "h2"])
                            entity_name = clean_text(title.get_text()) if title else "N/A"

                            tax_code, address, representative, entity_status = "N/A", "N/A", "N/A", "Không xác định"
                            for row in detail_soup.find_all(["tr", "li"]):
                                text = row.get_text()
                                cols = row.find_all("td")
                                if ("Mã số thuế" in text or "Mã số" in text) and cols:
                                    tax_code = clean_text(cols[-1].get_text())
                                elif "Địa chỉ" in text and cols:
                                    address = clean_text(cols[-1].get_text())
                                elif any(k in text for k in ["Người đại diện", "Chủ hộ", "Đại diện pháp luật"]) and cols:
                                    representative = clean_text(cols[-1].get_text())
                                elif any(k in text for k in ["Trạng thái", "Tình trạng"]) and cols:
                                    entity_status = clean_text(cols[-1].get_text())

                            all_data.append({
                                "Tên Đơn Vị": entity_name,
                                "Mã Số Thuế": tax_code,
                                "Số Điện Thoại": phone,
                                "Trạng Thái": entity_status,
                                "Người Đại Diện / Chủ Hộ": representative,
                                "Địa Chỉ": address,
                                "Link Chi Tiết": link,
                            })
                        except Exception:
                            continue

                    current_url = f"{url_input}&page={page_idx + 1}" if "?" in url_input else f"{url_input}?page={page_idx + 1}"

                context.close()
                browser.close()

        except Exception:
            st.error("Lỗi kết nối hệ thống.")

        status_text.text("✅ Hoàn tất quá trình cào dữ liệu Mã Số Thuế!")
        if all_data:
            st.success(f"🎉 Đã thu thập được {len(all_data)} đơn vị mới có SĐT chuẩn!")
            df = pd.DataFrame(all_data)
            st.dataframe(df)

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Mã_Số_Thuế")
            
            # Tên file kèm Ngày Giờ để không bị ghi đè gây hỏng file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name_mst = f"masothue_{timestamp}.xlsx"

            st.download_button(
                label="📥 Tải file Excel Mã Số Thuế",
                data=buffer.getvalue(),
                file_name=file_name_mst,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


# ==========================================
# TAB 2: GOOGLE MAPS
# ==========================================
with tab2:
    st.subheader("Tìm kiếm Lead Doanh Nghiệp / Cửa Hàng trên Google Maps")

    district_list = [
        "Quận 1, TP.HCM", "Quận 3, TP.HCM", "Quận 4, TP.HCM", "Quận 5, TP.HCM", 
        "Quận 6, TP.HCM", "Quận 7, TP.HCM", "Quận 8, TP.HCM", "Quận 10, TP.HCM", 
        "Quận 11, TP.HCM", "Quận 12, TP.HCM", "TP. Thủ Đức, TP.HCM", "Quận Bình Thạnh, TP.HCM", 
        "Quận Gò Vấp, TP.HCM", "Quận Phú Nhuận, TP.HCM", "Quận Tân Bình, TP.HCM", 
        "Quận Tân Phú, TP.HCM", "Quận Bình Tân, TP.HCM", "Huyện Bình Chánh, TP.HCM", 
        "Huyện Hóc Môn, TP.HCM", "Huyện Củ Chi, TP.HCM", "Huyện Nhà Bè, TP.HCM", 
        "Huyện Cần Giờ, TP.HCM", "Khu vực khác (Tự nhập)"
    ]

    col_g1, col_g2 = st.columns([1.5, 1])
    with col_g1:
        gmaps_keyword = st.text_input(
            "1. Nhập từ khóa ngành nghề (VD: Quán cafe, Spa, Ô tô):",
            value="Quán cafe",
            key="gmaps_key",
        )
    with col_g2:
        selected_district = st.selectbox(
            "2. Chọn Quận/Huyện khu vực:",
            options=district_list,
            index=0,
            key="gmaps_dist_select"
        )

    if selected_district == "Khu vực khác (Tự nhập)":
        gmaps_location = st.text_input(
            "Nhập tên Tỉnh/Thành phố/Khu vực tự do:",
            value="Hà Nội",
            key="gmaps_loc_custom"
        )
    else:
        gmaps_location = selected_district

    col_gm1, col_gm2 = st.columns([3, 1], vertical_alignment="bottom")
    with col_gm1:
        gmaps_max_results = st.number_input(
            "Số lượng địa điểm muốn quét thêm (Tối đa 30):",
            min_value=5,
            max_value=30,
            value=5,
            key="gmaps_max",
        )
    with col_gm2:
        if st.button("🔄 Reset lịch sử cào Maps", key="reset_gmaps", use_container_width=True):
            st.session_state.history_gmaps_urls.clear()
            st.success("Đã xóa lịch sử trùng Google Maps!")

    start_gmaps_button = st.button("🚀 Bắt đầu cào Google Maps", type="primary", key="btn_gmaps")

    if start_gmaps_button and gmaps_keyword:
        gmaps_data = []
        status_gmaps = st.empty()
        search_query = f"{gmaps_keyword} {gmaps_location}".strip()
        encoded_query = urllib.parse.quote(search_query)
        maps_url = f"https://www.google.com/maps/search/{encoded_query}"

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox", 
                        "--disable-setuid-sandbox", 
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled"
                    ],
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    locale="vi-VN",
                )
                page = context.new_page()

                status_gmaps.text(f"⏳ Đang mở Google Maps tìm kiếm: '{search_query}'...")
                page.goto(maps_url, wait_until="domcontentloaded", timeout=45000)
                time.sleep(3)

                scroll_times = max(3, int(len(st.session_state.history_gmaps_urls) / 3) + 3)
                for _ in range(scroll_times):
                    page.mouse.wheel(0, 3000)
                    time.sleep(1.2)

                items = page.query_selector_all('a[href*="/maps/place/"]')
                unique_urls = []
                for item in items:
                    href = item.get_attribute("href")
                    if href and href not in st.session_state.history_gmaps_urls:
                        unique_urls.append(href)
                        st.session_state.history_gmaps_urls.add(href)
                    if len(unique_urls) >= gmaps_max_results:
                        break

                if not unique_urls:
                    st.warning(f"⚠️ Không tìm thấy địa điểm MỚI nào với từ khóa '{search_query}'. Bấm 'Reset lịch sử cào Maps' để cào lại từ đầu.")
                else:
                    st.write(f"✨ Thu thập được **{len(unique_urls)}** địa điểm MỚI chưa trùng tại **{gmaps_location}**.")

                    for idx, place_url in enumerate(unique_urls, 1):
                        status_gmaps.text(f"⚡ Google Maps [{idx}/{len(unique_urls)}]: Đang trích xuất thông tin...")
                        try:
                            page.goto(place_url, wait_until="domcontentloaded", timeout=30000)
                            time.sleep(2)

                            place_soup = BeautifulSoup(page.content(), "html.parser")
                            
                            name_tag = place_soup.find("h1")
                            place_name = clean_text(name_tag.get_text()) if name_tag else "N/A"

                            phone_number = "Không có"
                            address = "N/A"
                            website = "N/A"
                            rating = "N/A"

                            rating_tag = place_soup.select_one("span.ceRate, div.F7beeb, span[aria-label*='sao']")
                            if rating_tag:
                                rating = clean_text(rating_tag.get_text())

                            for btn in place_soup.select("button[data-item-id], a[data-item-id]"):
                                item_id = btn.get("data-item-id", "")
                                btn_text = clean_text(btn.get_text())

                                if "phone:" in item_id or "tel:" in item_id:
                                    phone_match = re.search(r"(?:\+84|0)\d{8,10}\b", re.sub(r"[^\d+]", "", btn_text))
                                    if phone_match:
                                        phone_number = normalize_phone_number(phone_match.group(0))
                                elif "address" in item_id:
                                    address = btn_text
                                elif "authority" in item_id:
                                    website = btn_text

                            if phone_number == "Không có":
                                match = re.search(r"(?:\+84|0)\d{8,10}\b", re.sub(r"[^\d+]", "", place_soup.get_text()))
                                if match:
                                    phone_number = normalize_phone_number(match.group(0))

                            gmaps_data.append({
                                "Tên Địa Điểm": place_name,
                                "Số Điện Thoại": phone_number,
                                "Địa Chỉ": address,
                                "Khu Vực": gmaps_location,
                                "Đánh Giá (Rating)": rating,
                                "Website": website,
                                "Link Google Maps": place_url,
                            })

                        except Exception:
                            continue

                context.close()
                browser.close()

        except Exception as e:
            st.error(f"Lỗi hệ thống: {str(e)}")

        status_gmaps.text("✅ Hoàn tất quá trình cào Google Maps!")
        
        if gmaps_data:
            st.success(f"🎉 Đã thu thập thành công {len(gmaps_data)} địa điểm mới!")
            df_gmaps = pd.DataFrame(gmaps_data)
            st.dataframe(df_gmaps)

            buffer_gmaps = io.BytesIO()
            with pd.ExcelWriter(buffer_gmaps, engine="openpyxl") as writer:
                df_gmaps.to_excel(writer, index=False, sheet_name="Google_Maps")

            # Tên file kèm Ngày Giờ
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name_gmaps = f"gmaps_{timestamp}.xlsx"

            st.download_button(
                label="📥 Tải file Excel Google Maps",
                data=buffer_gmaps.getvalue(),
                file_name=file_name_gmaps,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
