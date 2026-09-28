import os
from datetime import datetime

import mysql.connector
import pandas as pd
import streamlit as st

# =========================================================
# MELIA VINPEARL PHU QUOC - HOUSEKEEPING ROOM STATUS
# MySQL / Aiven version
# =========================================================

st.set_page_config(
    page_title="Melia Vinpearl Phú Quốc - Room Status",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# AIVEN MYSQL CONFIGURATION
# =========================================================
# NOTE:
# The password is intentionally placed here because you requested
# the fastest setup. If this repository is public, rotate the
# Aiven password after testing.

MYSQL_CONFIG = {
    "host": "mysql-24eda0f5-tramy04062005-899b.k.aivencloud.com",
    "port": 13321,
    "user": "avnadmin",
    "password": "AVNS_eyALQ_tYt5oQ7pItFnm",
    "database": "defaultdb",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CA_FILE = os.path.join(BASE_DIR, "ca.pem")


# =========================================================
# CSS
# =========================================================
st.markdown(
    """
    <style>
    .main-title {
        font-size: 34px;
        font-weight: 800;
        margin-bottom: 0;
    }

    .sub-title {
        color: #6b7280;
        font-size: 15px;
        margin-top: 0;
        margin-bottom: 22px;
    }

    .status-card {
        padding: 18px;
        border-radius: 14px;
        border: 1px solid #e5e7eb;
        background: white;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,.04);
    }

    .room-box {
        border-radius: 14px;
        padding: 14px;
        margin-bottom: 12px;
        min-height: 145px;
        border: 1px solid #e5e7eb;
        background: white;
    }

    .room-number {
        font-size: 22px;
        font-weight: 800;
    }

    .room-type {
        color: #6b7280;
        font-size: 12px;
        min-height: 36px;
    }

    .small-muted {
        color: #6b7280;
        font-size: 12px;
    }

    div[data-testid="stMetric"] {
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 12px;
        background: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# DATABASE
# =========================================================
def get_connection():
    """Create a new Aiven MySQL connection."""
    try:
        config = MYSQL_CONFIG.copy()

        if os.path.exists(CA_FILE):
            config["ssl_ca"] = CA_FILE
            config["ssl_verify_cert"] = True
            config["ssl_verify_identity"] = True
        else:
            # Aiven requires SSL, but this branch gives a useful error
            # if ca.pem was accidentally omitted from the repository.
            raise FileNotFoundError(
                "Không tìm thấy ca.pem. Hãy đặt ca.pem cùng thư mục với app.py."
            )

        return mysql.connector.connect(
            **config,
            connection_timeout=20,
            autocommit=False,
        )

    except Exception as e:
        st.error("❌ Không thể kết nối đến Aiven MySQL.")
        st.code(str(e))
        return None


def execute_query(query, params=None, fetch=False, many=False):
    """Execute a SQL statement safely."""
    conn = get_connection()
    if conn is None:
        return None

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)

        if many:
            cursor.executemany(query, params)
        else:
            cursor.execute(query, params or ())

        if fetch:
            result = cursor.fetchall()
            conn.close()
            return result

        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected

    except Exception as e:
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        st.error("❌ Lỗi thao tác cơ sở dữ liệu.")
        st.code(str(e))
        return None

    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass


def init_database():
    """Create tables and seed sample rooms if the database is empty."""
    conn = get_connection()
    if conn is None:
        return False

    cursor = None
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rooms (
                id INT AUTO_INCREMENT PRIMARY KEY,
                room_number VARCHAR(20) NOT NULL UNIQUE,
                villa_type VARCHAR(120) NOT NULL,
                floor VARCHAR(30) DEFAULT '',
                status VARCHAR(30) NOT NULL DEFAULT 'Vacant Clean',
                guest_name VARCHAR(150) DEFAULT '',
                note TEXT,
                updated_by VARCHAR(100) DEFAULT 'Housekeeping',
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS room_history (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                room_id INT NULL,
                room_number VARCHAR(20) NOT NULL,
                old_status VARCHAR(30),
                new_status VARCHAR(30) NOT NULL,
                note TEXT,
                updated_by VARCHAR(100) DEFAULT 'Housekeeping',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_history_room (room_number),
                INDEX idx_history_date (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )

        cursor.execute("SELECT COUNT(*) AS total FROM rooms")
        total = cursor.fetchone()[0]

        if total == 0:
            rooms = []

            # Sample data. You can add/edit rooms from the app.
            room_types = [
                ("One Bedroom Lake View Private Pool", "1"),
                ("One Bedroom Lake View Private Pool", "1"),
                ("Two-Bedroom Lake Views Private Pool", "2"),
                ("Two-Bedroom Lake Views Private Pool", "2"),
                ("The Level", "3"),
            ]

            # Create 30 sample rooms: V001 - V030
            for i in range(1, 31):
                villa_type, floor = room_types[(i - 1) % len(room_types)]
                rooms.append(
                    (
                        f"V{i:03d}",
                        villa_type,
                        floor,
                        "Vacant Clean",
                        "",
                        "",
                        "Housekeeping",
                    )
                )

            cursor.executemany(
                """
                INSERT INTO rooms
                (room_number, villa_type, floor, status, guest_name, note, updated_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                rooms,
            )

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        st.error("❌ Không thể khởi tạo bảng trên Aiven.")
        st.code(str(e))
        return False

    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass


def load_rooms():
    return execute_query(
        """
        SELECT
            id,
            room_number,
            villa_type,
            floor,
            status,
            guest_name,
            note,
            updated_by,
            updated_at
        FROM rooms
        ORDER BY room_number
        """,
        fetch=True,
    )


def load_history(limit=100):
    return execute_query(
        """
        SELECT
            id,
            room_number,
            old_status,
            new_status,
            note,
            updated_by,
            created_at
        FROM room_history
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (int(limit),),
        fetch=True,
    )


def update_room(room_id, room_number, new_status, guest_name, note, updated_by):
    conn = get_connection()
    if conn is None:
        return False

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT status FROM rooms WHERE id = %s FOR UPDATE",
            (room_id,),
        )
        row = cursor.fetchone()

        if not row:
            raise ValueError("Không tìm thấy phòng.")

        old_status = row["status"]

        cursor.execute(
            """
            UPDATE rooms
            SET status = %s,
                guest_name = %s,
                note = %s,
                updated_by = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (new_status, guest_name, note, updated_by, room_id),
        )

        cursor.execute(
            """
            INSERT INTO room_history
            (room_id, room_number, old_status, new_status, note, updated_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                room_id,
                room_number,
                old_status,
                new_status,
                note,
                updated_by,
            ),
        )

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        st.error("❌ Không cập nhật được phòng.")
        st.code(str(e))
        return False

    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass


def add_room(room_number, villa_type, floor):
    result = execute_query(
        """
        INSERT INTO rooms
        (room_number, villa_type, floor, status, guest_name, note, updated_by)
        VALUES (%s, %s, %s, 'Vacant Clean', '', '', 'Housekeeping')
        """,
        (room_number.strip().upper(), villa_type, floor),
    )
    return result is not None


# =========================================================
# INITIALIZE
# =========================================================
if "db_ready" not in st.session_state:
    st.session_state.db_ready = init_database()

if not st.session_state.db_ready:
    st.stop()

rooms_data = load_rooms()

if rooms_data is None:
    st.stop()

df = pd.DataFrame(rooms_data)

# =========================================================
# HEADER
# =========================================================
st.markdown(
    '<div class="main-title">🏨 MELIA VINPEARL PHÚ QUỐC</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="sub-title">HỆ THỐNG THEO DÕI TÌNH TRẠNG PHÒNG · HOUSEKEEPING</div>',
    unsafe_allow_html=True,
)

st.success("🟢 Database: Aiven MySQL · Dữ liệu được lưu trực tiếp trên máy chủ Aiven.")

# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.header("🔎 BỘ LỌC")

    search_room = st.text_input(
        "Tìm số phòng",
        placeholder="Ví dụ: V001",
    )

    status_options = [
        "Tất cả",
        "Vacant Clean",
        "Vacant Dirty",
        "Occupied Clean",
        "Occupied Dirty",
        "Inspected",
        "Out of Order",
        "Out of Service",
    ]

    status_filter = st.selectbox(
        "Tình trạng phòng",
        status_options,
    )

    villa_options = ["Tất cả"] + sorted(df["villa_type"].dropna().unique().tolist())
    villa_filter = st.selectbox(
        "Loại villa",
        villa_options,
    )

    st.divider()

    st.caption("👤 Người cập nhật")
    updated_by = st.text_input(
        "Tên nhân viên",
        value="Housekeeping",
        label_visibility="collapsed",
    )

    st.divider()

    if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
        st.rerun()


# =========================================================
# FILTER
# =========================================================
filtered = df.copy()

if search_room.strip():
    filtered = filtered[
        filtered["room_number"]
        .astype(str)
        .str.contains(search_room.strip(), case=False, na=False)
    ]

if status_filter != "Tất cả":
    filtered = filtered[filtered["status"] == status_filter]

if villa_filter != "Tất cả":
    filtered = filtered[filtered["villa_type"] == villa_filter]


# =========================================================
# DASHBOARD METRICS
# =========================================================
total = len(df)
vacant_clean = int((df["status"] == "Vacant Clean").sum())
vacant_dirty = int((df["status"] == "Vacant Dirty").sum())
occupied = int(
    df["status"].isin(["Occupied Clean", "Occupied Dirty"]).sum()
)
inspected = int((df["status"] == "Inspected").sum())
ooo = int(
    df["status"].isin(["Out of Order", "Out of Service"]).sum()
)

m1, m2, m3, m4, m5, m6 = st.columns(6)

m1.metric("🏨 Tổng phòng", total)
m2.metric("🟢 Vacant Clean", vacant_clean)
m3.metric("🟠 Vacant Dirty", vacant_dirty)
m4.metric("🔵 Occupied", occupied)
m5.metric("✅ Inspected", inspected)
m6.metric("🔴 OOO / OOS", ooo)

st.divider()

# =========================================================
# TABS
# =========================================================
tab_rooms, tab_update, tab_history, tab_add = st.tabs(
    [
        "🏨 DANH SÁCH PHÒNG",
        "✏️ CẬP NHẬT PHÒNG",
        "📜 LỊCH SỬ",
        "➕ THÊM PHÒNG",
    ]
)


# =========================================================
# TAB 1 - ROOM LIST
# =========================================================
with tab_rooms:
    st.subheader(f"Danh sách phòng ({len(filtered)})")

    if filtered.empty:
        st.info("Không tìm thấy phòng phù hợp với bộ lọc.")
    else:
        status_emoji = {
            "Vacant Clean": "🟢",
            "Vacant Dirty": "🟠",
            "Occupied Clean": "🔵",
            "Occupied Dirty": "🟣",
            "Inspected": "✅",
            "Out of Order": "🔴",
            "Out of Service": "⚫",
        }

        # 3 columns of room cards
        rows = list(filtered.to_dict("records"))

        for start in range(0, len(rows), 3):
            cols = st.columns(3)

            for col, room in zip(cols, rows[start:start + 3]):
                emoji = status_emoji.get(room["status"], "⚪")

                with col:
                    st.markdown(
                        f"""
                        <div class="room-box">
                            <div class="room-number">
                                {emoji} {room["room_number"]}
                            </div>
                            <div class="room-type">
                                {room["villa_type"]}
                            </div>
                            <div style="margin-top:8px;">
                                <b>{room["status"]}</b>
                            </div>
                            <div class="small-muted">
                                Tầng/Khu: {room["floor"] or "-"}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if st.button(
                        f"✏️ Cập nhật {room['room_number']}",
                        key=f"quick_{room['id']}",
                        use_container_width=True,
                    ):
                        st.session_state["selected_room_id"] = int(room["id"])
                        st.rerun()


# =========================================================
# TAB 2 - UPDATE ROOM
# =========================================================
with tab_update:
    st.subheader("Cập nhật tình trạng phòng")

    room_map = {
        f"{row['room_number']} — {row['villa_type']}": int(row["id"])
        for row in rooms_data
    }

    if not room_map:
        st.info("Chưa có phòng.")
    else:
        selected_id = st.session_state.get(
            "selected_room_id",
            int(df.iloc[0]["id"]),
        )

        selected_index = 0
        id_list = list(room_map.values())
        if selected_id in id_list:
            selected_index = id_list.index(selected_id)

        selected_label = st.selectbox(
            "Chọn phòng",
            list(room_map.keys()),
            index=selected_index,
        )

        room_id = room_map[selected_label]
        room_row = df[df["id"] == room_id].iloc[0]

        c1, c2 = st.columns(2)

        with c1:
            st.info(
                f"**{room_row['room_number']}** · "
                f"{room_row['villa_type']}"
            )

            current_status = st.selectbox(
                "Tình trạng",
                status_options[1:],
                index=(
                    status_options[1:].index(room_row["status"])
                    if room_row["status"] in status_options[1:]
                    else 0
                ),
            )

        with c2:
            guest_name = st.text_input(
                "Tên khách",
                value=str(room_row["guest_name"] or ""),
            )

            note = st.text_area(
                "Ghi chú",
                value=str(room_row["note"] or ""),
                height=100,
            )

        if st.button(
            "💾 LƯU TÌNH TRẠNG PHÒNG",
            type="primary",
            use_container_width=True,
        ):
            success = update_room(
                room_id=room_id,
                room_number=room_row["room_number"],
                new_status=current_status,
                guest_name=guest_name,
                note=note,
                updated_by=updated_by.strip() or "Housekeeping",
            )

            if success:
                st.success(
                    f"✅ Đã cập nhật {room_row['room_number']} → {current_status}"
                )
                st.session_state.pop("selected_room_id", None)
                st.rerun()


# =========================================================
# TAB 3 - HISTORY
# =========================================================
with tab_history:
    st.subheader("Lịch sử cập nhật phòng")

    history_data = load_history(200)

    if history_data:
        history_df = pd.DataFrame(history_data)

        history_df["created_at"] = pd.to_datetime(
            history_df["created_at"]
        ).dt.strftime("%d/%m/%Y %H:%M:%S")

        history_df.columns = [
            "ID",
            "Số phòng",
            "Trạng thái cũ",
            "Trạng thái mới",
            "Ghi chú",
            "Người cập nhật",
            "Thời gian",
        ]

        st.dataframe(
            history_df,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Chưa có lịch sử cập nhật.")


# =========================================================
# TAB 4 - ADD ROOM
# =========================================================
with tab_add:
    st.subheader("Thêm phòng / villa")

    with st.form("add_room_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)

        with c1:
            new_room = st.text_input(
                "Số phòng",
                placeholder="Ví dụ: V031",
            )

        with c2:
            new_type = st.selectbox(
                "Loại villa",
                [
                    "One Bedroom Lake View Private Pool",
                    "Two-Bedroom Lake Views Private Pool",
                    "The Level",
                    "Khác",
                ],
            )

        with c3:
            new_floor = st.text_input(
                "Tầng / khu",
                placeholder="Ví dụ: 1",
            )

        submitted = st.form_submit_button(
            "➕ THÊM PHÒNG",
            use_container_width=True,
        )

        if submitted:
            if not new_room.strip():
                st.warning("Vui lòng nhập số phòng.")
            else:
                success = add_room(
                    new_room,
                    new_type,
                    new_floor,
                )

                if success:
                    st.success(
                        f"✅ Đã thêm phòng {new_room.strip().upper()}."
                    )
                    st.rerun()


# =========================================================
# FOOTER
# =========================================================
st.divider()

st.caption(
    "Melia Vinpearl Phú Quốc · Housekeeping Room Status Management · "
    f"Cập nhật giao diện: {datetime.now().strftime('%d/%m/%Y')}"
)
