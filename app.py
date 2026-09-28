import streamlit as st
import mysql.connector
from mysql.connector import Error
from pathlib import Path
from datetime import datetime
import pandas as pd


# =========================================================
# CẤU HÌNH STREAMLIT
# =========================================================

st.set_page_config(
    page_title="Melia Vinpearl Phú Quốc - Housekeeping",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# CẤU HÌNH DATABASE
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
CA_FILE = BASE_DIR / "ca.pem"


# =========================================================
# KẾT NỐI MYSQL AIVEN
# =========================================================

def get_connection():
    """
    Kết nối MySQL Aiven thông qua Streamlit Secrets.
    """

    try:
        def get_connection():

    try:
        connection = mysql.connector.connect(
            host="mysql-24eda0f5-tramy04062005-899b.k.aivencloud.com",
            port=13321,
            user="avnadmin",
            password="AVNS_eyALQ_tYt5oQ7pItFnm",
            database="defaultdb",
            ssl_ca=str(CA_FILE),
            connection_timeout=20
        )

        return connection

    except Exception as e:

        st.error("❌ Không kết nối được Aiven MySQL.")
        st.code(str(e))

        return None
        )

        return connection

    except Exception as e:
        st.error("❌ Không thể kết nối đến Aiven MySQL.")
        st.error(f"Chi tiết lỗi: {e}")
        return None


# =========================================================
# TẠO DATABASE TABLE
# =========================================================

def initialize_database():

    connection = get_connection()

    if connection is None:
        return False

    try:

        cursor = connection.cursor()

        # -------------------------------------------------
        # BẢNG ROOMS
        # -------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rooms (

                id INT AUTO_INCREMENT PRIMARY KEY,

                room_number VARCHAR(20)
                    NOT NULL UNIQUE,

                villa_type VARCHAR(150)
                    NOT NULL,

                building VARCHAR(100),

                floor VARCHAR(20),

                status VARCHAR(50)
                    NOT NULL DEFAULT 'Vacant Dirty',

                guest_name VARCHAR(150),

                hk_note TEXT,

                updated_by VARCHAR(100),

                updated_at DATETIME,

                INDEX idx_room_status (status),

                INDEX idx_room_number (room_number)

            )
        """)

        # -------------------------------------------------
        # BẢNG LỊCH SỬ
        # -------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS room_history (

                id INT AUTO_INCREMENT PRIMARY KEY,

                room_number VARCHAR(20)
                    NOT NULL,

                old_status VARCHAR(50),

                new_status VARCHAR(50),

                note TEXT,

                updated_by VARCHAR(100),

                updated_at DATETIME,

                INDEX idx_history_room (room_number),

                INDEX idx_history_date (updated_at)

            )
        """)

        connection.commit()

        cursor.close()
        connection.close()

        return True

    except Exception as e:

        st.error(
            f"❌ Không thể khởi tạo database: {e}"
        )

        try:
            connection.close()
        except:
            pass

        return False


# =========================================================
# THÊM DỮ LIỆU PHÒNG MẪU
# =========================================================

def create_sample_rooms():

    connection = get_connection()

    if connection is None:
        return

    try:

        cursor = connection.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM rooms"
        )

        total_rooms = cursor.fetchone()[0]

        # Nếu đã có phòng thì không thêm lại
        if total_rooms > 0:

            cursor.close()
            connection.close()

            return

        rooms = []

        # -------------------------------------------------
        # DỮ LIỆU MẪU
        # -------------------------------------------------

        for i in range(1, 11):

            rooms.append((
                f"V{i:03d}",
                "One Bedroom Lake View Private Pool",
                "Villa Area",
                "1",
                "Vacant Clean",
                "",
                "",
                "System",
                datetime.now()
            ))

        for i in range(11, 21):

            rooms.append((
                f"V{i:03d}",
                "Two-Bedroom Lake View Private Pool",
                "Villa Area",
                "1",
                "Vacant Clean",
                "",
                "",
                "System",
                datetime.now()
            ))

        for i in range(21, 31):

            rooms.append((
                f"V{i:03d}",
                "The Level",
                "Villa Area",
                "1",
                "Vacant Clean",
                "",
                "",
                "System",
                datetime.now()
            ))

        # -------------------------------------------------
        # INSERT
        # -------------------------------------------------

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

            VALUES (

                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s

            )
        """, rooms)

        connection.commit()

        cursor.close()
        connection.close()

    except Exception as e:

        st.warning(
            f"Không thể tạo dữ liệu phòng mẫu: {e}"
        )

        try:
            connection.close()
        except:
            pass


# =========================================================
# LẤY DANH SÁCH PHÒNG
# =========================================================

def get_rooms():

    connection = get_connection()

    if connection is None:
        return pd.DataFrame()

    try:

        query = """
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
        """

        df = pd.read_sql(query, connection)

        connection.close()

        return df

    except Exception as e:

        st.error(
            f"Không thể tải dữ liệu phòng: {e}"
        )

        try:
            connection.close()
        except:
            pass

        return pd.DataFrame()


# =========================================================
# CẬP NHẬT PHÒNG
# =========================================================

def update_room(
    room_number,
    new_status,
    guest_name,
    note,
    updated_by
):

    connection = get_connection()

    if connection is None:
        return False

    try:

        cursor = connection.cursor(dictionary=True)

        # -------------------------------------------------
        # LẤY TRẠNG THÁI CŨ
        # -------------------------------------------------

        cursor.execute("""
            SELECT status
            FROM rooms
            WHERE room_number = %s
        """, (room_number,))

        result = cursor.fetchone()

        if result is None:

            cursor.close()
            connection.close()

            return False

        old_status = result["status"]

        now = datetime.now()

        # -------------------------------------------------
        # UPDATE ROOM
        # -------------------------------------------------

        cursor.execute("""
            UPDATE rooms

            SET

                status = %s,

                guest_name = %s,

                hk_note = %s,

                updated_by = %s,

                updated_at = %s

            WHERE room_number = %s

        """, (
            new_status,
            guest_name,
            note,
            updated_by,
            now,
            room_number
        ))

        # -------------------------------------------------
        # LƯU HISTORY
        # -------------------------------------------------

        cursor.execute("""
            INSERT INTO room_history (

                room_number,

                old_status,

                new_status,

                note,

                updated_by,

                updated_at

            )

            VALUES (

                %s,
                %s,
                %s,
                %s,
                %s,
                %s

            )
        """, (
            room_number,
            old_status,
            new_status,
            note,
            updated_by,
            now
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return True

    except Exception as e:

        st.error(
            f"Lỗi cập nhật phòng: {e}"
        )

        try:
            connection.rollback()
            connection.close()
        except:
            pass

        return False


# =========================================================
# LẤY LỊCH SỬ
# =========================================================

def get_history():

    connection = get_connection()

    if connection is None:
        return pd.DataFrame()

    try:

        query = """
            SELECT

                room_number,
                old_status,
                new_status,
                note,
                updated_by,
                updated_at

            FROM room_history

            ORDER BY id DESC
        """

        df = pd.read_sql(query, connection)

        connection.close()

        return df

    except Exception as e:

        st.error(
            f"Không thể tải lịch sử: {e}"
        )

        try:
            connection.close()
        except:
            pass

        return pd.DataFrame()


# =========================================================
# KHỞI TẠO DATABASE
# =========================================================

database_ready = initialize_database()

if database_ready:
    create_sample_rooms()


# =========================================================
# LẤY DỮ LIỆU
# =========================================================

rooms_df = get_rooms()


# =========================================================
# HEADER
# =========================================================

st.title("🏨 MELIA VINPEARL PHÚ QUỐC")

st.subheader(
    "HỆ THỐNG THEO DÕI TÌNH TRẠNG PHÒNG"
)

st.caption(
    "Housekeeping Room Status Management System"
)

st.divider()


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.header("🔎 BỘ LỌC")

    search_room = st.text_input(
        "Tìm số phòng",
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
        "Tình trạng phòng",
        status_options
    )

    if not rooms_df.empty:

        villa_options = [
            "Tất cả"
        ] + sorted(
            rooms_df["villa_type"]
            .dropna()
            .unique()
            .tolist()
        )

    else:

        villa_options = ["Tất cả"]

    selected_villa = st.selectbox(
        "Loại villa",
        villa_options
    )

    st.divider()

    st.success(
        "🟢 Database: Aiven MySQL"
    )


# =========================================================
# LỌC
# =========================================================

filtered_df = rooms_df.copy()

if not filtered_df.empty:

    if search_room:

        filtered_df = filtered_df[
            filtered_df["room_number"]
            .str.contains(
                search_room,
                case=False,
                na=False
            )
        ]

    if selected_status != "Tất cả":

        filtered_df = filtered_df[
            filtered_df["status"]
            == selected_status
        ]

    if selected_villa != "Tất cả":

        filtered_df = filtered_df[
            filtered_df["villa_type"]
            == selected_villa
        ]


# =========================================================
# DASHBOARD
# =========================================================

st.header("📊 TỔNG QUAN")

total_rooms = len(rooms_df)

def count_status(status):
    if rooms_df.empty:
        return 0

    return len(
        rooms_df[
            rooms_df["status"] == status
        ]
    )


vacant_clean = count_status("Vacant Clean")
vacant_dirty = count_status("Vacant Dirty")
occupied_clean = count_status("Occupied Clean")
occupied_dirty = count_status("Occupied Dirty")
inspected = count_status("Inspected")
out_of_order = count_status("Out of Order")
out_of_service = count_status("Out of Service")


row1 = st.columns(4)

with row1[0]:

    st.metric(
        "🏨 Tổng phòng",
        total_rooms
    )

with row1[1]:

    st.metric(
        "🟢 Vacant Clean",
        vacant_clean
    )

with row1[2]:

    st.metric(
        "🔴 Vacant Dirty",
        vacant_dirty
    )

with row1[3]:

    st.metric(
        "🔵 Occupied Clean",
        occupied_clean
    )


row2 = st.columns(4)

with row2[0]:

    st.metric(
        "🟠 Occupied Dirty",
        occupied_dirty
    )

with row2[1]:

    st.metric(
        "✅ Inspected",
        inspected
    )

with row2[2]:

    st.metric(
        "⚠️ Out of Order",
        out_of_order
    )

with row2[3]:

    st.metric(
        "🚫 Out of Service",
        out_of_service
    )


st.divider()


# =========================================================
# DANH SÁCH PHÒNG
# =========================================================

st.header("🚪 DANH SÁCH PHÒNG")

if filtered_df.empty:

    st.warning(
        "Không có phòng phù hợp."
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

st.header("✏️ CẬP NHẬT TÌNH TRẠNG PHÒNG")

if rooms_df.empty:

    st.warning(
        "Chưa có dữ liệu phòng."
    )

else:

    room_list = rooms_df[
        "room_number"
    ].tolist()

    selected_room = st.selectbox(
        "Chọn phòng",
        room_list
    )

    current_room = rooms_df[
        rooms_df["room_number"]
        == selected_room
    ].iloc[0]

    col1, col2 = st.columns(2)

    with col1:

        st.info(
            f"""
**Phòng:** {selected_room}

**Loại villa:** {current_room["villa_type"]}

**Tình trạng hiện tại:** {current_room["status"]}
"""
        )

        guest_name = st.text_input(
            "Tên khách",
            value=str(
                current_room["guest_name"]
                or ""
            )
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

        updated_by = st.text_input(
            "Người cập nhật",
            placeholder="Ví dụ: My - HK"
        )

    note = st.text_area(
        "📝 Ghi chú Housekeeping",

        placeholder=(
            "Ví dụ: Đã vệ sinh toilet, "
            "bổ sung amenities, "
            "thay khăn, kiểm tra minibar..."
        )
    )

    if st.button(
        "💾 LƯU CẬP NHẬT",
        type="primary",
        use_container_width=True
    ):

        if not updated_by.strip():

            st.error(
                "⚠️ Vui lòng nhập người cập nhật."
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
                    f"✅ Đã cập nhật {selected_room} → "
                    f"{status_update}"
                )

                st.rerun()


# =========================================================
# LỊCH SỬ
# =========================================================

st.divider()

st.header("🕒 LỊCH SỬ CẬP NHẬT")

history_df = get_history()

if history_df.empty:

    st.info(
        "Chưa có lịch sử cập nhật."
    )

else:

    history_display = history_df.copy()

    history_display.columns = [
        "Phòng",
        "Trạng thái cũ",
        "Trạng thái mới",
        "Ghi chú",
        "Người cập nhật",
        "Thời gian"
    ]

    st.dataframe(
        history_display,
        use_container_width=True,
        hide_index=True,
        height=400
    )


# =========================================================
# THỐNG KÊ
# =========================================================

st.divider()

st.header("📈 THỐNG KÊ TÌNH TRẠNG")

if not rooms_df.empty:

    chart_data = (
        rooms_df["status"]
        .value_counts()
        .rename_axis("Tình trạng")
        .reset_index(
            name="Số phòng"
        )
    )

    st.bar_chart(
        chart_data.set_index(
            "Tình trạng"
        )
    )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "🏨 Melia Vinpearl Phú Quốc | "
    "Housekeeping Management System"
)

st.caption(
    "☁️ Database: Aiven MySQL"
)
