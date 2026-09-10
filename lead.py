import io
import re
import time
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from pyvirtualdisplay import Display
from seleniumbase import Driver

st.set_page_config(page_title="Tool Auto Scraper - Super Fast", page_icon="⚡")

# Chèn đoạn này ngay sau st.set_page_config(...)
hide_github_and_edit = """
    <style>
    /* 1. Triệt hạ nút GitHub triệt để bằng mọi thuộc tính liên quan */
    a[href*="github"],
    a[href*="github.com"],
    [data-testid="stHeader"] a[href*="github"],
    [data-testid="stAppHeader"] a[href*="github"],
    div[data-testid="stHeaderActionElements"] > a,
    div[data-testid="stToolbar"] a[href*="github"] {
        display: none !important;
        visibility: hidden !important;
        width: 0px !important;
        height: 0px !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }

    /* 2. Ẩn nút Edit (Cây bút) */
    button[title*="Edit"],
    button[title*="Studio"],
    button[aria-label*="Edit"],
    [data-testid="stHeader"] button[title*="Edit"] {
        display: none !important;
        visibility: hidden !important;
    }
    </style>
"""
st.markdown(hide_github_and_edit, unsafe_allow_html=True)

st.title("⚡ Tool Auto Scraper - Cào Dữ Liệu Siêu Tốc")

url_input = st.text_input(
    "Dán URL cần cào:",
    value="",
)
max_pages = st.number_input(
    "Số lượng trang muốn quét:", min_value=1, max_value=50, value=4
)
start_button = st.button("🚀 Bắt đầu cào dữ liệu", type="primary")


def clean_text(text):
    return re.sub(r"\s+", " ", text).strip() if text else "N/A"


def extract_phone(soup):
    for row in soup.find_all(["tr", "li", "div"]):
        row_text = row.get_text()
        if any(k in row_text for k in ["Điện thoại", "SĐT", "Telephone"]):
            match = re.search(
                r"(?:\+84|0)\d{9,10}\b", re.sub(r"[^\d+]", "", row_text)
            )
            if match:
                return match.group(0)
    return "Không có"


if start_button and url_input:
    all_data = []
    visited_links = set()
    status_text = st.empty()

    # Khởi tạo Màn hình ảo
    display = Display(visible=0, size=(1920, 1080))
    display.start()

    # Khởi tạo Driver tối ưu tốc độ (Chặn tải ảnh, font, media để load trang siêu nhanh)
    driver = Driver(
        uc=True,
        headless=False,
        chromium_arg="--blink-settings=imagesEnabled=false --disable-remote-fonts --disable-speech-api",
    )

    try:
        current_url = url_input

        for page_idx in range(1, max_pages + 1):
            status_text.text(
                f"⚡ Đang tải nhanh trang {page_idx}/{max_pages}: {current_url}"
            )

            driver.uc_open_with_reconnect(current_url, reconnect_time=3)
            time.sleep(1)  # Giảm thời gian chờ xuống 1s

            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")

            detail_links = []
            anchors = soup.select(
                "div.tax-listing h3 a, div.table-tax-listing h3 a"
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
                st.info(
                    f"Không tìm thấy danh sách doanh nghiệp ở trang {page_idx}."
                )
                break

            st.write(
                f" Tìm thấy {len(detail_links)} công ty ở trang {page_idx}."
            )

            # Quét từng trang chi tiết
            for idx, link in enumerate(detail_links, 1):
                status_text.text(
                    f"⚡ Trang {page_idx}/{max_pages} - Đang kiểm tra SĐT [{idx}/{len(detail_links)}]: {link}"
                )

                try:
                    driver.uc_open_with_reconnect(link, reconnect_time=2)
                    time.sleep(0.5)  # Giảm trễ giữa các lượt cào xuống 0.5s

                    detail_soup = BeautifulSoup(
                        driver.page_source, "html.parser"
                    )

                    phone = extract_phone(detail_soup)
                    if phone == "Không có" or not phone:
                        continue

                    title = detail_soup.find("h1")
                    company_name = (
                        clean_text(title.get_text()) if title else "N/A"
                    )

                    tax_code, address, representative = "N/A", "N/A", "N/A"
                    for row in detail_soup.find_all("tr"):
                        text = row.get_text()
                        cols = row.find_all("td")
                        if "Mã số thuế" in text and cols:
                            tax_code = clean_text(cols[-1].get_text())
                        elif "Địa chỉ" in text and cols:
                            address = clean_text(cols[-1].get_text())
                        elif "Người đại diện" in text and cols:
                            representative = clean_text(cols[-1].get_text())

                    all_data.append(
                        {
                            "Tên Công Ty": company_name,
                            "Mã Số Thuế": tax_code,
                            "Số Điện Thoại": phone,
                            "Người Đại Diện": representative,
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

    finally:
        driver.quit()
        display.stop()

    status_text.text("✅ Hoàn tất quá trình cào dữ liệu!")

    if all_data:
        st.success(f"🎉 Đã thu thập xong {len(all_data)} công ty có SĐT!")
        df = pd.DataFrame(all_data)
        st.dataframe(df)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Danh_Sach")

        st.download_button(
            label="📥 Tải file Excel",
            data=buffer.getvalue(),
            file_name="danh_sach_doanh_nghiep.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
