import io
import random
import re
import subprocess
import time
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# 1. Kiểm tra Chromium trên Server
try:
    subprocess.run(["playwright", "install", "chromium"], check=True)
except Exception:
    pass

# 2. CẤU HÌNH TRANG & CSS KHẮC PHỤC MÀU CHỮ Ô INPUT
st.set_page_config(
    page_title="Tool Scraper - Lễ Hội Trung Thu",
    page_icon="🌕",
    layout="wide",
)

mid_autumn_contrast_css = """
    <style>
    /* 1. NỀN TỔNG THỂ ĐÊM TRUNG THU */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background: linear-gradient(180deg, #090e17 0%, #0f1c2e 60%, #16273e 100%) !important;
        position: relative;
        overflow-x: hidden;
    }
    
    /* 2. MẶT TRĂNG REALISTIC GÓC TRÊN BÊN PHẢI */
    [data-testid="stAppViewContainer"]::before {
        content: "";
        position: fixed;
        top: 25px;
        right: 45px;
        width: 90px;
        height: 90px;
        border-radius: 50%;
        background-color: #f6e58d;
        background-image: 
            radial-gradient(circle at 30% 30%, rgba(220, 190, 100, 0.4) 12%, transparent 13%),
            radial-gradient(circle at 65% 45%, rgba(210, 180, 90, 0.35) 18%, transparent 19%),
            radial-gradient(circle at 45% 70%, rgba(220, 190, 100, 0.3) 10%, transparent 11%),
            radial-gradient(circle at 75% 75%, rgba(200, 170, 80, 0.25) 8%, transparent 9%);
        box-shadow: 
            inset -10px -8px 15px rgba(180, 140, 40, 0.5),
            0 0 25px rgba(246, 229, 141, 0.6),
            0 0 60px rgba(246, 229, 141, 0.25);
        z-index: 1 !important;
        pointer-events: none;
    }

    /* 3. DẢI ĐÈN LỒNG GÓC TRÁI */
    .lantern-group {
        position: fixed;
        top: 20px;
        left: 45px;
        font-size: 36px;
        z-index: 10;
        pointer-events: none;
        animation: lanternSway 4s ease-in-out infinite alternate;
        filter: drop-shadow(0 0 8px rgba(230, 57, 70, 0.8));
    }

    @keyframes lanternSway {
        0% { transform: rotate(-4deg); }
        100% { transform: rotate(4deg); }
    }

    /* 4. KHUNG GIAO DIỆN CHÍNH */
    [data-testid="stMainBlockContainer"] {
        background-color: rgba(15, 28, 46, 0.88) !important;
        border: 1px solid rgba(246, 229, 141, 0.35) !important;
        border-radius: 16px !important;
        padding: 30px !important;
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.6) !important;
        backdrop-filter: blur(10px) !important;
        margin-top: 20px !important;
    }

    /* 5. TỐI ƯU MÀU NHÃN CHỮ NỔI BẬT */
    h1, h2, h3, h4, h5, h6, p, label, span, div, .stMarkdown, [data-testid="stWidgetLabel"] {
        color: #ffffff !important;
        font-weight: 600 !important;
        text-shadow: 0px 1px 2px rgba(0, 0, 0, 0.9) !important;
    }

    h1 {
        color: #f6e58d !important;
        font-size: 2.1rem !important;
        font-weight: 800 !important;
        text-shadow: 0 0 10px rgba(246, 229, 141, 0.4) !important;
    }

    /* 6. FIX FIX FIX: TỐI TỐI KHUNG INPUT & ĐỔI CHỮ TRẮNG TINH NÉT CĂNG */
    div[data-baseweb="input"], 
    div[data-baseweb="base-input"], 
    div[data-baseweb="spinbutton"],
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input {
        background-color: #060d17 !important; /* Nền tối hẳn */
        color: #ffffff !important;             /* Chữ trắng tinh */
        border-radius: 8px !important;
        font-size: 1rem !important;
        font-weight: bold !important;
        -webkit-text-fill-color: #ffffff !important; /* Ép màu chữ rõ trên mọi trình duyệt */
    }

    div[data-baseweb="input"] {
        border: 2px solid #f6e58d !important; /* Viền vàng trăng rực rỡ */
    }

    /* 7. BẢNG DỮ LIỆU DATAFRAME */
    [data-testid="stDataFrame"], div[role="grid"] {
        background-color: #060d17 !important;
        border: 1px solid rgba(246, 229, 141, 0.4) !important;
        border-radius: 8px !important;
    }

    /* 8. NÚT BẤM ĐÈN LỒNG NỔI BẬT */
    div.stButton > button {
        background: linear-gradient(90deg, #e63946 0%, #ff4d6d 100%) !important;
        color: #ffffff !important;
        font-size: 1rem !important;
        font-weight: bold !important;
        border-radius: 18px !important;
        border: 1px solid #ffeaa7 !important;
        box-shadow: 0 4px 15px rgba(230, 57, 70, 0.5) !important;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(246, 229, 141, 0.7) !important;
    }

    /* Ẩn bớt nút thừa Streamlit */
    a[href*="github"],
    [data-testid="stHeaderActionElements"] > a,
    button[title*="Edit"],
    button[title*="Studio"],
    button[aria-label*="Edit"] {
        display: none !important;
    }
    </style>
"""
st.markdown(mid_autumn_contrast_css, unsafe_allow_html=True)

# Đèn lồng trang trí
st.markdown('<div class="lantern-group">🏮🏮🏮</div>', unsafe_allow_html=True)

# Banner & Tiêu đề
st.title("🥮 Tool Auto Scraper - Hội Mùa Trăng Rằm 🌕")
st.caption("✨ Giao diện Trung Thu chuyên nghiệp - Cào Data siêu tốc & không bỏ sót Lead!")

url_input = st.text_input(
    "Dán URL cần cào:",
    value="",
)

max_pages = st.number_input(
    "Số lượng trang muốn quét (Tối đa 10 trang/lượt):",
    min_value=1,
    max_value=10,
    value=1,
)
start_button = st.button("🚀 Bắt đầu cào Data ngay", type="primary")


def clean_text(text):
    return re.sub(r"\s+", " ", text).strip() if text else "N/A"


def extract_phone_accurate(soup):
    system_hotlines = ["0169764112", "039764112", "0901234567"]
    main_table = soup.select_one("table.table-taxinfo, div.tax-listing")
    target_area = main_table if main_table else soup

    for row in target_area.find_all("tr"):
        row_text = row.get_text()
        if any(k in row_text for k in ["Điện thoại", "SĐT", "Telephone", "Mobile"]):
            cols = row.find_all("td")
            phone_text = cols[-1].get_text() if cols else row_text
            raw_digits = re.sub(r"[^\d+]", "", phone_text)
            match = re.search(r"(?:\+84|0)\d{8,10}\b", raw_digits)
            if match:
                phone_number = match.group(0)
                if phone_number not in system_hotlines:
                    return phone_number
    return "Không có"


if start_button and url_input:
    all_data = []
    visited_links = set()
    status_text = st.empty()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                extra_http_headers={
                    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                },
            )
            page = context.new_page()

            page.route(
                "**/*.{png,jpg,jpeg,svg,woff,woff2,mp4}",
                lambda route: route.abort(),
            )

            current_url = url_input

            for page_idx in range(1, max_pages + 1):
                status_text.text(
                    f"⏳ Đang tải trang {page_idx}/{max_pages}: {current_url}"
                )

                try:
                    page.goto(
                        current_url, wait_until="networkidle", timeout=45000
                    )
                    time.sleep(2)

                    page_content = page.content()
                    if (
                        "Just a moment..." in page.title()
                        or "cf-mitigation" in page_content
                    ):
                        status_text.text(
                            f"🛡️ Gặp Cloudflare ở trang {page_idx}, đang tự động chờ 6s..."
                        )
                        time.sleep(6)

                except Exception:
                    st.error(f"Không thể mở trang {page_idx}.")
                    break

                soup = BeautifulSoup(page.content(), "html.parser")

                detail_links = []
                anchors = soup.select(
                    "div.tax-listing h3 a, div.table-tax-listing h3 a, table.table-taxinfo h3 a"
                )
                if not anchors:
                    anchors = soup.select("main a[href]")

                for a_tag in anchors:
                    href = a_tag.get("href", "")
                    full_url = (
                        f"https://masothue.com{href}"
                        if href.startswith("/")
                        else href
                    )
                    if (
                        "masothue.com/" in full_url
                        and re.search(r"/\d{9,13}", full_url)
                        and full_url not in visited_links
                    ):
                        detail_links.append(full_url)
                        visited_links.add(full_url)

                if not detail_links:
                    st.warning(
                        f"Trang {page_idx} không tìm thấy đơn vị nào."
                    )
                    break

                st.write(
                    f"✨ Tìm thấy {len(detail_links)} công ty/hộ kinh doanh ở trang {page_idx}."
                )

                for idx, link in enumerate(detail_links, 1):
                    status_text.text(
                        f"⚡ Trang {page_idx}/{max_pages} - Đang kiểm tra SĐT [{idx}/{len(detail_links)}]: {link}"
                    )

                    try:
                        page.goto(
                            link, wait_until="domcontentloaded", timeout=30000
                        )
                        time.sleep(random.uniform(1.0, 2.0))

                        detail_soup = BeautifulSoup(
                            page.content(), "html.parser"
                        )

                        phone = extract_phone_accurate(detail_soup)
                        if phone == "Không có" or not phone:
                            continue

                        title = detail_soup.find("h1")
                        entity_name = (
                            clean_text(title.get_text()) if title else "N/A"
                        )

                        tax_code, address, representative, entity_status = (
                            "N/A",
                            "N/A",
                            "N/A",
                            "Không xác định",
                        )
                        for row in detail_soup.find_all("tr"):
                            text = row.get_text()
                            cols = row.find_all("td")
                            if ("Mã số thuế" in text or "Mã số" in text) and cols:
                                tax_code = clean_text(cols[-1].get_text())
                            elif "Địa chỉ" in text and cols:
                                address = clean_text(cols[-1].get_text())
                            elif (
                                any(
                                    k in text
                                    for k in [
                                        "Người đại diện",
                                        "Chủ hộ",
                                        "Đại diện pháp luật",
                                    ]
                                )
                                and cols
                            ):
                                representative = clean_text(cols[-1].get_text())
                            elif (
                                any(
                                    k in text
                                    for k in ["Trạng thái", "Tình trạng"]
                                )
                                and cols
                            ):
                                entity_status = clean_text(cols[-1].get_text())

                        all_data.append(
                            {
                                "Tên Đơn Vị": entity_name,
                                "Mã Số Thuế": tax_code,
                                "Số Điện Thoại": phone,
                                "Trạng Thái": entity_status,
                                "Người Đại Diện / Chủ Hộ": representative,
                                "Địa Chỉ": address,
                                "Link Chi Tiết": link,
                            }
                        )
                    except Exception:
                        continue

                current_url = (
                    f"{url_input}&page={page_idx + 1}"
                    if "?" in url_input
                    else f"{url_input}?page={page_idx + 1}"
                )

            context.close()
            browser.close()

    except Exception:
        st.error("Hệ thống gián đoạn. Vui lòng thử lại sau ít phút!")

    status_text.text("✅ Hoàn tất quá trình cào dữ liệu!")

    if all_data:
        st.success(
            f"🎉 Đã thu thập được {len(all_data)} đơn vị có SĐT chuẩn!"
        )
        df = pd.DataFrame(all_data)
        st.dataframe(df)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Danh_Sach")

        st.download_button(
            label="📥 Tải file Excel về máy",
            data=buffer.getvalue(),
            file_name="danh_sach_don_vi.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
