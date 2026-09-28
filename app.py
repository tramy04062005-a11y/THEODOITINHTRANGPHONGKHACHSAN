import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd

# =========================================================
# CẤU HÌNH APP
# =========================================================

st.set_page_config(
    page_title="Melia Vinpearl Phú Quốc - Quản lý phòng",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_NAME = "melia_hotel.db"

# =========================================================
# DATABASE
# =========================================================

def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT UNIQUE NOT NULL,
            villa_type TEXT NOT NULL,
            building TEXT,
            floor TEXT,
            status TEXT NOT NULL DEFAULT 'Vacant Dirty',
            guest_name TEXT,
            hk_note TEXT,
            updated_by TEXT,
            updated_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT NOT NULL,
            old_status TEXT,
            new_status TEXT,
            note TEXT,
            updated_by TEXT,
            updated_at TEXT
        )
    """)

    conn.commit()

    # Tạo dữ liệu mẫu nếu database chưa có phòng
    cursor.execute("SELECT COUNT(*) FROM rooms")
    count = cursor.fetchone()[0]

    if count == 0:
        sample_rooms = []

        # Dữ liệu mẫu minh họa
        for i in range(1, 31):
            room_number = f"V{i:03d}"

            if i <= 10:
                villa_type = "One Bedroom Lake View Private Pool"
            elif i <= 20:
                villa_type = "Two-Bedroom Lake View Private Pool"
            else:
                villa_type = "The Level"

            sample_rooms.append((
                room_number,
                villa_type,
                "Villa Area",
                "1",
                "Vacant Clean",
                "",
                "",
                "System",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

        cursor.executemany("""
            INSERT INTO rooms (
                room_number,
                villa_type,
                building,
                floor,
                status,
                guest_name,
                hk_note,
                updated_by,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_rooms)

        conn.commit()

    conn.close()


# =========================================================
# HÀM DATABASE
# =========================================================

def get_rooms():
    conn = get_connection()

    df = pd.read_sql_query("""
        SELECT
            id,
            room_number,
            villa_type,
            building,
            floor,
            status,
            guest_name,
            hk_note,
            updated_by,
            updated_at
        FROM rooms
        ORDER BY room_number
    """, conn)

    conn.close()
    return df


def update_room(
    room_number,
    new_status,
    guest_name,
    note,
    updated_by
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT status
        FROM rooms
        WHERE room_number = ?
    """, (room_number,))

    result = cursor.fetchone()

    if result is None:
        conn.close()
        return False

    old_status = result["status"]

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE rooms
        SET
            status = ?,
            guest_name = ?,
            hk_note = ?,
            updated_by = ?,
            updated_at = ?
        WHERE room_number = ?
    """, (
        new_status,
        guest_name,
        note,
        updated_by,
        now,
        room_number
    ))

    cursor.execute("""
        INSERT INTO history (
            room_number,
            old_status,
            new_status,
            note,
            updated_by,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        room_number,
        old_status,
        new_status,
        note,
        updated_by,
        now
    ))

    conn.commit()
    conn.close()

    return True


def get_history():
    conn = get_connection()

    df = pd.read_sql_query("""
        SELECT
            room_number,
            old_status,
            new_status,
            note,
            updated_by,
            updated_at
        FROM history
        ORDER BY id DESC
    """, conn)

    conn.close()
    return df


# =========================================================
# KHỞI TẠO
# =========================================================

init_database()

rooms_df = get_rooms()

# =========================================================
# TIÊU ĐỀ
# =========================================================

st.title("🏨 THEO DÕI TÌNH TRẠNG PHÒNG")
st.subheader("MELIA VINPEARL PHÚ QUỐC")

st.caption(
    "Hệ thống hỗ trợ bộ phận Housekeeping theo dõi, cập nhật "
    "và kiểm soát tình trạng phòng khách sạn."
)

st.divider()

# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.header("⚙️ BỘ LỌC")

    search_room = st.text_input(
        "🔎 Tìm số phòng",
        placeholder="Ví dụ: V001"
    )

    status_options = [
        "Tất cả",
        "Vacant Clean",
        "Vacant Dirty",
        "Occupied Clean",
        "Occupied Dirty",
        "Inspected",
        "Out of Order",
        "Out of Service"
    ]

    selected_status = st.selectbox(
        "🚪 Tình trạng phòng",
        status_options
    )

    villa_options = [
        "Tất cả"
    ] + sorted(
        rooms_df["villa_type"].dropna().unique().tolist()
    )

    selected_villa = st.selectbox(
        "🏡 Loại villa",
        villa_options
    )

    st.divider()

    st.info(
        "💡 Cập nhật tình trạng phòng thường xuyên "
        "để bộ phận Housekeeping và Front Office "
        "nắm được tình trạng phòng mới nhất."
    )


# =========================================================
# LỌC DỮ LIỆU
# =========================================================

filtered_df = rooms_df.copy()

if search_room:
    filtered_df = filtered_df[
        filtered_df["room_number"]
        .str.contains(search_room, case=False, na=False)
    ]

if selected_status != "Tất cả":
    filtered_df = filtered_df[
        filtered_df["status"] == selected_status
    ]

if selected_villa != "Tất cả":
    filtered_df = filtered_df[
        filtered_df["villa_type"] == selected_villa
    ]


# =========================================================
# DASHBOARD
# =========================================================

st.markdown("## 📊 TỔNG QUAN PHÒNG")

total_rooms = len(rooms_df)

vacant_clean = len(
    rooms_df[rooms_df["status"] == "Vacant Clean"]
)

vacant_dirty = len(
    rooms_df[rooms_df["status"] == "Vacant Dirty"]
)

occupied_clean = len(
    rooms_df[rooms_df["status"] == "Occupied Clean"]
)

occupied_dirty = len(
    rooms_df[rooms_df["status"] == "Occupied Dirty"]
)

inspected = len(
    rooms_df[rooms_df["status"] == "Inspected"]
)

out_of_order = len(
    rooms_df[rooms_df["status"] == "Out of Order"]
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "🏨 Tổng số phòng",
        total_rooms
    )

with col2:
    st.metric(
        "🟢 Vacant Clean",
        vacant_clean
    )

with col3:
    st.metric(
        "🔴 Vacant Dirty",
        vacant_dirty
    )

with col4:
    st.metric(
        "🔵 Occupied Clean",
        occupied_clean
    )

col5, col6, col7, col8 = st.columns(4)

with col5:
    st.metric(
        "🟠 Occupied Dirty",
        occupied_dirty
    )

with col6:
    st.metric(
        "✅ Inspected",
        inspected
    )

with col7:
    st.metric(
        "⚠️ Out of Order",
        out_of_order
    )

with col8:
    st.metric(
        "📋 Đang hiển thị",
        len(filtered_df)
    )


st.divider()


# =========================================================
# BẢNG PHÒNG
# =========================================================

st.markdown("## 🚪 DANH SÁCH PHÒNG")

if filtered_df.empty:

    st.warning(
        "Không tìm thấy phòng phù hợp với điều kiện lọc."
    )

else:

    display_df = filtered_df[
        [
            "room_number",
            "villa_type",
            "status",
            "guest_name",
            "hk_note",
            "updated_by",
            "updated_at"
        ]
    ].copy()

    display_df.columns = [
        "Số phòng",
        "Loại villa",
        "Tình trạng",
        "Tên khách",
        "Ghi chú HK",
        "Người cập nhật",
        "Cập nhật lúc"
    ]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=500
    )


# =========================================================
# CẬP NHẬT PHÒNG
# =========================================================

st.divider()

st.markdown("## ✏️ CẬP NHẬT TÌNH TRẠNG PHÒNG")

room_list = rooms_df["room_number"].tolist()

col1, col2 = st.columns(2)

with col1:

    selected_room = st.selectbox(
        "Chọn phòng cần cập nhật",
        room_list
    )

    current_room = rooms_df[
        rooms_df["room_number"] == selected_room
    ].iloc[0]

    st.write(
        f"**Loại villa:** {current_room['villa_type']}"
    )

    st.write(
        f"**Tình trạng hiện tại:** "
        f"`{current_room['status']}`"
    )


with col2:

    status_update = st.selectbox(
        "Tình trạng mới",
        [
            "Vacant Clean",
            "Vacant Dirty",
            "Occupied Clean",
            "Occupied Dirty",
            "Inspected",
            "Out of Order",
            "Out of Service"
        ]
    )

    guest_name = st.text_input(
        "Tên khách",
        value=str(current_room["guest_name"] or "")
    )

    updated_by = st.text_input(
        "Người cập nhật",
        placeholder="Ví dụ: HK Staff"
    )

note = st.text_area(
    "📝 Ghi chú Housekeeping",
    placeholder=(
        "Ví dụ: Đã vệ sinh phòng, bổ sung amenities, "
        "kiểm tra minibar..."
    )
)

if st.button(
    "💾 CẬP NHẬT PHÒNG",
    type="primary",
    use_container_width=True
):

    if not updated_by.strip():
        st.error(
            "Vui lòng nhập tên người cập nhật."
        )

    else:

        success = update_room(
            selected_room,
            status_update,
            guest_name,
            note,
            updated_by
        )

        if success:

            st.success(
                f"Đã cập nhật phòng {selected_room} "
                f"→ {status_update}"
            )

            st.rerun()

        else:

            st.error(
                "Không thể cập nhật phòng."
            )


# =========================================================
# LỊCH SỬ
# =========================================================

st.divider()

st.markdown("## 🕒 LỊCH SỬ CẬP NHẬT")

history_df = get_history()

if history_df.empty:

    st.info(
        "Chưa có lịch sử cập nhật."
    )

else:

    history_df.columns = [
        "Phòng",
        "Trạng thái cũ",
        "Trạng thái mới",
        "Ghi chú",
        "Người cập nhật",
        "Thời gian"
    ]

    st.dataframe(
        history_df,
        use_container_width=True,
        hide_index=True,
        height=400
    )


# =========================================================
# THỐNG KÊ THEO TRẠNG THÁI
# =========================================================

st.divider()

st.markdown("## 📈 THỐNG KÊ TÌNH TRẠNG PHÒNG")

status_count = (
    rooms_df["status"]
    .value_counts()
    .reset_index()
)

status_count.columns = [
    "Tình trạng",
    "Số phòng"
]

st.bar_chart(
    status_count.set_index("Tình trạng")
)


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "🏨 Melia Vinpearl Phú Quốc | "
    "Housekeeping Room Status Management System"
)

st.caption(
    f"⏱️ Thời gian hệ thống: "
    f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
)
