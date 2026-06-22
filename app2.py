import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import base64
import io
from PIL import Image, ImageDraw

st.set_page_config(
    page_title="MMR KPA (GAJI)",
    page_icon="TDM.png",
    layout="centered",
    initial_sidebar_state="expanded"
)

if "host_logged_in" not in st.session_state:
    st.session_state.host_logged_in = False

st.markdown("""
<style>
   .stTextInput {
        font-size: 20px;
    }

    .stMarkdown h1, .stMarkdown h2 {
        font-size: 20px;
    }

    .stMarkdown p {
        font-size: 30px;
    }

    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 900px;
    }

    .time-box {
        text-align: center;
        font-size: 16px;
        font-weight: 600;
        padding: 10px;
        border-radius: 10px;
        background-color: #f3f4f6;
        margin-top: 14px;
        margin-bottom: 18px;
        color: black;
    }

    .center-caption {
        text-align: center;
        margin-bottom: 20px;
        color: #555;
    }

    div[data-testid="stTextInput"] {
        max-width: 420px;
    }

    @media (max-width: 640px) {
        .block-container {
            padding-top: 0.5rem;
            padding-left: 0.7rem;
            padding-right: 0.7rem;
        }
    }
</style>
""", unsafe_allow_html=True)

DATA_FILE = "data baru 1.csv"
ATTENDANCE_FILE = "attendance_records.csv"

LOGO_UGAT = "Logo-UGAT.png"
CENTER_IMAGE = "GAMBAR BARU 3.png"   # <-- change this if your new image has another filename

DEFAULT_HOST_PASSWORD = "salman"

required_cols = ["BIL", "NOTEN", "NAMA", "MENU", "MEJA"]


# =========================================================
# BASIC FUNCTIONS
# =========================================================
def get_file_mtime(file_path):
    path = Path(file_path)
    if path.exists():
        return path.stat().st_mtime
    return 0


def get_file_updated_time():
    files_to_check = [DATA_FILE, ATTENDANCE_FILE]
    existing_files = [Path(f) for f in files_to_check if Path(f).exists()]

    if not existing_files:
        return "Tiada rekod"

    latest_file = max(existing_files, key=lambda x: x.stat().st_mtime)
    latest_time = datetime.fromtimestamp(
        latest_file.stat().st_mtime,
        ZoneInfo("Asia/Kuala_Lumpur")
    )

    return latest_time.strftime("%d/%m/%Y %I:%M:%S %p")


def clean_csv(df_raw):
    df_raw = df_raw.dropna(how="all").reset_index(drop=True)
    df_raw.columns = [str(col).strip().upper() for col in df_raw.columns]

    if all(col in df_raw.columns for col in required_cols):
        df = df_raw.copy()
    else:
        header_row_index = None

        for i in range(len(df_raw)):
            row_values = [str(value).strip().upper() for value in df_raw.iloc[i].tolist()]

            if (
                "BIL" in row_values
                and "NOTEN" in row_values
                and "NAMA" in row_values
                and "MENU" in row_values
                and "MEJA" in row_values
            ):
                header_row_index = i
                break

        if header_row_index is None:
            st.error(
                "Header CSV tidak dijumpai. Pastikan fail CSV ada kolum "
                "BIL, NOTEN, NAMA, MENU dan MEJA."
            )
            st.stop()

        headers = [str(value).strip().upper() for value in df_raw.iloc[header_row_index].tolist()]
        df = df_raw.iloc[header_row_index + 1:].copy()
        df.columns = headers

    df = df.loc[:, df.columns.notna()]
    df = df.loc[:, [str(col).strip() != "" for col in df.columns]]
    df = df.loc[:, ~df.columns.astype(str).str.upper().str.startswith("UNNAMED")]
    df = df.dropna(how="all").reset_index(drop=True)
    df.columns = [str(col).strip().upper() for col in df.columns]

    for col in df.columns:
        df[col] = df[col].fillna("").astype(str).str.strip()

    if "BIL" in df.columns:
        df["BIL"] = df["BIL"].str.replace(".0", "", regex=False)

    if "NOTEN" in df.columns:
        df["NOTEN"] = df["NOTEN"].str.replace(".0", "", regex=False)

    if "MEJA" in df.columns:
        df["MEJA"] = df["MEJA"].str.replace(".0", "", regex=False).str.upper().str.strip()

    return df


@st.cache_data
def load_default_data(file_mtime):
    file_path = Path(DATA_FILE)

    if not file_path.exists():
        st.error(f"Fail '{DATA_FILE}' tidak dijumpai.")
        st.stop()

    df_raw = pd.read_csv(file_path, encoding="utf-8")
    return clean_csv(df_raw)


def load_uploaded_files(uploaded_files):
    all_data = []

    for uploaded_file in uploaded_files:
        df_raw = pd.read_csv(uploaded_file, encoding="utf-8")
        df = clean_csv(df_raw)
        all_data.append(df)

    if not all_data:
        return pd.DataFrame()

    return pd.concat(all_data, ignore_index=True)


def load_attendance():
    file_path = Path(ATTENDANCE_FILE)

    if file_path.exists():
        try:
            attendance_df = pd.read_csv(file_path)
            attendance_df.columns = [str(col).strip().upper() for col in attendance_df.columns]

            for col in attendance_df.columns:
                attendance_df[col] = attendance_df[col].fillna("").astype(str).str.strip()

            if "NOTEN" in attendance_df.columns:
                attendance_df["NOTEN"] = attendance_df["NOTEN"].str.replace(".0", "", regex=False)

            return attendance_df
        except Exception:
            pass

    return pd.DataFrame(columns=[
        "BIL", "NOTEN", "NAMA", "MENU", "MEJA",
        "STATUS_KEHADIRAN", "TARIKH_MASA"
    ])


def save_attendance(attendance_df):
    attendance_df.to_csv(ATTENDANCE_FILE, index=False, encoding="utf-8")


def reset_attendance():
    reset_attendance_df = pd.DataFrame(columns=[
        "BIL", "NOTEN", "NAMA", "MENU", "MEJA",
        "STATUS_KEHADIRAN", "TARIKH_MASA"
    ])
    reset_attendance_df.to_csv(ATTENDANCE_FILE, index=False, encoding="utf-8")


def verify_host_password(password_input):
    try:
        real_password = st.secrets["HOST_PASSWORD"]
    except Exception:
        real_password = DEFAULT_HOST_PASSWORD

    return password_input == real_password


def get_base64_image(image_path):
    path = Path(image_path)

    if not path.exists():
        return ""

    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# =========================================================
# HIGHLIGHT FUNCTIONS
# HIGHLIGHT ONLY TABLE NUMBER BOXES FROM THE FILTERED GROUP
# =========================================================
import base64
import io
from pathlib import Path
from PIL import Image, ImageDraw

# =========================================================
# IMAGE PATH
# Change this to your actual new image file name/path
# =========================================================
CENTER_IMAGE = "GAMBAR BARU 3.png"
# Example if full path:
# CENTER_IMAGE = "/mount/src/mmrugat/GAMBAR BARU 3.png"

# =========================================================
# REFERENCE SIZE OF THE ANALYZED IMAGE
# This coordinate setup is based on the new image size:
# 2048 x 1152
# =========================================================
REF_W = 2048
REF_H = 1152


# =========================================================
# NORMALIZE MEJA VALUE
# Example:
# " ar 1 " -> "AR1"
# "1.0" -> "1"
# =========================================================
def normalize_meja(value):
    value = str(value).strip().upper()

    if value.endswith(".0"):
        value = value[:-2]

    value = value.replace(" ", "")
    return value


# =========================================================
# GENERATE FULL SEAT MAP
# Covers:
# - FL20 until FL1
# - FR20 until FR1
# - ...
# - AL20 until AL1
# - AR20 until AR1
# - VIP side 1,2,3...14
# =========================================================
def generate_seat_map(img_w, img_h):
    seat_map = {}

    # -----------------------------------------------------
    # HALL ROW X CENTERS
    # LEFT -> RIGHT in the image = seat 20 -> seat 1
    # Based on your new image
    # -----------------------------------------------------
    hall_x_centers_ref = [
        210, 287, 362, 438, 512,
        587, 662, 737, 810, 885,
        958, 1033, 1107, 1182, 1257,
        1331, 1406, 1481, 1555, 1629
    ]

    # -----------------------------------------------------
    # HALL ROW Y CENTERS
    # Based on the new image
    # -----------------------------------------------------
    hall_row_y_ref = {
        "FL": 58,
        "FR": 159,
        "EL": 221,
        "ER": 321,
        "DL": 379,
        "DR": 480,
        "CL": 583,
        "CR": 683,
        "BL": 738,
        "BR": 837,
        "AL": 898,
        "AR": 998,
    }

    # Box size for hall seats
    hall_box_w_ref = 68
    hall_box_h_ref = 32

    hall_box_w = int(round(hall_box_w_ref * img_w / REF_W))
    hall_box_h = int(round(hall_box_h_ref * img_h / REF_H))

    # Create coordinates for FL20 until AR1
    for prefix, y_ref in hall_row_y_ref.items():
        y = int(round(y_ref * img_h / REF_H))

        for i, x_ref in enumerate(hall_x_centers_ref):
            seat_no = 20 - i
            x = int(round(x_ref * img_w / REF_W))

            seat_id = f"{prefix}{seat_no}"

            seat_map[seat_id] = {
                "x": x,
                "y": y,
                "w": hall_box_w,
                "h": hall_box_h
            }

    # -----------------------------------------------------
    # VIP RIGHT SIDE NUMBER BOXES
    # Correct order based on the new image
    # -----------------------------------------------------
    vip_x_ref = 1932
    vip_y_ref = {
        "13": 171,
        "11": 221,
        "9": 270,
        "7": 319,
        "5": 367,
        "3": 416,
        "1": 465,
        "2": 520,
        "4": 574,
        "6": 624,
        "8": 674,
        "10": 725,
        "12": 775,
        "14": 826,
    }

    vip_box_w_ref = 44
    vip_box_h_ref = 32

    vip_x = int(round(vip_x_ref * img_w / REF_W))
    vip_box_w = int(round(vip_box_w_ref * img_w / REF_W))
    vip_box_h = int(round(vip_box_h_ref * img_h / REF_H))

    for meja, y_ref in vip_y_ref.items():
        y = int(round(y_ref * img_h / REF_H))

        seat_map[meja] = {
            "x": vip_x,
            "y": y,
            "w": vip_box_w,
            "h": vip_box_h
        }

    return seat_map


# =========================================================
# GENERATE HIGHLIGHTED LAYOUT
# IMPORTANT:
# Pass group_df here, NOT full df
# =========================================================
def generate_highlighted_layout(group_df):
    path = Path(CENTER_IMAGE)

    if not path.exists():
        return "", []

    image = Image.open(path).convert("RGBA")
    img_w, img_h = image.size

    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    seat_map = generate_seat_map(img_w, img_h)

    meja_list = (
        group_df["MEJA"]
        .dropna()
        .astype(str)
        .apply(normalize_meja)
        .unique()
    )

    missing_meja = []

    for meja in meja_list:
        if meja in seat_map:
            info = seat_map[meja]

            x = info["x"]
            y = info["y"]
            w = info["w"]
            h = info["h"]

            pad_x = 4
            pad_y = 4

            x1 = x - (w // 2) - pad_x
            y1 = y - (h // 2) - pad_y
            x2 = x + (w // 2) + pad_x
            y2 = y + (h // 2) + pad_y

            draw.rectangle(
                [x1, y1, x2, y2],
                fill=(0, 102, 255, 70),
                outline=(0, 102, 255, 255),
                width=4
            )
        else:
            missing_meja.append(meja)

    highlighted = Image.alpha_composite(image, overlay)

    img_byte_arr = io.BytesIO()
    highlighted.convert("RGB").save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    layout_base64 = base64.b64encode(img_byte_arr.getvalue()).decode()

    return layout_base64, missing_meja


# =========================================================
# SIDEBAR HOST LOGIN + UPLOAD
# =========================================================
if st.session_state.host_logged_in:
    st.sidebar.title("Host Panel")
    st.sidebar.success("Anda login sebagai host.")

    uploaded_files = st.sidebar.file_uploader(
        "Upload CSV Files",
        accept_multiple_files=True,
        type=["csv"]
    )

    if uploaded_files:
        try:
            new_df = load_uploaded_files(uploaded_files)

            missing_uploaded_cols = [
                col for col in required_cols
                if col not in new_df.columns
            ]

            if missing_uploaded_cols:
                st.sidebar.error(
                    f"CSV baru tidak lengkap. Kolum tiada: {missing_uploaded_cols}"
                )
            else:
                new_df.to_csv(DATA_FILE, index=False, encoding="utf-8")
                reset_attendance()
                st.cache_data.clear()

                st.sidebar.success(
                    "CSV baru berjaya dimuat naik. "
                    "Data tetamu telah dikemaskini dan rekod kehadiran telah direset."
                )
                st.rerun()

        except Exception as e:
            st.sidebar.error(f"Fail tidak dapat dibaca: {e}")

    if st.sidebar.button("Logout Host"):
        st.session_state.host_logged_in = False
        st.rerun()

else:
    st.sidebar.title("Host Login")

    host_password_input = st.sidebar.text_input(
        "Masukkan kata laluan",
        type="password"
    )

    if st.sidebar.button("Login"):
        if verify_host_password(host_password_input):
            st.session_state.host_logged_in = True
            st.sidebar.success("Login berjaya.")
            st.rerun()
        else:
            st.sidebar.error("Kata laluan salah.")


# =========================================================
# LOAD DATA
# =========================================================
df = load_default_data(get_file_mtime(DATA_FILE))
attendance_df = load_attendance()

missing_cols = [col for col in required_cols if col not in df.columns]

if missing_cols:
    st.error(f"Kolum berikut tiada dalam fail CSV: {missing_cols}")
    st.stop()


# =========================================================
# BANNER HEADER
# =========================================================
img_base64 = get_base64_image(LOGO_UGAT)

if img_base64:
    st.markdown(f"""
    <div style="
        display: flex;
        align-items: center;
        gap: 23px;
        background: linear-gradient(90deg, #020617, #111827);
        padding: 15px;
        border-radius: 15px;
        margin-bottom: 15px;
        margin-top: 30px;
    ">
        <img src="data:image/png;base64,{img_base64}" width="60">
        <h2 style="
            margin: 0;
            color: #e0f2f1;
            font-family: 'Arial', sans-serif;
            font-weight: bold;
            font-size: 22px;
        ">
            Majlis Makan Malam
            Rejimental Penghargaan
            Brigedier Jeneral Dato' Zamzuri bin Harun
        </h2>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="
        display: flex;
        align-items: center;
        gap: 12px;
        background: linear-gradient(90deg, #020617, #111827);
        padding: 15px;
        border-radius: 15px;
        margin-bottom: 15px;
        margin-top: 30px;
    ">
        <h2 style="
            margin: 0;
            color: white;
            font-family: 'Arial', sans-serif;
            font-weight: bold;
            font-size: 22px;
        ">
            Majlis Makan Malam
            Rejimental Penghargaan
            Brigedier Jeneral Dato' Zamzuri bin Harun
        </h2>
    </div>
    """, unsafe_allow_html=True)


# =========================================================
# SEARCH SECTION
# =========================================================
st.markdown(
    "<h3 style='color:#ffffff;'>Masukkan Nombor Tentera</h3>",
    unsafe_allow_html=True
)
search_no = st.text_input("",max_chars=20,placeholder="Contoh: 3004463")

if search_no:
    search_value = search_no.strip()

    result_df = df[
        df["NOTEN"].astype(str).str.contains(search_value, case=False, na=False)
    ].copy()

    if result_df.empty:
        st.warning("Tiada rekod dijumpai untuk nombor tentera tersebut.")
    else:
        bil_value = str(result_df.iloc[0]["BIL"]).strip()
        group_df = df[df["BIL"].astype(str).str.strip() == bil_value].copy()

        st.success("Rekod dijumpai")

        st.markdown("### Maklumat Kehadiran")

        display_cols = ["BIL", "NOTEN", "NAMA", "MENU", "MEJA"]
        if "CATATAN" in group_df.columns:
            display_cols.append("CATATAN")

        st.table(group_df[display_cols])

        st.markdown("### Pelan Kedudukan Dewan")

        # IMPORTANT: use group_df, NOT full df
        layout_base64, missing_meja = generate_highlighted_layout(group_df)

        if layout_base64:
            st.image(f"data:image/png;base64,{layout_base64}", use_container_width=True)

            if missing_meja:
                st.warning(
                    f"The following meja values are missing from the layout: {', '.join(missing_meja)}"
                )
        else:
            st.error("Error generating the highlighted image.")

        st.markdown(
            f"<div class='time-box'>Last Updated: {get_file_updated_time()}</div>",
            unsafe_allow_html=True
        )

        sudah_hadir_semua = True

        for _, row in group_df.iterrows():
            noten = str(row["NOTEN"]).strip()
            sudah_hadir = False

            if not attendance_df.empty and "NOTEN" in attendance_df.columns:
                sudah_hadir = noten in attendance_df["NOTEN"].astype(str).str.strip().values

            if not sudah_hadir:
                sudah_hadir_semua = False

        if sudah_hadir_semua:
            st.success("✅ TELAH HADIR")
        else:
            st.warning("❌ BELUM HADIR")

        if st.session_state.host_logged_in:
            if not sudah_hadir_semua:
                if st.button("Submit / Tandakan Kehadiran Kumpulan Ini"):
                    new_records = []

                    for _, row in group_df.iterrows():
                        noten = str(row["NOTEN"]).strip()

                        already_exists = False
                        if not attendance_df.empty and "NOTEN" in attendance_df.columns:
                            already_exists = noten in attendance_df["NOTEN"].astype(str).str.strip().values

                        if not already_exists:
                            new_records.append({
                                "BIL": row["BIL"],
                                "NOTEN": row["NOTEN"],
                                "NAMA": row["NAMA"],
                                "MENU": row["MENU"],
                                "MEJA": row["MEJA"],
                                "STATUS_KEHADIRAN": "HADIR",
                                "TARIKH_MASA": datetime.now(
                                    ZoneInfo("Asia/Kuala_Lumpur")
                                ).strftime("%Y-%m-%d %H:%M:%S")
                            })

                    if new_records:
                        attendance_df = pd.concat(
                            [attendance_df, pd.DataFrame(new_records)],
                            ignore_index=True
                        )
                        save_attendance(attendance_df)
                        st.success("Kehadiran berjaya direkodkan.")
                        st.rerun()
                    else:
                        st.info("Semua dalam BIL ini telah ditandakan hadir.")
        else:
            st.info("Sila ke kaunter pendaftaran untuk mengesahkan kehadiran.")

else:
    st.info("Sila masukkan No Tentera untuk membuat carian.")

st.markdown("---")


# =========================================================
# LIVE ATTENDANCE - HOST ONLY
# =========================================================
if st.session_state.host_logged_in:
    st.markdown("### 📋 Live Attendance / Kehadiran Semasa")

    hadir_noten = []

    if not attendance_df.empty and "NOTEN" in attendance_df.columns:
        hadir_noten = attendance_df["NOTEN"].astype(str).str.strip().tolist()

    belum_hadir_df = df[
        ~df["NOTEN"].astype(str).str.strip().isin(hadir_noten)
    ].copy()

    total_semua = len(df)
    total_hadir = len(attendance_df)
    total_belum_hadir = len(belum_hadir_df)

    st.info(f"Jumlah Keseluruhan: {total_semua}")
    st.success(f"Jumlah Telah Hadir: {total_hadir}")
    st.warning(f"Jumlah Belum Hadir: {total_belum_hadir}")

    st.markdown("### ✅ Telah Hadir")

    if attendance_df.empty:
        st.warning("Belum ada rekod kehadiran.")
    else:
        st.dataframe(attendance_df, use_container_width=True)

    st.markdown("### ❌ Belum Hadir")

    if belum_hadir_df.empty:
        st.success("Semua telah hadir.")
    else:
        belum_cols = ["BIL", "NOTEN", "NAMA", "MENU", "MEJA"]

        if "CATATAN" in belum_hadir_df.columns:
            belum_cols.append("CATATAN")

        st.dataframe(belum_hadir_df[belum_cols], use_container_width=True)

    csv_data = attendance_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Muat Turun Rekod Kehadiran",
        data=csv_data,
        file_name="attendance_records.csv",
        mime="text/csv"
    )
