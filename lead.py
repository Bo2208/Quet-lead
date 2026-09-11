import io
import random
import re
import subprocess
import time
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# 1. Tự động kiểm tra Chromium trên Server
try:
    subprocess.run(["playwright", "install", "chromium"], check=True)
except Exception:
    pass

# 2. CSS ẩn nút Header Streamlit
hide_github_and_edit = """
    <style>
    a[href*="github"],
    [data-testid="stHeaderActionElements"] > a,
    button[title*="Edit"],
    button[title*="Studio"],
    button[aria-label*="Edit"] {
        display: none !important;
    }
    </style>
"""
st.markdown(hide_github_and_edit, unsafe_allow_html=True)

st.title("⚡ Tool Auto Scraper - Chuẩn SĐT Doanh Nghiệp")

url_input = st.text_input(
    "Dán URL cần cào:",
    value="https://masothue.com/tra-cuu-ma-so-thue-theo-tinh/ho-chi-minh-23",
)

max_pages = st.number_input(
    "Số lượng trang muốn quét (Tối đa 10 trang/lượt):",
    min_value=1,
    max_value=10,
    value=4,
)
start_button = st.button("🚀 Bắt đầu cào dữ liệu", type="primary")


def clean_text(text):
    return re.sub(r"\s+", " ", text).strip() if text else "N/A"


def extract_phone_accurate(soup):
    """
    Chỉ tìm SĐT trong bảng thông tin chi tiết của doanh nghiệp.
    Loại bỏ SĐT hotline hệ thống/footer trùng lặp.
    """
    # Số hotline/hỗ trợ của trang cần loại bỏ
    system_hotlines = ["0169764112", "039764112", "0901234567"]
    
    # 1. Tìm ưu tiên trong bảng thông tin chi tiết (table-taxinfo)
    main_table = soup.select_one("table.table-taxinfo, div.tax-listing")
    target_area = main_table if main_table else soup

    for row in target_area.find_all("tr"):
        row_text = row.get_text()
        if any(k in row_text for k in ["Điện thoại", "SĐT", "Telephone", "Mobile"]):
            # Lấy ô chứa thông tin (thường là td cuối)
            cols = row.find_all("td")
            phone_text = cols[-1].get_text() if cols else row_text
            
            # Trích xuất chuỗi số
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
                            f"🛡️ Phát hiện Cloudflare ở trang {page_idx}, đang tự động chờ..."
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
                        f"Trang {page_idx} không tìm thấy đối tượng nào."
                    )
                    break

                st.write(
                    f" Tìm thấy {len(detail_links)} đối tượng ở trang {page_idx}."
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

                        # Bỏ qua nếu không có SĐT chính xác
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
        st.error("Hệ thống gián đoạn. Vui lòng thử lại sau 2 phút!")

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
            label="📥 Tải file Excel",
            data=buffer.getvalue(),
            file_name="danh_sach_don_vi.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
