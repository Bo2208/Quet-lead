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

st.title("⚡ Tool Auto Scraper - Vượt Bảo Mật Cloudflare")

url_input = st.text_input(
    "Dán URL cần cào:",
    value="",
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
            
            # Khởi tạo Context với User-Agent chuẩn desktop
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                extra_http_headers={
                    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                }
            )
            page = context.new_page()

            # Chặn tải các tài nguyên nặng không cần thiết (hình ảnh, media, font)
            page.route(
                "**/*.{png,jpg,jpeg,svg,woff,woff2,mp4}", lambda route: route.abort()
            )

            current_url = url_input

            for page_idx in range(1, max_pages + 1):
                status_text.text(
                    f"⏳ Đang tải trang {page_idx}/{max_pages}: {current_url}"
                )

                try:
                    # Chuyển trang kèm wait_until="networkidle" để đợi Cloudflare giải xong challenge
                    page.goto(
                        current_url, wait_until="networkidle", timeout=45000
                    )
                    time.sleep(2)  # Trễ cố định 2s cho trang chính

                    # KIỂM TRA BẢO MẬT CLOUDFLARE
                    page_content = page.content()
                    if "Just a moment..." in page.title() or "cf-mitigation" in page_content:
                        status_text.text(f"🛡️ Phát hiện Cloudflare ở trang {page_idx}, đang tự động chờ xác minh...")
                        time.sleep(6)  # Đợi Cloudflare tự vượt qua challenge
                        page_content = page.content()

                except Exception as e:
                    st.error(f"Không thể mở trang {page_idx} (Có thể bị ngắt kết nối do bảo mật).")
                    break

                soup = BeautifulSoup(page.content(), "html.parser")

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
                    st.warning(
                        f"Trang {page_idx} không lấy được danh sách công ty (Có thể đã dính captcha xác minh)."
                    )
                    break

                st.write(
                    f" Tìm thấy {len(detail_links)} công ty ở trang {page_idx}."
                )

                for idx, link in enumerate(detail_links, 1):
                    status_text.text(
                        f"⚡ Trang {page_idx}/{max_pages} - Đang cào dữ liệu [{idx}/{len(detail_links)}]: {link}"
                    )

                    try:
                        page.goto(
                            link, wait_until="domcontentloaded", timeout=30000
                        )
                        
                        # Giảm tần suất bị chặn bằng khoảng trễ ngẫu nhiên (1s - 2s)
                        time.sleep(random.uniform(1.0, 2.0))

                        detail_soup = BeautifulSoup(page.content(), "html.parser")

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

            context.close()
            browser.close()

    except Exception as err:
        st.error("Hệ thống gián đoạn do Cloudflare chặn IP tạm thời. Vui lòng thử lại sau 2 - 3 phút!")

    status_text.text("✅ Hoàn tất quá trình cào dữ liệu!")

    if all_data:
        st.success(f"🎉 Đã thu thập được {len(all_data)} công ty có SĐT!")
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
