HALF_LIFE_MIN = 109.7  # نیمه‌عمر F-18 به دقیقه - هماهنگ با محاسبات موجود در برنامه

# تاریخچه‌ی پرینت‌ها به تفکیک BachNo: کلید = نام batch (مثل C020050505-01)،
# مقدار = لیست متن کامل هر لیبلی که برای همان batch پرینت شده است.
# این جداسازی تضمین می‌کند که گزارش هر batch فقط شامل لیبل‌های همان batch باشد،
# نه لیبل‌های batchهای قبلی/بعدی.
print_history_by_batch = {}


def extract_batch_name(text):
    """نام batch را از خط 'BachNo:' یک متن لیبل استخراج می‌کند (قسمت قبل از '/'،
    بدون خود پیشوند BachNo:)، مثل C020050505-01. اگر پیدا نشود None برمی‌گرداند."""
    for line in text.split('\n'):
        if line.startswith("BachNo:"):
            return line.replace("BachNo:", "").split('/')[0].strip()
    return None


def format_activity_mci(raw_value):
    """عدد اکتیویته را بدون رقم اعشار (صرف‌نظر/truncate) و با واحد mCi برمی‌گرداند.
    اگر مقدار ورودی عدد معتبر نباشد، مقدار پیش‌فرض 0 mCi بازگردانده می‌شود."""
    try:
        num = float(raw_value)
    except (TypeError, ValueError):
        return "0 mCi"
    return f"{int(num)} mCi"


def compute_a_activity(current_activity_mci, target_time_str, click_dt):
    """اکتیویته‌ی خوانده‌شده (Activity) را از لحظه‌ی کلیک تا ساعت مشخص‌شده برای
    مرکز (ستون list2 همان ردیف) دیکی (decay) می‌کند و عدد صحیح بدون اعشار برمی‌گرداند.
    اگر ساعت مرکز خالی/نامعتبر باشد، 0 برگردانده می‌شود."""
    try:
        hour_str, minute_str = target_time_str.strip().split(':')
        target_dt = click_dt.replace(hour=int(hour_str), minute=int(minute_str),
                                      second=0, microsecond=0)
    except Exception:
        return 0
    elapsed_min = (target_dt - click_dt).total_seconds() / 60.0
    try:
        decayed = float(current_activity_mci) * (0.5 ** (elapsed_min / HALF_LIFE_MIN))
    except Exception:
        return 0
    return int(decayed)


# When a widget in list0 is clicked, insert its label text as a new line after the batch number line
def update_batch_line(event):
    widget = event.widget
    # Try to get text from Label or Entry
    try:
        if hasattr(widget, 'cget') and widget.winfo_class() == 'Label':
            value = widget.cget('text').strip()
        else:
            value = widget.get().strip()
    except Exception:
        value = ""
    if value:
        text = text_field.get("1.0", "end-1c")
        lines = text.split('\n')

        # Find the index of the clicked label in list0 (row index for this center)
        try:
            idx = list0.index(widget)
        except Exception:
            idx = None

        # --- خواندن مقدار فعلی خط Activity (بدون واحد mCi) برای استفاده در محاسبه A-Activity ---
        current_activity_val = 0.0
        for line in lines:
            if line.startswith("Activity:"):
                raw_activity = line.replace("Activity:", "").replace("mCi", "").strip()
                try:
                    current_activity_val = float(raw_activity)
                except ValueError:
                    current_activity_val = 0.0
                break

        # --- به‌روزرسانی خط A-Activity: دیکی اکتیویته از لحظه کلیک تا ساعت مرکز ---
        click_dt = datetime.now()
        if idx is not None:
            try:
                center_time_val = list2[idx].get().strip()
            except Exception:
                center_time_val = ''
            a_activity_val = compute_a_activity(current_activity_val, center_time_val, click_dt)
            for i, line in enumerate(lines):
                if line.startswith("A-Activity:"):
                    lines[i] = f"A-Activity: {a_activity_val} mCi"
                    break

        # --- به‌روزرسانی خط Time: ساعت همین لحظه (کلیک) - ساعت کالیبره مرکز ---
        if idx is not None:
            click_time_part = click_dt.strftime("%H:%M")
            for i, line in enumerate(lines):
                if line.startswith("Time:"):
                    lines[i] = f"Time: {click_time_part} - Cal Time:{center_time_val}"
                    break

        # --- به‌روزرسانی خط "15 ml container/": حجم لازم همان ردیف (Needed Volume) ---
        if idx is not None:
            try:
                needed_vol_val = list5[idx].get().strip()
            except Exception:
                needed_vol_val = ''
            if needed_vol_val:
                for i, line in enumerate(lines):
                    if 'container/' in line and 'ml' in line:
                        before = line.split('container/')[0] + 'container/ '
                        lines[i] = f"{before}{needed_vol_val} ml"
                        break

        # --- منطق فعلی خط BachNo (بدون تغییر) ---
        # Find the batch number line
        batch_line = None
        for i, line in enumerate(lines):
            if line.startswith("BachNo:"):
                batch_line = i
                break
        if batch_line is None:
            from persiantools.jdatetime import JalaliDate
            today = JalaliDate.today()
            year = today.year % 100
            month = today.month
            day = today.day
            # پیشوند بعد از BachNo: طبق محصولِ فعلاً انتخاب‌شده (پیش‌فرض C020 برای FDG).
            # این پیشوند از پنل Advance می‌آید و می‌تواند چند کاراکتری باشد (حرف+عدد)،
            # پس دیگر "020" به‌صورت ثابت اضافه نمی‌شود.
            batch_number = f"BachNo:{CURRENT_PRODUCT_LETTER}{year:02d}{month:02d}{day:02d}-01/"
            lines.append(batch_number)
            batch_line = len(lines) - 1
        # Remove any previous label appended to the batch number line (after a slash)
        import re
        batch_line_content = lines[batch_line]
        batch_line_content = re.sub(r"(/.*)$", "/", batch_line_content)
        clean_value = value.replace(' ', '').replace(':', '')
        # Get the corresponding value from list1 (Entry) using idx already computed above
        try:
            entry_val = list1[idx].get().strip().replace(' ', '').replace(':', '') if idx is not None else ''
        except Exception:
            entry_val = ''
        # Append both cleaned label and entry value
        lines[batch_line] = batch_line_content + clean_value + entry_val
        text_field.delete("1.0", "end")
        text_field.insert("1.0", '\n'.join(lines))

# Bindings for Entry widgets (must be after all variables and functions are defined)
def setup_entry_bindings():
    # Only bind if all variables are defined
    try:
        for entry in [entry15, entry25, entry35, entry45, entry55, entry65, entry75, entry85, entry95, entry10_5]:
            entry.bind('<FocusIn>', update_container_line)
        for widget in list0:
            widget.bind('<Button-1>', update_batch_line)
    except Exception as e:
        print(f"[DEBUG] Entry binding error: {e}")

## Call after all widgets and lists are defined (move to end of file)
from tkinter import *
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import time
import re
import math
from datetime import datetime, timedelta
from dateutil import parser
import os
import sys
import json
from PIL import ImageTk, Image
import win32print
import win32ui
import win32con
# ------------- ایمپورت‌های مربوط به اتصال زنده به دوزکالیبراتور Comecer -------------
import socket
import threading
import queue
from dataclasses import dataclass
from typing import Optional, Callable
# ---------------------------------
window =Tk()
# پنجره تا وقتی همه‌چیز (صفحه‌ی اصلی + صفحه‌ی خوش‌آمد روی آن) کامل ساخته نشده، مخفی می‌ماند
# تا هیچ‌وقت برای لحظه‌ای صفحه‌ی دوم (اصلی) قبل از صفحه‌ی خوش‌آمد دیده نشود.
window.withdraw()

# --- Debug helper for UI mapping ---
def debug_widget(event, name):
    widget = event.widget
    try:
        info = widget.grid_info()
    except Exception:
        info = {}
    print(f"[DEBUG] Widget: {name}, Type: {type(widget).__name__}, Grid: {info}")

def add_debug(widget, name):
    try:
        widget.bind('<Button-1>', lambda e: debug_widget(e, name))
    except Exception:
        pass
    return widget
# -----------------------------------------

window.geometry("830x730+350+10")
window.title("NADEF18")
window.resizable(1, 0)
window.config(bg='#adad85')

# فشرده‌سازی چیدمان — همه اجزا در 900x780 جا شوند (بدون تغییر اندازه پنجره)
UI_COL_PAD = 2
UI_ROW_PAD = 0
UI_ENTRY_W = 7
UI_CENTER_W = 13
UI_FONT_ENTRY = ("STENCIL", 11)
UI_FONT_ENTRY_BOLD = ("STENCIL", 11, "bold")
UI_FONT_TIME = ("franklin gothic", 10, "bold")
UI_FONT_CENTER = ("0 jadid bold", 15)
UI_FONT_HEADER = ("0 jadid bold", 12)
UI_TOPBAR_FONT = ("NPIYaghooti Regular", 13, "bold")
# ---------------------------------------------------

# ---------------- مدیریت محصولات (Name / حرف BachNo) ----------------
# هر محصول یک نام (که در لیبل پرینتر جلوی Name: چاپ می‌شود) و یک حرف (که
# بلافاصله بعد از BachNo: می‌آید، مثلاً C برای FDG) دارد. این لیست در یک
# فایل JSON در پوشه‌ی AppData ذخیره می‌شود تا حتی بعد از بستن و باز کردن
# دوباره‌ی برنامه (و حتی بعد از اجرا به‌صورت exe) باقی بماند.
PRODUCTS_CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "NADEF18")
PRODUCTS_CONFIG_FILE = os.path.join(PRODUCTS_CONFIG_DIR, "products.json")

# نکته: "letter" دیگر فقط یک حرف تکی نیست — می‌تواند یک پیشوند چندکاراکتری
# (حرف + عدد) مثل "C020" یا "S058" باشد که بلافاصله بعد از BachNo: و قبل از
# تاریخ چاپ می‌شود. "C020" همان مقدار پیش‌فرض قبلی برنامه است (حرف C + عدد 020
# که قبلاً به‌صورت ثابت در کد نوشته شده بود).
DEFAULT_PRODUCTS = {"FDG": "C020"}   # نام: پیشوند BachNo — همان مقدار پیش‌فرض قبلی برنامه
MAX_BATCH_PREFIX_LEN = 12   # سقف طول پیشوند، فقط برای جلوگیری از مقادیر نامعقول


def load_products():
    """لیست محصولات را از فایل ذخیره‌شده می‌خواند؛ اگر فایل وجود نداشت یا خراب
    بود، مقدار پیش‌فرض (FDG: C020) برگردانده می‌شود تا رفتار قبلی برنامه حفظ شود."""
    try:
        with open(PRODUCTS_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data:
            return {str(k): (str(v)[:MAX_BATCH_PREFIX_LEN] if str(v) else "C020") for k, v in data.items()}
    except (OSError, ValueError):
        pass
    return DEFAULT_PRODUCTS.copy()


def save_products(products):
    """لیست محصولات را برای همیشه (حتی بعد از بستن برنامه) ذخیره می‌کند."""
    try:
        os.makedirs(PRODUCTS_CONFIG_DIR, exist_ok=True)
        with open(PRODUCTS_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


PRODUCTS = load_products()
CURRENT_PRODUCT_NAME = next(iter(PRODUCTS.keys()), "FDG")
CURRENT_PRODUCT_LETTER = PRODUCTS.get(CURRENT_PRODUCT_NAME, "C020")
# ---------------------------------------------------------------------

# =====================================================================
# هسته‌ی اتصال زنده به دوزکالیبراتور Comecer (خواندن Raw Com. Chambers
# Values از طریق TCP/Ethernet، مشابه نرم‌افزار اصلی Comecer).
# این بخش هیچ وابستگی گرافیکی ندارد و در یک ترد جدا اجرا می‌شود.
# =====================================================================
# ⚠️ نگاشت چمبر خام (01/02) به ظرف فیزیکی واقعی — این مقدار هنوز با قطعیتِ کامل
# (مثلاً با یک تست دسپنس واقعی یا برچسب فیزیکی روی خودِ دستگاه) تأیید نشده؛ فقط بر
# اساس نزدیک‌ترین تطبیق عددی که تا این لحظه مشاهده شده تنظیم شده. اگر بعداً معلوم شد
# برعکس است، کافی است فقط همین دو خط را جابه‌جا کنید — جای دیگری از کد نیاز به تغییر ندارد.
CHAMBER_ID_FOR_VIK203 = "02"   # ظرف دوز بیمار (Patient dose vial) → لیبل پرینتر (Activity:)
CHAMBER_ID_FOR_VIK202 = "01"   # ظرف بالک/مادر (Bulk/mother vial) → entry0 (Whole Activity)

DEFAULT_COMECER_CONFIG = {
    "host": "127.0.0.1",
    "ethernet_port": 11111,
    "bytes_to_read": 50,
    "ms_wait_next_chamber": 100,
    "ms_wait_start_loop": 100,
    "line_terminator": "auto",   # auto | \n | \r\n | \r
    # نکته: NADEF18 عمداً هیچ‌وقت چیزی روی این اتصال TCP نمی‌فرستد — فقط
    # منفعلانه گوش می‌دهد. فرمان '!R' که در Serial Port Monitor دیده شد،
    # بین خودِ دوزکالیبراتور و IBC-lite (روی COM) رد و بدل می‌شود؛ به آن
    # اتصال سریال اصلاً دسترسی نداریم و نباید هم داشته باشیم. تنها کاری که
    # NADEF18 باید بکند، خواندن هرچه IBC-lite خودش روی TCP:11111 پخش
    # می‌کند است — بدون هیچ مزاحمتی برای ارتباط IBC-lite/دوزکالیبراتور.
}


_RECORD_START_RE = re.compile(rb"\d{2},[A-Za-z]")  # الگوی شروع هر رکورد: شناسه‌ی چمبر (۲ رقم) + کاما + شروع نام ایزوتوپ


@dataclass
class ChamberReading:
    chamber_id: str
    isotope: str
    activity: float          # ⚠️ این یک مقدار مرجع/کالیبراسیون تقریباً ثابت است، نه اکتیویته‌ی زنده — برای اکتیویته‌ی واقعی از live_activity_mci استفاده کنید
    field4_raw: str          # نیمه‌عمر خام، مثل '000001.830H'
    checksum_field: str      # ⚠️ نامش گمراه‌کننده است؛ این فیلد در واقع مقدار زنده و دیکی‌شونده‌ی اکتیویته (raw counts) است
    refresh_counter: int
    trailing_field: str
    raw_line: str
    timestamp: datetime

    @staticmethod
    def parse(raw_line: str) -> "ChamberReading":
        parts = [p.strip() for p in raw_line.strip().split(",")]
        if len(parts) < 7:
            raise ValueError(f"Incomplete record (fields={len(parts)}): {raw_line!r}")
        chamber_id, isotope, activity_str, field4, checksum, counter_str, trailing = parts[:7]
        return ChamberReading(
            chamber_id=chamber_id,
            isotope=isotope,
            activity=float(activity_str),
            field4_raw=field4,
            checksum_field=checksum,
            refresh_counter=int(counter_str),
            trailing_field=trailing,
            raw_line=raw_line.strip(),
            timestamp=datetime.now(),
        )

    @property
    def half_life_minutes(self) -> Optional[float]:
        try:
            raw = self.field4_raw.strip()
            hl_hours = float(raw[:-1]) if raw and raw[-1].isalpha() else float(raw)
            return hl_hours * 60.0
        except (ValueError, IndexError):
            return None

    # ضریب تبدیل «شمارش خام / mCi» — از روی دو جفت داده‌ی مستقل (از دو جلسه‌ی
    # کاملاً متفاوت) به‌دست آمده:
    #   ۱) checksum_field=1075  <->  Activity واقعی=29.05 mCi  →  نسبت 37.005
    #   ۲) checksum_field=26    <->  Activity واقعی=0.6938 mCi →  نسبت 37.475
    # این دو مقدار مستقل فقط ۱.۲۶٪ با هم اختلاف دارند و هر دو رفتار دیکی
    # نمایی این فیلد را با نیمه‌عمر واقعی F-18 (از روی field4_raw) با دقت
    # بالا تأیید کردند؛ میانگین این دو، ۳۷.۲۴، به‌عنوان ضریب نهایی استفاده
    # می‌شود. اگر بعداً داده‌ی دقیق‌تری (مخصوصاً برای ایزوتوپ‌های دیگر) به
    # دست آمد، فقط کافی است همین یک عدد را اصلاح کنید.
    RAW_COUNTS_PER_MCI = 37.00

    @property
    def live_activity_mci(self) -> Optional[float]:
        """اکتیویته‌ی واقعی و زنده بر حسب mCi — بر خلاف فیلد activity (که یک
        مقدار مرجع/کالیبراسیون تقریباً ثابت است)، این مقدار از روی
        checksum_field (که واقعاً بر اساس نیمه‌عمر ایزوتوپ دیکی می‌شود)
        محاسبه می‌شود."""
        try:
            raw_counts = float(self.checksum_field.strip())
        except (ValueError, AttributeError):
            return None
        return raw_counts / self.RAW_COUNTS_PER_MCI


class ComecerReader:
    """خواننده‌ی TCP که در ترد پس‌زمینه اجرا می‌شود؛ برای هر رکورد جدید
    یکی از callbackها را صدا می‌زند: on_reading / on_status / on_error.
    نکته: این callbackها در ترد جدا اجرا می‌شوند، پس مستقیم ویجت
    Tkinter را از داخل آن‌ها آپدیت نکنید — فقط در صف بگذارید (به تابع
    comecer_drain_queue در پایین این فایل نگاه کنید)."""

    def __init__(self, config: dict,
                 on_reading: Callable[["ChamberReading"], None],
                 on_status: Callable[[str], None] = lambda s: None,
                 on_error: Callable[[str], None] = lambda e: None):
        self.config = config
        self.on_reading = on_reading
        self.on_status = on_status
        self.on_error = on_error
        self._sock = None
        self._stop_event = threading.Event()
        self._thread = None
        self._last_counter = None   # شمارنده سراسری بین چمبرها
        self._record_len = None     # طول واقعی هر رکورد (خودکار از روی داده کشف می‌شود، نه فرضی)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        try:
            if self._sock:
                self._sock.close()
        except OSError:
            pass

    def _run(self):
        host = self.config["host"]
        port = int(self.config["ethernet_port"])
        bytes_to_read = int(self.config["bytes_to_read"])
        wait_next_chamber = int(self.config["ms_wait_next_chamber"]) / 1000.0
        wait_start_loop = int(self.config["ms_wait_start_loop"]) / 1000.0

        try:
            self.on_status(f"Connecting to {host}:{port} ...")
            self._sock = socket.create_connection((host, port), timeout=5)
            self._sock.settimeout(1.0)
            self.on_status(f"Connected to {host}:{port}")
        except OSError as e:
            self.on_error(f"Connection error: {e}")
            return

        buffer = b""
        while not self._stop_event.is_set():
            try:
                data = self._sock.recv(bytes_to_read)
                if not data:
                    self.on_error("Connection closed by server.")
                    break
                # --- تشخیصی: نمایش خودِ بایت‌های خام دریافتی، پیش از هر پردازشی ---
                # طول نمایش محدود می‌شود تا از عرض نوار وضعیت بیرون نزند (چون این متن
                # فاصله ندارد و Tkinter نمی‌تواند آن را به‌صورت خودکار بشکند).
                preview = repr(data)
                if len(preview) > 100:
                    preview = preview[:100] + "...'"
                self.on_status(f"RX {len(data)}B: {preview}")
                buffer += data
                lines, buffer = self._split_lines(buffer)
                for raw_line in lines:
                    if not raw_line.strip():
                        continue
                    try:
                        reading = ChamberReading.parse(raw_line.decode(errors="replace"))
                    except ValueError as e:
                        self.on_error(str(e))
                        continue
                    self._check_missed_counter(reading)
                    self.on_reading(reading)
                    time.sleep(wait_next_chamber)
            except socket.timeout:
                pass
            except OSError as e:
                if not self._stop_event.is_set():
                    self.on_error(f"Communication error: {e}")
                break

            time.sleep(wait_start_loop)

        try:
            if self._sock:
                self._sock.close()
        except OSError:
            pass
        self.on_status("Connection closed.")

    def _split_lines(self, buffer: bytes):
        term = self.config.get("line_terminator", "auto")
        if term == "auto":
            for t in (b"\r\n", b"\n", b"\r"):
                if t in buffer:
                    term = t
                    break
            else:
                # پروتکل واقعی Comecer نه کاراکتر پایان‌خط دارد و نه هیچ جداکننده‌ای
                # بین دو رکورد پشت‌سرهم — رکورد بعدی بلافاصله بعد از رکورد قبلی شروع
                # می‌شود. طول هر رکورد را به‌جای حدس‌زدن (که قبلاً اشتباه ۵۰ فرض شده
                # بود، در حالی که واقعی‌اش ۴۷ بایت است)، مستقیماً از روی خودِ داده کشف
                # می‌کنیم: دنبال الگوی «دو رقم + کاما + حرف» (شروع شناسه‌ی چمبر + شروع
                # نام ایزوتوپ) می‌گردیم — این الگو دقیقاً ابتدای هر رکورد است. فاصله‌ی
                # بین دو وقوع متوالی همین الگو، طول واقعی یک رکورد کامل را می‌دهد.
                matches = [m.start() for m in _RECORD_START_RE.finditer(buffer)]
                if len(matches) >= 2:
                    self._record_len = matches[1] - matches[0]
                    start_offset = matches[0]
                elif matches:
                    start_offset = matches[0]
                else:
                    start_offset = None

                if start_offset is None or self._record_len is None:
                    # هنوز طول رکورد کشف نشده یا هیچ شروع رکوردی پیدا نشد؛ منتظر
                    # داده‌ی بیشتر می‌مانیم (با محدودیت رشد بافر برای اطمینان).
                    if len(buffer) > 4096:
                        return [], buffer[-256:]
                    return [], buffer

                aligned = buffer[start_offset:]
                record_len = self._record_len
                n_complete = len(aligned) // record_len
                if n_complete == 0:
                    return [], aligned
                complete = aligned[: n_complete * record_len]
                remainder = aligned[n_complete * record_len:]
                lines = [complete[i:i + record_len] for i in range(0, len(complete), record_len)]
                return lines, remainder
        else:
            term = term.encode().replace(b"\\r", b"\r").replace(b"\\n", b"\n")
        parts = buffer.split(term)
        return parts[:-1], parts[-1]

    def _check_missed_counter(self, reading: "ChamberReading"):
        if self._last_counter is not None:
            expected = self._last_counter + 1
            if reading.refresh_counter != expected:
                self.on_error(
                    f"⚠️ Possible missed count: expected {expected}, "
                    f"got {reading.refresh_counter} (chamber {reading.chamber_id})"
                )
        self._last_counter = reading.refresh_counter
# =====================================================================
# پایان هسته اتصال Comecer
# =====================================================================
# ---------------------------------------------------
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# path=resource_path0(relative):

window.iconbitmap(resource_path("barlogo.ico"))
# ---------------------------------------------------
# تابع محاسباتی---------------------------------------
def allesFunc():
    time_format = "%H:%M"
    for act in list4:
        act.delete(0, END)
    # برای ریست کردن مقدار دریافتی entry
    for low in list3:
        low.delete(0, END)
    for vol in list5:
        vol.delete(0, END)
    for te in list6:
        te.delete(0, END)
# ---------------------------------------------------------
    entry_sum_A.delete(0, END)
    entry_sum_V.delete(0, END)
    # محاسبه اکتیویته یک میلی لیتر دارو
    if entry0.get() == '':
        print("Please enter whole activity")
    else:
        if (entry0.get()).isdigit() == True and (entry01.get()).isdigit() == True:
            if int(entry0.get()) > 0 and int(entry01.get()) > 0:
                answer = int(entry0.get())/int(entry01.get())
                print(answer)
            else:
                print("input are below zero")
        else:
            print("input are not number")
    if entry02.get() == '':
        print("enter valid start dispense time")
    else:
        if bool(parser.parse(entry02.get())) == True:
            print("start dispense time format is OK")
        else:
            print(ValueError())
    #   محاسبه زمان تزریق اول هر مرکز--------------
    if check_1.get():
        for t0 in list2:
            t0.delete(0, END)
        if entry03.get() !='':
            #  پیام
            payam_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) + timedelta(minutes=95)
            entry12.insert(0, payam_time.strftime("%H:%M"))

            #  رجائی
            rajaii_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) + timedelta(minutes=125)
            entry22.insert(0, rajaii_time.strftime("%H:%M"))

            #  امام
            emam_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) + timedelta(minutes=100)
            entry32.insert(0, emam_time.strftime("%H:%M"))
            #  شریعتی
            shariati_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) + timedelta(minutes=115)
            entry42.insert(0, shariati_time.strftime("%H:%M"))

            #  خاتم
            khatam_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) +timedelta(minutes=130)
            entry52.insert(0, khatam_time.strftime("%H:%M"))

            #  محک
            mahak_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) + timedelta(minutes=170)
            entry62.insert(0, mahak_time.strftime("%H:%M"))

            # فردوس
            ferdos_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) + timedelta(minutes=120)
            entry72.insert(0, ferdos_time.strftime("%H:%M"))

            # undef1
            undef1_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) + timedelta(minutes=180)
            entry82.insert(0, undef1_time.strftime("%H:%M"))

            # undef2
            undef2_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) + timedelta(minutes=330)
            entry92.insert(0, undef2_time.strftime("%H:%M"))

            # undef3
            undef3_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) + timedelta(minutes=180)
            entry10_2.insert(0, undef1_time.strftime("%H:%M"))

            # undef4
            undef4_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) + timedelta(minutes=330)
            entry11_2.insert(0, undef2_time.strftime("%H:%M"))

            # undef5
            undef5_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) + timedelta(minutes=330)
            entry12_2.insert(0, undef2_time.strftime("%H:%M"))

        else:
            entry03.insert(0, 30)
            payam_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) + timedelta(minutes=95)
            entry12.insert(0, payam_time.strftime("%H:%M"))

            #  رجائی
            rajaii_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) + timedelta(minutes=125)
            entry22.insert(0, rajaii_time.strftime("%H:%M"))

            #  امام
            emam_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) + timedelta(minutes=100)
            entry32.insert(0, emam_time.strftime("%H:%M"))
            #  شریعتی
            shariati_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) + timedelta(minutes=115)
            entry42.insert(0, shariati_time.strftime("%H:%M"))

            #  خاتم
            khatam_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) +timedelta(minutes=130)
            entry52.insert(0, khatam_time.strftime("%H:%M"))

            #  محک
            mahak_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) + timedelta(minutes=170)
            entry62.insert(0, mahak_time.strftime("%H:%M"))

            # فردوس
            ferdos_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) + timedelta(minutes=120)
            entry72.insert(0, ferdos_time.strftime("%H:%M"))

            # undef1
            undef1_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) + timedelta(minutes=210)
            entry82.insert(0, undef1_time.strftime("%H:%M"))

            # undef2
            undef2_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) + timedelta(minutes=360)
            entry92.insert(0, undef2_time.strftime("%H:%M"))

            
            # undef3
            undef3_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) + timedelta(minutes=210)
            entry10_2.insert(0, undef3_time.strftime("%H:%M"))

            # undef4
            undef4_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) + timedelta(minutes=360)
            entry11_2.insert(0, undef4_time.strftime("%H:%M"))

            
            # undef5
            undef5_time = datetime.strptime(
                entry02.get(), time_format) + timedelta(minutes=int(entry03.get())) + timedelta(minutes=210)
            entry12_2.insert(0, undef5_time.strftime("%H:%M"))


    else:
        for t0 in list2:
            if t0.get() == entry02.get():
                t0.delete(0, END)
                t0.insert(0, start_dis_time)
            else:
                pass

    # ایجاد حلقه اصلی-----------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------
    
    counter = 0
    for lm, dose, t0, low, act, vol, te, gb in zip(list0, list1, list2, list3, list4, list5, list6, listGBI):

        time_format = '%H:%M'

        if dose.get() != '':
            req = int(dose.get())
            print(req)
        else:
            req = 0
        print("dose field is empty")

    #    محاسبه اختلا ف زمانی دیسپنس تا تزریق اول
        if t0.get()!='':
            time_sub = datetime.strptime(
                t0.get(), time_format) - datetime.strptime(entry02.get(), time_format)
            print(time_sub.total_seconds() / 60.0)
        else:
            time_sub = 0

    #    محاسبه اکتیویته پایین

        if gb.get() !='':
            gap_time=int(gb.get())
        else:
            gap_time=35

        sump = 0
        for i in range(req):
            num = 10*2**((i*gap_time)/109.771)
            sump += num

        if entry_percent.get() != '' :
            sump=(sump-(int(entry_percent.get())/100)*sump)
        else:
            pass
    #    خروج از حلقه داخلی---------------
        print(gap_time)
        print(int(sump))
        low.insert(0, int(sump))

    #    محاسبه اکتیویته بالا
        if time_sub != 0:
            high_act = sump*pow(2, (time_sub.total_seconds() / 60.0/109.7))
            act.insert(0, int(high_act))
            print(int(high_act))
        
    #              محاسبه حجم لازم برای هر مرکز
            req_vol = (int(high_act)/int(entry0.get()))*int(entry01.get())
            vol.insert(0, float("{:.2f}".format(req_vol)))
            print(float("{:.1f}".format(req_vol)))
    #              محاسبه زمان تزریق بعدی
            interval_time = (req*gap_time)
            Next_time = datetime.strptime(
                t0.get(), time_format) + timedelta(minutes=interval_time)
            print(Next_time.strftime("%H:%M"))
        else:
            pass
        # رنگی کردن تزریق بعد برای فیلدهای مراکزی که درخواست دارند---------------
        if dose.get() != '':
           te.insert(0, Next_time.strftime("%H:%M"))
           bg_color = lm.cget("background")
           te.config(bg=bg_color)
        else:
        # برگرداندن رنگ تزریق بعد به حالت اولیه برای درخواستهای خالی----------
           default_rgb = te.winfo_rgb("SystemButtonFace") # get default RGB color
           default_hex = '#' + ''.join([hex(c)[2:].zfill(2) for c in default_rgb]) # convert to hex string
           te.config(bg=default_hex) # set background color to default

        counter += 1
    for dose, t0, low, act, vol in zip(list1, list2, list3, list4, list5):
        if dose.get() == '':
            t0.delete(0, END)
            low.delete(0, END)
            act.delete(0, END)
            vol.delete(0, END)
        else:
            pass
        
    #    خروج از حلقه اصلی ---------------------------------
    #        ------------------------------------------------------------------------------------
    #    مجموع اکتیویته بالا
    Sum_act = 0
    for act in list4:
        if act.get() != '':
           Sum_act += float("{:.2f}".format(float(act.get())))
        else:
            act.get() == 0
    entry_sum_A.insert(0, Sum_act)
    #    مجموع حجم مراکز
    Sum_vol = 0
    for vol in list5:
        if vol.get() != '':
           Sum_vol += float(vol.get())
        else:
            vol.get() == 0
    entry_sum_V.insert(0, "{:.2f}".format(Sum_vol))

    # Add these common parameters to each Label creation
    common_params = {
        'bg': "black",
        'font': ("NPIYaghooti Regular", 16),
        'width': 36,
        'anchor': 'nw',
        'justify': 'left'
    }

    if Sum_vol > float(entry01.get())-1.0 and entry_percent.get() !='':
        wlabel = Label(frame2, text=f'Required Activity Is Over, Even With {entry_percent.get()} Percent Off', fg="#EC1526", **common_params)
        wlabel.grid(row=0, column=0, sticky='nw', padx=4, pady=2)

    elif Sum_vol < float(entry01.get())-1.0 and entry_percent.get() !='':
        wlabel = Label(frame2, text=f' !!!Required Activity Is Enough With {entry_percent.get()} Percent Off!!!', fg="#21EE10", **common_params)
        wlabel.grid(row=0, column=0, sticky='nw', padx=4, pady=2)

    elif Sum_vol > float(entry01.get())-1.0:
        print("not ok")
        wlabel = Label(frame2, text=" !!! Required Activity Is Over !!!", fg="#EC1526", **common_params)
        wlabel.grid(row=0, column=0, sticky='nw', padx=4, pady=2)

    else:
        wlabel = Label(frame2, text=" "u'\u2713'"Activity Is Enough", fg="#21EE10", **common_params)
        wlabel.grid(row=0, column=0, sticky='nw', padx=4, pady=2)

    print(check_1.get())  
# -----------------------------------------------------------------------------------------------------
    # ردیف 0
frame0 = Frame(window)
frame0.grid(row=0, padx=0, pady=4)
frame0.configure(bg='#154360')

lable0 = Label(frame0, text="Whole Activity:", fg="#000000", font=UI_TOPBAR_FONT, width=13).grid(row=0, column=0, padx=4)
entry0 = add_debug(Entry(frame0, font=UI_FONT_ENTRY, bd=2, relief='solid',
               bg="#D5DBDB", width=UI_ENTRY_W + 1, justify='center'), 'entry0')
entry0.grid(row=0, column=1, padx=6)
lable01 = Label(frame0, text="Whole volume:", fg="#000000", font=UI_TOPBAR_FONT, width=14).grid(row=0, column=2, padx=6)
entry01 = add_debug(Entry(frame0, font=UI_FONT_ENTRY,
                bg="#D5DBDB", width=UI_ENTRY_W, justify='center'), 'entry01')
entry01.grid(row=0, column=3, padx=2)
entry01.insert(0, 40)
lable02 = Label(frame0, text="D.S Time:", fg="#000000", font=UI_TOPBAR_FONT).grid(row=0, column=4, padx=2)
entry02 = add_debug(Entry(frame0, font=UI_FONT_ENTRY,
                bg="#D5DBDB", width=7, justify='center'), 'entry02')
start_dis_time = time.strftime('%H:%M')
entry02.insert(0, start_dis_time)
entry02.grid(row=0, column=5, padx=2)
entry03 = add_debug(Entry(frame0, font=UI_FONT_ENTRY_BOLD, bg="#D5DBDB", width=4, justify='center'), 'entry03')
entry03.grid(row=0, column=8, padx=1)
btn = add_debug(Button(frame0, text="Run", fg="#000000", bg="red", font=UI_TOPBAR_FONT, width=5, command=allesFunc), 'btn')
btn.grid(row=0, column=6)
# ------------------------------------------------------
#مدت زمان دیسپنس
# -------------------------------------------------------
lable03 = Label(frame0, text="G.T:", fg="#000000", font=UI_TOPBAR_FONT).grid(row=0, column=7, padx=2)
entry03 = Entry(frame0, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=4, justify='center')
entry03.grid(row=0, column=8, padx=1)

# دکمه‌های Settings / Report / Advance — هر سه در یک ستون (9)، با عرض/ارتفاع یکسان
# (width/height صریح روی هر سه) و sticky='new' تا دقیقاً زیر هم و هم‌عرض بمانند
# (قبلاً چون هر متن طول متفاوتی داشت، عرض دکمه‌ها با هم یکی نبود).
UI_TOPBTN_WIDTH = 12
UI_TOPBTN_HEIGHT = 1

btn_settings = Button(frame0, text="\u2699 Settings", fg="#000000", bg="#D5DBDB",
                      font=UI_TOPBAR_FONT, width=UI_TOPBTN_WIDTH, height=UI_TOPBTN_HEIGHT,
                      command=lambda: open_print_settings_window())
btn_settings.grid(row=0, column=9, padx=6, pady=(6, 0), sticky='new')

btn_report = Button(frame0, text="\U0001F4C4 Report", fg="#000000", bg="#D5DBDB",
                    font=UI_TOPBAR_FONT, width=UI_TOPBTN_WIDTH, height=UI_TOPBTN_HEIGHT,
                    command=lambda: generate_dispense_report())
btn_report.grid(row=1, column=9, padx=6, pady=(6, 0), sticky='new')

# دکمه Advance — مدیریت نام محصولات و حرف BachNo (طبق راهنمای تصویر، محل شماره 3)
btn_advance = Button(frame0, text="Advance", fg="#000000", bg="#D5DBDB",
                     font=UI_TOPBAR_FONT, width=UI_TOPBTN_WIDTH, height=UI_TOPBTN_HEIGHT,
                     command=lambda: open_advance_window())
btn_advance.grid(row=2, column=9, padx=6, pady=(6, 0), sticky='new')

# ----------------- پنل اتصال زنده به دوزکالیبراتور Comecer -----------------
comecer_gui_queue = queue.Queue()
comecer_reader_holder = {"reader": None, "last_reading": None}

# رنگ پنل هماهنگ با نوار بالای صفحه (همان تیره‌ی سرمه‌ای frame0) تا با ظاهر برنامه یکدست باشد
COMECER_BG = '#154360'
COMECER_FG = 'white'
COMECER_VALUE_FG = '#F5C518'   # طلایی، برای مقادیر زنده (هم‌رنگ با تاکیدهای دیگر برنامه)
COMECER_FONT = ("NPIYaghooti Regular", 10, "bold")
COMECER_VALUE_FONT = ("STENCIL", 11)

frame_comecer = Frame(frame0, bg=COMECER_BG)
frame_comecer.grid(row=1, column=0, columnspan=9, pady=(2, 2), padx=2, sticky='ew')

Label(frame_comecer, text="Comecer Host:", bg=COMECER_BG, fg=COMECER_FG, font=COMECER_FONT).grid(
    row=0, column=0, padx=(6, 2), pady=4)
entry_comecer_host = Entry(frame_comecer, width=12, justify='center', bg="#D5DBDB")
entry_comecer_host.insert(0, "127.0.0.1")
entry_comecer_host.grid(row=0, column=1, padx=2)

Label(frame_comecer, text="Port:", bg=COMECER_BG, fg=COMECER_FG, font=COMECER_FONT).grid(
    row=0, column=2, padx=2)
entry_comecer_port = Entry(frame_comecer, width=7, justify='center', bg="#D5DBDB")
entry_comecer_port.insert(0, "11111")
entry_comecer_port.grid(row=0, column=3, padx=2)

comecer_status_var = StringVar(value="Not connected")


def comecer_on_reading(reading):
    comecer_gui_queue.put(("reading", reading))


def comecer_on_status(msg):
    comecer_gui_queue.put(("status", msg))


def comecer_on_error(msg):
    comecer_gui_queue.put(("error", msg))


comecer_state = {"paused": False, "activity_locked": False}   # paused: توقف/ادامه خواندن (کنار Print)؛ activity_locked: قفل Whole Activity

# آخرین رکورد خام دریافتی برای هر چمبر — چون فیلد پنجم (checksum_field) خودش
# مقدار زنده و واقعاً دیکی‌شونده‌ی activity است (نه یک عدد مرجع/کالیبراسیون
# ثابت که نیاز به حدس زدنِ زمان سپری‌شده داشته باشد)، دیگر به baseline/تیکِ
# هرثانیه نیازی نیست — با رسیدن هر رکورد تازه، همان لحظه عدد صحیح نمایش داده
# می‌شود.
comecer_last_reading_by_chamber = {}   # chamber_id -> ChamberReading

# ----------------- پنل لاگ (برای دیباگ/عیب‌یابی بعدی) -----------------
# همه‌ی رویدادهای اتصال Comecer (وضعیت، بایت‌های خام دریافتی، خطاها، رکوردهای
# پارس‌شده) اینجا با زمان دقیق ذخیره می‌شوند تا در صورت بروز مشکل، بتوان کل
# لاگ را ذخیره/کپی کرد و برای بررسی بعدی فرستاد — بدون نیاز به کنسول (که در
# نسخه‌ی نهایی/exe اصلاً دیده نمی‌شود).
comecer_log_lines = []          # لیست کامل خطوط لاگ (رشته)
comecer_log_window_ref = {"win": None, "text": None}   # مرجع پنجره‌ی لاگ، اگر باز باشد


def comecer_log(text):
    """یک خط را با برچسب زمان به بافر لاگ اضافه می‌کند و اگر پنجره‌ی لاگ باز
    است، همان‌جا هم زنده نمایش می‌دهد (با اسکرول خودکار به آخرین خط)."""
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"[{ts}] {text}"
    comecer_log_lines.append(line)
    # محدود کردن اندازه‌ی بافر تا حافظه بی‌رویه رشد نکند (۵۰۰۰ خط آخر کافی است)
    if len(comecer_log_lines) > 5000:
        del comecer_log_lines[: len(comecer_log_lines) - 5000]
    win = comecer_log_window_ref.get("win")
    txt = comecer_log_window_ref.get("text")
    if win is not None and txt is not None:
        try:
            txt.insert("end", line + "\n")
            txt.see("end")
        except TclError:
            comecer_log_window_ref["win"] = None
            comecer_log_window_ref["text"] = None


def comecer_save_log_to_file():
    path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        initialfile=f"comecer_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        title="ذخیره‌ی لاگ Comecer")
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(comecer_log_lines))
        messagebox.showinfo("لاگ ذخیره شد", f"لاگ در این مسیر ذخیره شد:\n{path}")
    except OSError as e:
        messagebox.showerror("خطا در ذخیره", str(e))


def comecer_clear_log():
    comecer_log_lines.clear()
    txt = comecer_log_window_ref.get("text")
    if txt is not None:
        try:
            txt.delete("1.0", "end")
        except TclError:
            pass


def comecer_open_log_window():
    """پنجره‌ی لاگ را باز می‌کند (یا اگر باز است، به جلو می‌آورد)."""
    existing = comecer_log_window_ref.get("win")
    if existing is not None:
        try:
            existing.deiconify()
            existing.lift()
            return
        except TclError:
            pass  # پنجره‌ی قبلی بسته شده بود؛ یکی تازه می‌سازیم

    log_win = Toplevel(window)
    log_win.title("Comecer Log — برای دیباگ/عیب‌یابی")
    log_win.geometry("760x480")

    toolbar = Frame(log_win)
    toolbar.pack(fill="x", padx=6, pady=4)
    Button(toolbar, text="💾 Save to File", command=comecer_save_log_to_file).pack(side="left", padx=4)
    Button(toolbar, text="🗑 Clear", command=comecer_clear_log).pack(side="left", padx=4)

    text_frame = Frame(log_win)
    text_frame.pack(fill="both", expand=True, padx=6, pady=(0, 6))
    scrollbar = Scrollbar(text_frame)
    scrollbar.pack(side="right", fill="y")
    log_text = Text(text_frame, wrap="none", font=("Consolas", 9),
                     yscrollcommand=scrollbar.set)
    log_text.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=log_text.yview)

    # لاگ‌های قبلی (قبل از باز شدن این پنجره) را هم نشان بده
    if comecer_log_lines:
        log_text.insert("1.0", "\n".join(comecer_log_lines) + "\n")
        log_text.see("end")

    comecer_log_window_ref["win"] = log_win
    comecer_log_window_ref["text"] = log_text

    def _on_close():
        comecer_log_window_ref["win"] = None
        comecer_log_window_ref["text"] = None
        log_win.destroy()

    log_win.protocol("WM_DELETE_WINDOW", _on_close)


btn_comecer_log = Button(frame_comecer, text="📋 Log", bg="#D5DBDB",
                         command=comecer_open_log_window)
btn_comecer_log.grid(row=0, column=9, padx=(10, 6))
# ----------------- پایان پنل لاگ -----------------

# ----------------- دکمه قفل/آزاد Whole Activity -----------------
def comecer_toggle_activity_lock():
    """وقتی قفل است، مقدار entry0 (Whole Activity) دیگر با هر رکورد جدید از
    VIK-202 بازنویسی نمی‌شود و کاربر می‌تواند آزادانه آن را تایپ یا پاک کند؛
    وقتی دوباره باز شود، به‌روزرسانی زنده‌ی خودکار از سر گرفته می‌شود."""
    comecer_state["activity_locked"] = not comecer_state["activity_locked"]
    if comecer_state["activity_locked"]:
        btn_lock_activity.config(text="\U0001F512 Unlock Whole Activity", bg="#E67E22", fg="white")
    else:
        btn_lock_activity.config(text="\U0001F513 Lock Whole Activity", bg="#D5DBDB", fg="black")


btn_lock_activity = Button(frame_comecer, text="\U0001F513 Lock Whole Activity", bg="#D5DBDB", fg="black",
                           font=COMECER_FONT, command=comecer_toggle_activity_lock)
btn_lock_activity.grid(row=0, column=4, columnspan=5, padx=6, pady=4, sticky='ew')
# ----------------- پایان دکمه قفل Whole Activity -----------------


def comecer_update_activity_line(value_text):
    """به‌روزرسانی خط 'Activity:' در کادر گزارش/چاپ (text_field) با مقدار زنده activity.
    این تابع بعد از ساخته‌شدن text_field (پایین‌تر در فایل) صدا زده می‌شود؛ چون
    فراخوانی واقعی هنگام اجرای برنامه (بعد از بالا آمدن کل GUI) اتفاق می‌افتد، مشکلی
    از نظر ترتیب تعریف در فایل ایجاد نمی‌شود."""
    try:
        text = text_field.get("1.0", "end-1c")
    except NameError:
        return   # text_field هنوز ساخته نشده (خیلی زود فراخوانی شده)
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if line.startswith("Activity:"):
            lines[i] = f"Activity: {value_text}"
            break
    else:
        lines.insert(1, f"Activity: {value_text}")
    text_field.delete("1.0", "end")
    text_field.insert("1.0", '\n'.join(lines))
    comecer_recompute_a_activity()


def comecer_recompute_a_activity():
    """هر بار که خط Activity: تغییر می‌کند صدا زده می‌شود. اگر در خط Time: یک
    'Cal Time:HH:MM' معتبر درج شده باشد (مثلاً با کلیک روی نام یک مرکز)، مقدار
    A-Activity با افت پرتوزایی از همین لحظه تا آن ساعت محاسبه می‌شود؛ در غیر
    این صورت (هیچ ساعتی درج نشده)، A-Activity دقیقاً برابر Activity می‌شود."""
    try:
        text = text_field.get("1.0", "end-1c")
    except NameError:
        return
    lines = text.split('\n')

    current_activity_val = 0.0
    cal_time_str = ""
    for line in lines:
        if line.startswith("Activity:"):
            raw = line.replace("Activity:", "").replace("mCi", "").strip()
            try:
                current_activity_val = float(raw)
            except ValueError:
                current_activity_val = 0.0
        elif line.startswith("Time:") and "Cal Time:" in line:
            cal_time_str = line.split("Cal Time:", 1)[1].strip()

    if cal_time_str:
        a_activity_val = compute_a_activity(current_activity_val, cal_time_str, datetime.now())
    else:
        a_activity_val = int(current_activity_val)

    for i, line in enumerate(lines):
        if line.startswith("A-Activity:"):
            lines[i] = f"A-Activity: {a_activity_val} mCi"
            break
    else:
        lines.insert(2, f"A-Activity: {a_activity_val} mCi")

    text_field.delete("1.0", "end")
    text_field.insert("1.0", '\n'.join(lines))


def comecer_handle_reading(reading):
    comecer_reader_holder["last_reading"] = reading
    comecer_last_reading_by_chamber[reading.chamber_id] = reading

    # نکته‌ی مهم (اصلاح‌شده): فیلد activity یک مقدار مرجع/کالیبراسیون تقریباً
    # ثابت است، نه اکتیویته‌ی زنده. اکتیویته‌ی واقعی و زنده از روی
    # checksum_field محاسبه می‌شود (که با فرمول دیکی نمایی F-18 و نیمه‌عمر
    # واقعی‌اش کاملاً مطابقت دارد — تأییدشده با دو جفت داده‌ی مستقل).
    activity_mci = reading.live_activity_mci
    if activity_mci is None:
        comecer_log(f"PARSE WARNING: could not compute live activity for chamber={reading.chamber_id} "
                    f"raw_line={reading.raw_line!r}")
        return
    comecer_log(f"PARSED: chamber={reading.chamber_id} isotope={reading.isotope} "
                f"checksum_field={reading.checksum_field} -> {activity_mci:.3f} mCi "
                f"counter={reading.refresh_counter} raw_line={reading.raw_line!r}")

    # --- جدول RAW + Activity: برای هر دو ظرف، همیشه و مستقل از دکمه‌ها ---
    if reading.chamber_id in comecer_raw_vars:
        comecer_raw_vars[reading.chamber_id].set(reading.raw_line)
        comecer_clear_raw_error(reading.chamber_id)   # داده معتبر تازه رسید -> رنگ خطا پاک شود
    if reading.chamber_id in comecer_activity_vars:
        comecer_activity_vars[reading.chamber_id].set(f"{activity_mci:.3f} mCi  ({reading.isotope})")

    if reading.chamber_id == CHAMBER_ID_FOR_VIK202 and not comecer_state["activity_locked"]:
        # ظرف بالک/مادر → مستقیم و پیوسته در entry0 (Whole Activity) نوشته می‌شود؛
        # مگر این‌که کاربر با دکمه‌ی قفل، این مقدار را ثابت نگه داشته باشد (در آن
        # حالت، entry0 دیگر بازنویسی نمی‌شود و با تایپ/پاک‌کردن قابل اصلاح است).
        entry0.delete(0, "end")
        entry0.insert(0, f"{activity_mci:.3f}")

    if reading.chamber_id == CHAMBER_ID_FOR_VIK203 and not comecer_state["paused"]:
        # ظرف دوز بیمار → خط Activity: در لیبل چاپ؛ اگر Stop زده شده، این
        # بلوک اصلاً اجرا نمی‌شود و مقدار قبلی دست‌نخورده باقی می‌ماند.
        comecer_update_activity_line(format_activity_mci(activity_mci))


def comecer_show_message(text, color="#FF6B6B"):
    """پیام‌های وضعیت/خطا حالا در پنل لاگ داخلی (قابل مشاهده و ذخیره از داخل
    خودِ برنامه، حتی در نسخه‌ی exe که کنسول ندارد) ثبت می‌شوند؛ پیام‌های خطا
    علاوه‌بر آن مستقیم در همان دو ردیف RAW مربوط به VIK-202/VIK-203 هم نشان
    داده می‌شوند (متن قرمز) تا در همان لحظه دیده شوند."""
    comecer_log(text)
    print(f"[Comecer] {text}")   # برای اجرای مستقیم از ترمینال هم همچنان چاپ می‌شود


def comecer_drain_queue():
    try:
        while True:
            kind, payload = comecer_gui_queue.get_nowait()
            if kind == "reading":
                comecer_handle_reading(payload)
            elif kind == "status":
                comecer_status_var.set(payload)
                comecer_show_message(payload, color="#7EC8FF")   # آبی روشن برای وضعیت عادی
            elif kind == "error":
                comecer_status_var.set("Error")
                comecer_show_message(f"Comecer error: {payload}", color="#FF6B6B")
                comecer_show_error_in_raw(payload)
    except queue.Empty:
        pass
    window.after(150, comecer_drain_queue)


def comecer_toggle_connect():
    if comecer_reader_holder["reader"] is None:
        try:
            cfg = DEFAULT_COMECER_CONFIG.copy()
            cfg["host"] = entry_comecer_host.get().strip()
            cfg["ethernet_port"] = int(entry_comecer_port.get().strip())
        except ValueError:
            comecer_show_message("Error: Port must be a number.", color="#FF6B6B")
            return
        reader = ComecerReader(cfg, on_reading=comecer_on_reading,
                                on_status=comecer_on_status, on_error=comecer_on_error)
        reader.start()
        comecer_reader_holder["reader"] = reader
    else:
        comecer_reader_holder["reader"].stop()
        comecer_reader_holder["reader"] = None
        comecer_show_message("Comecer connection closed.", color="#7EC8FF")

# ----------------- جدول RAW + Activity برای هر ظرف (VIK-202 / VIK-203) -----------------
# طبق راهنمای تصویر: به‌جای ردیف‌های قبلی Live/Sel/VIK-202 (که فقط یک عدد نشان
# می‌دادند)، یک جدول با ۴ ستون برای هر ظرف: نام ظرف، شماره ردیف، متن RAW زنده‌ی
# دریافتی، و مقدار Activity محاسبه‌شده — هر دو ظرف هم‌زمان و همیشه قابل مشاهده،
# مستقل از انتخاب dropdown، تا مقایسه و دیباگ راحت‌تر باشد.
comecer_meter_rows = [
    ("VIK-202", CHAMBER_ID_FOR_VIK202),
    ("VIK-203", CHAMBER_ID_FOR_VIK203),
]
comecer_raw_vars = {}        # chamber_id -> StringVar (متن RAW زنده یا پیام خطا)
comecer_raw_labels = {}      # chamber_id -> Label widget (برای تغییر رنگ هنگام خطا)
comecer_activity_vars = {}   # chamber_id -> StringVar (Activity محاسبه‌شده به mCi)

for _i, (_meter_name, _chamber_id) in enumerate(comecer_meter_rows):
    _row = _i + 1
    Label(frame_comecer, text=_meter_name, bg="white", fg="black", relief="solid", bd=1,
          font=("Segoe UI", 10, "bold"), width=9).grid(
        row=_row, column=0, padx=2, pady=2, sticky='w')
    Label(frame_comecer, text=str(_i + 1), bg="white", fg="black", relief="solid", bd=1,
          font=("Segoe UI", 10, "bold"), width=2).grid(
        row=_row, column=1, padx=2, pady=2)

    _raw_var = StringVar(value="")
    _raw_label = Label(frame_comecer, textvariable=_raw_var, bg="white", fg="black", relief="solid", bd=1,
                       font=("Consolas", 9), anchor='w', justify='left', width=42)
    _raw_label.grid(row=_row, column=2, columnspan=4, padx=2, pady=2, sticky='ew')
    comecer_raw_vars[_chamber_id] = _raw_var
    comecer_raw_labels[_chamber_id] = _raw_label

    _activity_var = StringVar(value="")
    Label(frame_comecer, textvariable=_activity_var, bg="white", fg="black", relief="solid", bd=1,
          font=("Segoe UI", 10, "bold"), anchor='center', width=16).grid(
        row=_row, column=6, columnspan=3, padx=2, pady=2, sticky='ew')
    comecer_activity_vars[_chamber_id] = _activity_var


def comecer_show_error_in_raw(text):
    """طبق درخواست، خطاها به‌جای (یا علاوه‌بر) کنسول، مستقیم در همان دو ردیف
    RAW مربوط به VIK-202/VIK-203 نشان داده می‌شوند (متن قرمز، جایگزین متن RAW
    عادی) تا در همان لحظه‌ی دیدن جدول، خطا هم دیده شود. اگر بشود چمبر مربوط
    به خطا را از خودِ متن پیام تشخیص داد (مثلاً '...(chamber 01)')، فقط همان
    ردیف قرمز می‌شود؛ در غیر این صورت (خطاهای عمومی مثل قطع اتصال)، هر دو
    ردیف قرمز می‌شوند چون به هر دو چمبر مربوط است."""
    m = re.search(r"chamber (\d{2})", text)
    target_chambers = [m.group(1)] if m else list(comecer_raw_vars.keys())
    for cid in target_chambers:
        if cid in comecer_raw_vars:
            comecer_raw_vars[cid].set(f"ERROR: {text}")
            comecer_raw_labels[cid].config(fg="#C0392B")


def comecer_clear_raw_error(chamber_id):
    """وقتی یک رکورد معتبر جدید برای یک چمبر برسد، رنگ آن ردیف را به حالت
    عادی (سیاه) برمی‌گرداند — یعنی خطا دیگر فعلی/جاری نیست."""
    if chamber_id in comecer_raw_labels:
        comecer_raw_labels[chamber_id].config(fg="black")
# ----------------- پایان جدول RAW + Activity -----------------

window.after(150, comecer_drain_queue)
window.after(300, comecer_toggle_connect)   # اتصال خودکار، بدون نیاز به دکمه Connect
# ----------------- پایان پنل Comecer -----------------

# ------------- فریم اصلی ---------------------------------------------------------------

frame1 = Frame(window,bg='#adad85')
frame1.grid(row=1, column=0, columnspan=9, pady=(2, 2), padx=6, sticky='ew')
for _col in range(9):
    frame1.grid_columnconfigure(_col, weight=1)
for _row in range(16):
    frame1.grid_rowconfigure(_row, minsize=0)

# ------GBI فواصل بین تزریق مراکز---------------------------------------------------
entryGB1 = Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center')
entryGB1.grid(row=2, column=0, padx=UI_COL_PAD)

entryGB2 = Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center')
entryGB2.grid(row=3, column=0)

entryGB3 = Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center')
entryGB3.grid(row=4, column=0)

entryGB4 = Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center')
entryGB4.grid(row=5, column=0)

entryGB5 = Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center')
entryGB5.grid(row=6, column=0)

entryGB6 = Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center')
entryGB6.grid(row=7, column=0)

entryGB7 = Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center')
entryGB7.grid(row=8, column=0)

entryGB8 = Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center')
entryGB8.grid(row=9, column=0)

entryGB9 = Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center')
entryGB9.grid(row=10, column=0)

entryGB10 = Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center'
                )
entryGB10.grid(row=11, column=0)

entryGB11 = Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center')
entryGB11.grid(row=12, column=0)

entryGB12 = Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center')
entryGB12.grid(row=13, column=0)

# ------------- ردیف عناوین---------------------------------------------------------------

label_GBI=Label(frame1, text="GBI", fg="black",
                    bg='#adad85', font=UI_FONT_HEADER).grid(row=1, column=0)
label_centername = Label(frame1, text="center name", fg="black",
                    bg='#adad85', font=UI_FONT_HEADER).grid(row=1, column=1)
label_ReqNumber = Label(frame1, text="Req\nNumber", fg="black",
                    bg='#adad85', font=UI_FONT_HEADER).grid(row=1, column=2)
label_FirstInjTime = Label(frame1, text="First\nInj\nTime", fg="black",
                    bg='#adad85', font=UI_FONT_HEADER).grid(row=1, column=3)
label_DeliveryTimeActivity = Label(frame1, text="Delivery\nTime\nActivity", fg="black",
                    bg='#adad85', font=UI_FONT_HEADER).grid(row=1, column=4)
label_DispenseTimeActivity = Label(frame1, text="Dispense\nTime\nActivity", fg="black",
                    bg='#adad85', font=UI_FONT_HEADER).grid(row=1, column=5)
label_NeededVolume = Label(frame1, text="Needed\nVolume", fg="black",
                    bg='#adad85', font=UI_FONT_HEADER).grid(row=1, column=6)
label_NextDispenseTime = Label(frame1, text="Next\nDispense\nTime", fg="black",
                    bg='#adad85', font=UI_FONT_HEADER).grid(row=1, column=7)

# ردیف پیام

label_payam = add_debug(Entry(frame1, fg="#00001a", bg='#ffa31a', font=UI_FONT_CENTER, width=UI_CENTER_W, justify=LEFT), 'label_payam')
label_payam.grid(row=2, column=1)
label_payam.insert(0, "Payam  :")
# ------------------------------------------------------------
entry11 = add_debug(Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center'), 'entry11')
entry11.grid(row=2, column=2)
# ------------------------------------------------------------
entry12 = add_debug(Entry(frame1, font=UI_FONT_TIME,
                bg="#D5DBDB", fg="red", width=5, justify='center'), 'entry12')
entry12.grid(row=2, column=3, padx=UI_COL_PAD)
entry12.insert(0, start_dis_time)

# -------------------------------------------------------------
entry13 = add_debug(Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False), 'entry13')
entry13.grid(row=2, column=4, padx=UI_COL_PAD)
# -------------------------------------------------------------
entry14 = add_debug(Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False), 'entry14')
entry14.grid(row=2, column=5, padx=UI_COL_PAD)
# -------------------------------------------------------------
entry15 = add_debug(Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False), 'entry15')
entry15.grid(row=2, column=6, padx=UI_COL_PAD)
# -------------------------------------------------------------
entry16 = add_debug(Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False), 'entry16')
entry16.grid(row=2, column=7, padx=UI_COL_PAD)

# ردیف رجایی

label_rajaii = Entry(frame1, fg="#00001a", bg='#8A2BE2', font=UI_FONT_CENTER, width=UI_CENTER_W)
label_rajaii.grid(row=3, column=1)
label_rajaii.insert(0, "Rajaii    :")
# ---------------------------------------------------------------
entry21 = Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center')
entry21.grid(row=3, column=2)
# ---------------------------------------------------------------
entry22 = Entry(frame1, font=UI_FONT_TIME,
                bg="#D5DBDB", fg="red", width=5, justify='center')
entry22.grid(row=3, column=3, padx=UI_COL_PAD)
entry22.insert(0, start_dis_time)
# ---------------------------------------------------------------
entry23 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry23.grid(row=3, column=4, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry24 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry24.grid(row=3, column=5, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry25 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry25.grid(row=3, column=6, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry26 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry26.grid(row=3, column=7, padx=UI_COL_PAD)

# ردیف امام

label_emam = Entry(frame1, fg="#00001a", bg='#66ccff', font=UI_FONT_CENTER, width=UI_CENTER_W)
label_emam.grid(row=4, column=1)
label_emam.insert(0, "Emam   :")
# ---------------------------------------------------------------
entry31 = Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center')
entry31.grid(row=4, column=2)
# ---------------------------------------------------------------
entry32 = Entry(frame1, font=UI_FONT_TIME,
                bg="#D5DBDB", fg="red", width=5, justify='center')
entry32.grid(row=4, column=3, padx=UI_COL_PAD)
entry32.insert(0, start_dis_time)
# ---------------------------------------------------------------
entry33 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry33.grid(row=4, column=4, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry34 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry34.grid(row=4, column=5, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry35 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry35.grid(row=4, column=6, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry36 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry36.grid(row=4, column=7, padx=UI_COL_PAD)

# ردیف شریعتی

label_shariati = Entry(frame1, fg="#00001a", bg='#ffff4d', font=UI_FONT_CENTER, width=UI_CENTER_W)
label_shariati.grid(row=5, column=1)
label_shariati.insert(0, "Shariati :")
# ---------------------------------------------------------------
entry41 = Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center')
entry41.grid(row=5, column=2)
# ---------------------------------------------------------------
entry42 = Entry(frame1, font=UI_FONT_TIME,
                bg="#D5DBDB", fg="red", width=5, justify='center')
entry42.grid(row=5, column=3, padx=UI_COL_PAD)
entry42.insert(0, start_dis_time)
# ---------------------------------------------------------------
entry43 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry43.grid(row=5, column=4, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry44 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry44.grid(row=5, column=5, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry45 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry45.grid(row=5, column=6, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry46 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry46.grid(row=5, column=7, padx=UI_COL_PAD)

# ردیف خاتم

label_khatam = Entry(frame1, fg="#00001a", bg='#33cc00', font=UI_FONT_CENTER, width=UI_CENTER_W)
label_khatam.grid(row=6, column=1)
label_khatam.insert(0, "Khatam :")
# ---------------------------------------------------------------
entry51 = Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center')
entry51.grid(row=6, column=2)
# ---------------------------------------------------------------
entry52 = Entry(frame1, font=UI_FONT_TIME,
                bg="#D5DBDB", fg="red", width=5, justify='center')
entry52.grid(row=6, column=3, padx=UI_COL_PAD)
entry52.insert(0, start_dis_time)
# ---------------------------------------------------------------
entry53 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry53.grid(row=6, column=4, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry54 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry54.grid(row=6, column=5, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry55 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry55.grid(row=6, column=6, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry56 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry56.grid(row=6, column=7, padx=UI_COL_PAD)

# ردیف محک

label_mahak = Entry(frame1, fg="#00001a", bg='#ff3300', font=UI_FONT_CENTER, width=UI_CENTER_W)
label_mahak.grid(row=7, column=1)
label_mahak.insert(0, "Mahak  :")
# ---------------------------------------------------------------
entry61 = Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center')
entry61.grid(row=7, column=2)
# ---------------------------------------------------------------
entry62 = Entry(frame1, font=UI_FONT_TIME,
                bg="#D5DBDB", fg="red", width=5, justify='center')
entry62.grid(row=7, column=3, padx=UI_COL_PAD)
entry62.insert(0, start_dis_time)
# ---------------------------------------------------------------
entry63 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry63.grid(row=7, column=4, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry64 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry64.grid(row=7, column=5, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry65 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry65.grid(row=7, column=6, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry66 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry66.grid(row=7, column=7, padx=UI_COL_PAD)

# ردیف فردوس

label_ferdos = Entry(frame1, text="Ferdos  :", fg="#00001a", bg='#660066', font=UI_FONT_CENTER, width=UI_CENTER_W)
label_ferdos.grid(row=8, column=1)
label_ferdos.insert(0,"Ferdos  :")
# ---------------------------------------------------------------
entry71 = Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center')
entry71.grid(row=8, column=2)
# ---------------------------------------------------------------
entry72 = Entry(frame1, font=UI_FONT_TIME,
                bg="#D5DBDB", fg="red", width=5, justify='center')
entry72.grid(row=8, column=3, padx=UI_COL_PAD)
entry72.insert(0, start_dis_time)
# ---------------------------------------------------------------
entry73 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry73.grid(row=8, column=4, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry74 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry74.grid(row=8, column=5, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry75 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry75.grid(row=8, column=6, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry76 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry76.grid(row=8, column=7, padx=UI_COL_PAD)
# ------------------------------------------------------------------------------

# ردیف unknown1

label_entry_undef1 = Entry(frame1, fg="#00001a", bg='#52D9AB', font=UI_FONT_CENTER, width=UI_CENTER_W)
label_entry_undef1.grid(row=9, column=1)
label_entry_undef1.insert(0, " Zanjan :")
# ---------------------------------------------------------------
entry81 = Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center')
entry81.grid(row=9, column=2)
# ---------------------------------------------------------------
entry82 = Entry(frame1, font=UI_FONT_TIME,
                bg="#D5DBDB", fg="red", width=5, justify='center')
entry82.grid(row=9, column=3, padx=UI_COL_PAD)
entry82.insert(0, start_dis_time)
# ---------------------------------------------------------------
entry83 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry83.grid(row=9, column=4, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry84 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry84.grid(row=9, column=5, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry85 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry85.grid(row=9, column=6, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry86 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry86.grid(row=9, column=7, padx=UI_COL_PAD)
# ------------------------------------------------------------------------------
# ردیف unknown2

label_entry_undef2 = Entry(frame1, fg="#00001a", bg='#8568C3', font=UI_FONT_CENTER, width=UI_CENTER_W)
label_entry_undef2.grid(row=10, column=1)
label_entry_undef2.insert(0, ' Tabriz   :')
# ---------------------------------------------------------------
entry91 = Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center')
entry91.grid(row=10, column=2)
# ---------------------------------------------------------------
entry92 = Entry(frame1, font=UI_FONT_TIME,
                bg="#D5DBDB", fg="red", width=5, justify='center')
entry92.grid(row=10, column=3, padx=UI_COL_PAD)
entry92.insert(0, start_dis_time)
# ---------------------------------------------------------------
entry93 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry93.grid(row=10, column=4, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry94 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry94.grid(row=10, column=5, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry95 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry95.grid(row=10, column=6, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry96 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry96.grid(row=10, column=7, padx=UI_COL_PAD)
# ------------------------------------------------------------------------------
# ردیف unknown3

label_entry_undef3 = Entry(frame1, fg="#00001a", bg='#DC57AE', font=UI_FONT_CENTER, width=UI_CENTER_W)
label_entry_undef3.grid(row=11, column=1)
label_entry_undef3.insert(0, 'DR.I : ')
# ---------------------------------------------------------------
entry10_1 = Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center')
entry10_1.grid(row=11, column=2)
# ---------------------------------------------------------------
entry10_2 = Entry(frame1, font=UI_FONT_TIME,
                bg="#D5DBDB", fg="red", width=5, justify='center')
entry10_2.grid(row=11, column=3, padx=UI_COL_PAD)
entry10_2.insert(0, start_dis_time)
# ---------------------------------------------------------------
entry10_3 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry10_3.grid(row=11, column=4, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry10_4 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry10_4.grid(row=11, column=5, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry10_5 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry10_5.grid(row=11, column=6, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry10_6 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry10_6.grid(row=11, column=7, padx=UI_COL_PAD)
# ----------------------------------------------------------------------------------
# ردیف unknown4

label_entry_undef4 = Entry(frame1, fg="#00001a", bg='#8EC8D0', font=UI_FONT_CENTER, width=UI_CENTER_W)
label_entry_undef4.grid(row=12, column=1)
label_entry_undef4.insert(0, 'Sina : ')
# ---------------------------------------------------------------
entry11_1 = Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center')
entry11_1.grid(row=12, column=2)
# ---------------------------------------------------------------
entry11_2 = Entry(frame1, font=UI_FONT_TIME,
                bg="#D5DBDB", fg="red", width=5, justify='center')
entry11_2.grid(row=12, column=3, padx=UI_COL_PAD)
entry11_2.insert(0, start_dis_time)
# ---------------------------------------------------------------
entry11_3 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry11_3.grid(row=12, column=4, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry11_4 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry11_4.grid(row=12, column=5, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry11_5 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry11_5.grid(row=12, column=6, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry11_6 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry11_6.grid(row=12, column=7, padx=UI_COL_PAD)
# ----------------------------------------------------------------------------------
# ردیف unknown5

label_entry_undef5 = Entry(frame1, fg="#00001a", bg='#B2E31A', font=UI_FONT_CENTER, width=UI_CENTER_W)
label_entry_undef5.grid(row=13, column=1)
label_entry_undef5.insert(0, 'Sanandaj:')
# ---------------------------------------------------------------
entry12_1 = Entry(frame1, font=UI_FONT_ENTRY_BOLD,
                bg="#D5DBDB", width=5, justify='center')
entry12_1.grid(row=13, column=2)
# ---------------------------------------------------------------
entry12_2 = Entry(frame1, font=UI_FONT_TIME,
                bg="#D5DBDB", fg="red", width=5, justify='center')
entry12_2.grid(row=13, column=3, padx=UI_COL_PAD)
entry12_2.insert(0, start_dis_time)
# ---------------------------------------------------------------
entry12_3 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry12_3.grid(row=13, column=4, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry12_4 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry12_4.grid(row=13, column=5, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry12_5 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry12_5.grid(row=13, column=6, padx=UI_COL_PAD)
# ---------------------------------------------------------------
entry12_6 = Entry(frame1, font=UI_FONT_ENTRY, width=UI_ENTRY_W, justify='center',takefocus=False)
entry12_6.grid(row=13, column=7, padx=UI_COL_PAD)
# ----------------------------------------------------------------------------------
# تعریف تابع کاهش و افزایش زمان تزریق اول مراکز
    
# زمان تزریق اول
list2 = [entry12, entry22, entry32, entry42,
         entry52, entry62, entry72, entry82, entry92, entry10_2, entry11_2, entry12_2]

def plus_first_inj(t0):
    
     time_format = '%H:%M'
     added_time = datetime.strptime(t0.get(), time_format) + timedelta(minutes=5)
     f = open("myfile.txt", "a")
     f = open("myfile.txt", "w")
     f.write(str(added_time))
     t0.delete(0, END)
     t0.insert(0, added_time.strftime("%H:%M"))
     f.close()
     os.remove("myfile.txt")
def minus_first_inj(t0):
     time_format = '%H:%M'
     added_time = datetime.strptime(t0.get(), time_format) - timedelta(minutes=5)
     f = open("myfile.txt", "a")
     f = open("myfile.txt", "w")
     f.write(str(added_time))
     t0.delete(0, END)
     t0.insert(0, added_time.strftime("%H:%M"))
     f.close()
     os.remove("myfile.txt")    
 
#  ---------------------------------------------------
 # دکمه های کم و زیاد زمان اولین تزریق
btn_payam_frame=Frame(frame1)
btn_payam_frame.grid(row=2, column=3, sticky="e")

btn_plus_payam = Button(btn_payam_frame, text="+", fg="#000000", bg="green", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[0]:plus_first_inj(t0))
btn_plus_payam.grid(row=0, column=0)
btn_minus_payam = Button(btn_payam_frame, text="-", fg="#000000", bg="red", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[0]:minus_first_inj(t0))
btn_minus_payam.grid(row=1, column=0)
# -------------------------
btn_rajaii_frame=Frame(frame1)
btn_rajaii_frame.grid(row=3, column=3, sticky="e")

btn_plus_rajaii = Button(btn_rajaii_frame, text="+", fg="#000000", bg="green", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[1]:plus_first_inj(t0))
btn_plus_rajaii.grid(row=0, column=0)
btn_minus_rajaii = Button(btn_rajaii_frame, text="-", fg="#000000", bg="red", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[1]:minus_first_inj(t0))
btn_minus_rajaii.grid(row=1, column=0)
# -------------------------


btn_emam_frame=Frame(frame1)
btn_emam_frame.grid(row=4, column=3, sticky="e")

btn_plus_emam = Button(btn_emam_frame, text="+", fg="#000000", bg="green", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[2]:plus_first_inj(t0))
btn_plus_emam.grid(row=0, column=0)
btn_minus_emam = Button(btn_emam_frame, text="-", fg="#000000", bg="red", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[2]:minus_first_inj(t0))
btn_minus_emam.grid(row=1, column=0)
# -------------------------
btn_shariati_frame=Frame(frame1)
btn_shariati_frame.grid(row=5, column=3, sticky="e")

btn_plus_shariati = Button(btn_shariati_frame, text="+", fg="#000000", bg="green", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[3]:plus_first_inj(t0))
btn_plus_shariati.grid(row=0, column=0)
btn_minus_shariati = Button(btn_shariati_frame, text="-", fg="#000000", bg="red", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[3]:minus_first_inj(t0))
btn_minus_shariati.grid(row=1, column=0)
# -------------------------
btn_khatam_frame=Frame(frame1)
btn_khatam_frame.grid(row=6, column=3, sticky="e")

btn_plus_khatam = Button(btn_khatam_frame, text="+", fg="#000000", bg="green", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[4]:plus_first_inj(t0))
btn_plus_khatam.grid(row=0, column=0)
btn_minus_khatam = Button(btn_khatam_frame, text="-", fg="#000000", bg="red", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[4]:minus_first_inj(t0))
btn_minus_khatam.grid(row=1, column=0)
# -------------------------
btn_mahak_frame=Frame(frame1)
btn_mahak_frame.grid(row=7, column=3, sticky="e")

btn_plus_mahak = Button(btn_mahak_frame, text="+", fg="#000000", bg="green", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[5]:plus_first_inj(t0))
btn_plus_mahak.grid(row=0, column=0)
btn_minus_mahak = Button(btn_mahak_frame, text="-", fg="#000000", bg="red", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[5]:minus_first_inj(t0))
btn_minus_mahak.grid(row=1, column=0)
# -------------------------
btn_ferdos_frame=Frame(frame1)
btn_ferdos_frame.grid(row=8, column=3, sticky="e")

btn_plus_ferdos = Button(btn_ferdos_frame, text="+", fg="#000000", bg="green", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[6]:plus_first_inj(t0))
btn_plus_ferdos.grid(row=0, column=0)
btn_minus_ferdos = Button(btn_ferdos_frame, text="-", fg="#000000", bg="red", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[6]:minus_first_inj(t0))
btn_minus_ferdos.grid(row=1, column=0)
# -------------------------

btn_undef1_frame=Frame(frame1)
btn_undef1_frame.grid(row=9, column=3, sticky="e")

btn_plus_undef1 = Button(btn_undef1_frame, text="+", fg="#000000", bg="green", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[7]:plus_first_inj(t0))
btn_plus_undef1.grid(row=0, column=0)
btn_minus_undef1 = Button(btn_undef1_frame, text="-", fg="#000000", bg="red", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[7]:minus_first_inj(t0))
btn_minus_undef1.grid(row=1, column=0)
# -------------------------

btn_undef2_frame=Frame(frame1)
btn_undef2_frame.grid(row=10, column=3, sticky="e")

btn_plus_undef2 = Button(btn_undef2_frame, text="+", fg="#000000", bg="green", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[8]:plus_first_inj(t0))
btn_plus_undef2.grid(row=0, column=0)
btn_minus_undef2 = Button(btn_undef2_frame, text="-", fg="#000000", bg="red", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[8]:minus_first_inj(t0))
btn_minus_undef2.grid(row=1, column=0)
# -------------------------
btn_undef3_frame=Frame(frame1)
btn_undef3_frame.grid(row=11, column=3, sticky="e")

btn_plus_undef3 = Button(btn_undef3_frame, text="+", fg="#000000", bg="green", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[9]:plus_first_inj(t0))
btn_plus_undef3.grid(row=0, column=0)
btn_minus_undef3 = Button(btn_undef3_frame, text="-", fg="#000000", bg="red", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[9]:minus_first_inj(t0))
btn_minus_undef3.grid(row=1, column=0)
# -------------------------

btn_undef4_frame=Frame(frame1)
btn_undef4_frame.grid(row=12, column=3, sticky="e")

btn_plus_undef4 = Button(btn_undef4_frame, text="+", fg="#000000", bg="green", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[10]:plus_first_inj(t0))
btn_plus_undef4.grid(row=0, column=0)
btn_minus_undef4 = Button(btn_undef4_frame, text="-", fg="#000000", bg="red", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[10]:minus_first_inj(t0))
btn_minus_undef4.grid(row=1, column=0)
# -------------------------
btn_undef5_frame=Frame(frame1)
btn_undef5_frame.grid(row=13, column=3, sticky="e")

btn_plus_undef5 = Button(btn_undef5_frame, text="+", fg="#000000", bg="green", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[11]:plus_first_inj(t0))
btn_plus_undef5.grid(row=0, column=0)
btn_minus_undef5 = Button(btn_undef5_frame, text="-", fg="#000000", bg="red", takefocus=False, font=(
    "cooper black", 6, "bold"), width=3, height=1, command=lambda t0=list2[11]:minus_first_inj(t0))
btn_minus_undef5.grid(row=1, column=0)

#   ردیف مجموع  و حالت دستی
# چک باکس
#  ایجاد چک باتون


def check1Clicked():
    if check_1.get():
        print('Checkbox 1 selected')
    else:
        print('Checkbox 1 unselected')


check_1 = IntVar()
check_but_1 = Checkbutton(frame1, text='Auto fill time', variable=check_1,
                          onvalue=1, offvalue=0, command=check1Clicked)
check_but_1.grid(row=14, column=3)

# مجموع — این دو مستقیماً در همان ستون‌های اصلی جدول (frame1) قرار می‌گیرند،
# دقیقاً زیر همان ستونی که هر entry در ردیف‌های بالا دارد (column=5 زیر
# «Dispense Time Activity» و column=6 زیر «Needed Volume»)، تا label زیر
# entry بالای خودش بماند، نه در یک زیر-فریم جدا با چیدمان مستقل.
entry_sum_A = Entry(frame1, font=("STENCIL", 12), takefocus=False, width=8, justify='center')
entry_sum_A.grid(row=14, column=5, padx=3)
label_sum_A = Label(frame1, text=" Activity Sum ", font=("0 jadid bold", 11, "bold"),
                    bg='#adad85')
label_sum_A.grid(row=15, column=5, pady=0, ipady=0)

entry_sum_V = Entry(frame1, font=("STENCIL", 12), takefocus=False, width=8, justify='center')
entry_sum_V.grid(row=14, column=6, padx=3)
label_sum_V = Label(frame1, text=" Volume Sum ", font=("0 jadid bold", 10, "bold"),
                    bg='#adad85')
label_sum_V.grid(row=15, column=6, pady=0, ipady=0)


# ------------------------------درصد کاهش 

label_enter=Label(frame1,text="apply", font=("0 jadid bold", 11, "bold"),bg='#DA8416')
label_enter.grid(row=14, column=0, padx=0, pady=2)

entry_percent = Entry(frame1, fg="#000000", bg='yellow', font=UI_TOPBAR_FONT, justify='center', width=9)
entry_percent.grid(row=14, column=1)


label_percent=Label(frame1,text=" %  off  ", font=("0 jadid bold", 11, "bold"),bg='#DA8416')
label_percent.grid(row=14, column=2)

# ----------------پنجره اخطار--------

frame2 = Frame(window, height=55, bg="black")
frame2.grid(row=2, pady=0, padx=0, columnspan=3, sticky='ew')
window.grid_columnconfigure(0, weight=1)
window.grid_rowconfigure(0, weight=0)
window.grid_rowconfigure(1, weight=0)
window.grid_rowconfigure(2, weight=0)

# Configure columns in frame2
frame2.grid_columnconfigure(0, weight=1)  # For wlabel
frame2.grid_columnconfigure(1, weight=0)  # For PRINT/Stop buttons
frame2.grid_columnconfigure(2, weight=0)  # For text_field

wlabel = Label(frame2, text="", fg="#EC1526", bg="black", font=("0 jadid bold", 16), width=30, height=1, anchor='nw', justify='left')
wlabel.grid(row=0, column=0, padx=0, sticky="nsew")

# -------------------- تابع پرینت لیبل--------------------
# Assuming frame1 and frame2 are already defined


# Persian date calculator
def get_persian_date_code():
    try:
        from persiantools.jdatetime import JalaliDate
    except ImportError:
        return f"BachNo:{CURRENT_PRODUCT_LETTER}000000-01/"  # fallback if package not installed
    today = JalaliDate.today()
    year = today.year % 100  # last two digits
    month = today.month
    day = today.day
    return f"BachNo:{CURRENT_PRODUCT_LETTER}{year:02d}{month:02d}{day:02d}-01/"

text_field = Text(frame2, height=6, width=33)
text_field.grid(row=0, column=2, sticky="e")
persian_date = f"Time: {datetime.now().strftime('%H:%M')} - --:--"

# Function to update the '15 ml container/ ml' line with the selected value

# Improved: update on FocusIn, allow float, and always update the line
def update_container_line(event):
    widget = event.widget
    value = widget.get()
    try:
        float_value = float(value)
        is_number = True
    except ValueError:
        is_number = False
    if is_number:
        text = text_field.get("1.0", "end-1c")
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'container/ ' in line and 'ml' in line:
                # Replace with new value before the last 'ml'
                before = line.split('container/')[0] + 'container/ '
                lines[i] = f"{before}{value} ml"
                break
        text_field.delete("1.0", "end")
        text_field.insert("1.0", '\n'.join(lines))

# Insert initial text
text_field.insert("1.0", f"Name:{CURRENT_PRODUCT_NAME}\nActivity: 0 mCi\nA-Activity: 0 mCi\n{persian_date}\n15 ml container/ ml\n" + get_persian_date_code())


def apply_product_selection(name, letter):
    """محصول انتخاب‌شده در پنجره‌ی Advance را روی لیبل پرینتر اعمال می‌کند:
    خط Name: و پیشوندِ (حرف+عدد، مثل C020 یا S058) بعد از BachNo: به‌روز
    می‌شوند؛ بقیه‌ی متن (تاریخ، پسوند مرکز و ...) دست‌نخورده باقی می‌ماند.

    چون این پیشوند حالا می‌تواند چند کاراکتری باشد (نه فقط یک حرف)، برای این‌که
    بدانیم دقیقاً چند کاراکتر از ابتدای خط BachNo باید با پیشوند جدید عوض شود،
    طول پیشوندِ *فعلی* (CURRENT_PRODUCT_LETTER، قبل از اعمال تغییر) را مبنا
    قرار می‌دهیم."""
    global CURRENT_PRODUCT_NAME, CURRENT_PRODUCT_LETTER
    old_letter = CURRENT_PRODUCT_LETTER
    CURRENT_PRODUCT_NAME = name
    CURRENT_PRODUCT_LETTER = letter
    text = text_field.get("1.0", "end-1c")
    lines = text.split('\n')
    name_found = False
    for i, line in enumerate(lines):
        if line.startswith("Name:"):
            lines[i] = f"Name:{name}"
            name_found = True
            break
    if not name_found:
        lines.insert(0, f"Name:{name}")
    bach_found = False
    for i, line in enumerate(lines):
        if line.startswith("BachNo:"):
            rest = line[len("BachNo:"):]
            if old_letter and rest.startswith(old_letter):
                # حالت معمول: پیشوند فعلی همان چیزی است که انتظار داریم، پس
                # دقیقاً همان تعداد کاراکتر را با پیشوند جدید جایگزین می‌کنیم.
                suffix = rest[len(old_letter):]
            else:
                # اگر به هر دلیلی متن دستی ویرایش شده و با پیشوند قبلی مطابقت
                # نداشت، باز هم به همان تعداد کاراکتر از ابتدا صرف‌نظر می‌کنیم
                # تا تاریخ/پسوند بعد از آن خراب نشود.
                suffix = rest[len(old_letter):] if old_letter else rest
            lines[i] = "BachNo:" + letter + suffix
            bach_found = True
            break
    if not bach_found:
        lines.append(get_persian_date_code())
    text_field.delete("1.0", "end")
    text_field.insert("1.0", '\n'.join(lines))


# Bind only the specified Entry widgets to update the label on FocusIn
for entry in [entry15, entry25, entry35, entry45, entry55, entry65, entry75, entry85, entry95, entry10_5]:
    entry.bind('<FocusIn>', update_container_line)

# ---------------- تنظیمات چاپ برچسب (مطابق صفحه Calibration نرم‌افزار اصلی Comecer) ----------------
# ⚠️ مقادیر زیر را با نام دقیق پرینتر و اندازه واقعی حاشیه‌ها/فونت خودتان تنظیم کنید.
# این مقادیر از روی تصویر صفحه Calibration نرم‌افزار اصلی گرفته شده‌اند:
#   Default Printer Name: Brother QL-820NWB (Copy 1)
#   Top Margin: 0.2   Left Margin: 0.4   Bottom Margin: 0.2   Right Margin: 0.4   (فرض بر اینچ)
#   Font Size: 9   (پوینت)
# نکته مهم: چون پرینتر برادر QL معمولاً از قبل در تنظیمات ویندوز (Printer Properties)
# روی اندازه صحیح برچسب تنظیم شده (همان چیزی که در تصویر با نام "Copy 1" دیده می‌شود)،
# این کد عمداً اندازه کاغذ (PaperSize/PaperWidth/PaperLength) را دستکاری نمی‌کند —
# چون اندازه‌های سفارشی در درایورهای Brother QL معمولاً با شناسه‌های اختصاصی درایور
# تعریف می‌شوند و override کردن دستی آن‌ها در کد می‌تواند غلط از آب دربیاید. به‌جایش
# فقط از حاشیه‌ها و فونت (که در تصویر شما مشخص بودند) برای چیدمان متن استفاده می‌شود.
COMECER_PRINTER_NAME = "Brother QL-820NWB (Copy 1)"   # اگر None باشد از پرینتر پیش‌فرض ویندوز استفاده می‌شود
PRINT_MARGIN_TOP_IN = 0.0
PRINT_MARGIN_LEFT_IN = 0.0
PRINT_MARGIN_BOTTOM_IN = 0.2
PRINT_MARGIN_RIGHT_IN = 0.4
PRINT_FONT_SIZE_PT = 9
PRINT_FONT_NAME = "Tahoma"


def print_text():
    """ارسال محتوای text_field به پرینتر انتخاب‌شده (COMECER_PRINTER_NAME).
    بررسی صورت‌گرفته روی این تابع:
    - نام پرینتر باید دقیقاً با نامی که در Windows > Devices and Printers ثبت شده یکی باشد
      (حروف بزرگ/کوچک و فاصله‌ها هم باید دقیقاً یکسان باشند)، وگرنه OpenPrinter/CreatePrinterDC خطا می‌دهد.
    - اگر COMECER_PRINTER_NAME هیچ‌کدام از پرینترهای نصب‌شده را match نکند یا پرینتر آفلاین/خاموش باشد،
      این تابع حالا آن را می‌گیرد و به‌جای کرش خاموش، یک پیام خطای واضح به کاربر نشان می‌دهد.
    - بعد از StartDoc/StartPage، متن با TextOut نوشته و EndPage/EndDoc صدا زده می‌شود که همان
      چیزی است که واقعاً کار چاپ (ارسال job به صف‌ی پرینتر ویندوز) را انجام می‌دهد؛ اگر تا اینجا
      بدون Exception برسد، یعنی دستور چاپ واقعاً به پرینتر/صف چاپ ویندوز ارسال شده است.
    """
    hprinter = None
    hdc = None
    try:
        printer_name = COMECER_PRINTER_NAME or win32print.GetDefaultPrinter()

        hprinter = win32print.OpenPrinter(printer_name)

        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(printer_name)

        # DPI واقعی پرینتر را می‌گیریم تا حاشیه (اینچ) و فونت (پوینت) را درست به پیکسل تبدیل کنیم
        dpi_x = hdc.GetDeviceCaps(win32con.LOGPIXELSX)
        dpi_y = hdc.GetDeviceCaps(win32con.LOGPIXELSY)

        left_px = int(PRINT_MARGIN_LEFT_IN * dpi_x)
        top_px = int(PRINT_MARGIN_TOP_IN * dpi_y)

        # فرمول استاندارد ویندوز برای تبدیل اندازه فونت از پوینت به واحد LOGFONT.height
        font_height = -int(PRINT_FONT_SIZE_PT * dpi_y / 72)
        font = win32ui.CreateFont({
            "name": PRINT_FONT_NAME,
            "height": font_height,
            "weight": 400,
        })
        hdc.SelectObject(font)

        hdc.StartDoc("Dose Label - NADEF18")
        hdc.StartPage()

        text = text_field.get("1.0", END).strip()
        lines = text.split('\n')
        line_height_px = int(abs(font_height) * 1.4)   # فاصله بین خطوط، کمی بیشتر از ارتفاع فونت
        y = top_px
        for line in lines:
            hdc.TextOut(left_px, y, line)
            y += line_height_px

        hdc.EndPage()
        hdc.EndDoc()

        # ثبت متن این لیبل در تاریخچه‌ی همان batch (برای گزارش کامل مراکز پرینت‌شده)
        batch_key = extract_batch_name(text) or "DispenseReport"
        print_history_by_batch.setdefault(batch_key, []).append(text)

        messagebox.showinfo("Print", f"Print job sent to '{printer_name}' successfully.")
        return True

    except Exception as ex:
        messagebox.showerror(
            "Print Error",
            "Sending the print job failed.\n\n"
            f"Printer name: {COMECER_PRINTER_NAME}\n"
            f"Error: {ex}\n\n"
            "Check: Settings button \u2192 that the printer name exactly matches "
            "an installed Windows printer, and that it is on/online."
        )
        return False

    finally:
        try:
            if hdc is not None:
                hdc.DeleteDC()
        except Exception:
            pass
        try:
            if hprinter is not None:
                win32print.ClosePrinter(hprinter)
        except Exception:
            pass


def get_app_dir():
    """پوشه‌ی محل قرارگیری فایل اصلی برنامه را برمی‌گرداند (نسخه‌ی exe فریز‌شده
    یا اسکریپت پایتون) — برای ذخیره‌ی فایل‌های گزارش، نه پوشه‌ی موقتی PyInstaller
    که resource_path به آن اشاره می‌کند."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def generate_dispense_report():
    """گزارش کامل تمام لیبل‌هایی که برای batch جاری (همان BachNo لیبل روی صفحه)
    پرینت گرفته شده‌اند را در یک فایل .txt داخل پوشه‌ی 'Dispense report' (کنار
    فایل اصلی برنامه) ذخیره می‌کند. نام فایل از روی مقدار جلوی 'BachNo:' گرفته
    می‌شود، مثل C020050505-01.

    اگر BachNo با دفعه‌ی قبل یکی باشد، همان فایل با تاریخچه‌ی به‌روزشده‌ی همان
    batch بازنویسی می‌شود (یعنی لیبل‌های جدید در ادامه‌ی همان فایل قرار می‌گیرند).
    اگر BachNo متفاوت باشد، چون تاریخچه‌ی آن به‌طور جداگانه نگه‌داری می‌شود، یک
    فایل جدید و مستقل ساخته می‌شود که فقط شامل لیبل‌های همان batch جدید است —
    هیچ اطلاعاتی از batch(های) قبلی در آن نمی‌آید.
    """
    current_text = text_field.get("1.0", "end-1c")
    batch_name = extract_batch_name(current_text) or "DispenseReport"

    entries = print_history_by_batch.get(batch_name, [])
    if not entries:
        messagebox.showwarning("Dispense Report", f"No printed labels recorded yet for batch '{batch_name}'.")
        return

    # --- ساخت پوشه‌ی خروجی کنار فایل اصلی برنامه ---
    report_dir = os.path.join(get_app_dir(), "Dispense report")
    try:
        os.makedirs(report_dir, exist_ok=True)
    except Exception as ex:
        messagebox.showerror("Dispense Report", f"Could not create report folder:\n{ex}")
        return

    report_path = os.path.join(report_dir, f"{batch_name}.txt")

    try:
        # حالت "w" عمداً استفاده شده: چون entries از قبل شامل تمام لیبل‌های همین
        # batch (قدیمی + جدید) است، بازنویسی کامل فایل معادل «ادامه‌ی همان فایل»
        # است، بدون تکرار محتوا. برای batch متفاوت، چون entries از صفر شروع
        # می‌شود، همین رفتار خودش «فایل جدید و خالی از قبل» را تضمین می‌کند.
        with open(report_path, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(entry)
                f.write("\n" + ("-" * 30) + "\n")
        messagebox.showinfo("Dispense Report", f"Report saved:\n{report_path}")
    except Exception as ex:
        messagebox.showerror("Dispense Report", f"Could not write report file:\n{ex}")


def get_locally_connected_printers():
    """فقط پرینترهایی که واقعاً و به‌صورت فیزیکی به این کامپیوتر وصل هستند را برمی‌گرداند —
    پرینترهای مجازی (Microsoft Print to PDF/XPS، Fax، OneNote و مشابه) و پرینترهای
    شبکه‌ای/متصل‌شده از راه دور در این لیست نمی‌آیند."""
    VIRTUAL_NAME_KEYWORDS = ("pdf", "xps", "fax", "onenote", "document writer", "send to", "journal note")
    VIRTUAL_PORT_PREFIXES = ("FILE:", "PORTPROMPT:", "XPSPORT:", "NUL:", "SHRFAX:")
    result = []
    try:
        printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)
    except Exception:
        printers = []
    for _flags, _description, name, _comment in printers:
        if any(k in name.lower() for k in VIRTUAL_NAME_KEYWORDS):
            continue
        try:
            hprinter = win32print.OpenPrinter(name)
            try:
                info = win32print.GetPrinter(hprinter, 2)
            finally:
                win32print.ClosePrinter(hprinter)
            port_name = (info.get("pPortName") or "").upper()
            if any(port_name.startswith(p) for p in VIRTUAL_PORT_PREFIXES):
                continue
        except Exception:
            pass
        result.append(name)
    return result


# ---------------- پنجره تنظیمات (انتخاب پرینتر + تنظیمات لیبل چاپ) ----------------
def open_print_settings_window():
    global COMECER_PRINTER_NAME, PRINT_MARGIN_TOP_IN, PRINT_MARGIN_LEFT_IN
    global PRINT_MARGIN_BOTTOM_IN, PRINT_MARGIN_RIGHT_IN, PRINT_FONT_SIZE_PT, PRINT_FONT_NAME

    settings_win = Toplevel(window)
    settings_win.title("Print Settings")
    settings_win.configure(bg='#adad85')
    settings_win.resizable(False, False)
    settings_win.transient(window)   # همیشه روی پنجره اصلی بماند، بدون این‌که پنجره اصلی را قفل کند

    # --- لیست پرینترهای واقعاً و فیزیکی به این کامپیوتر متصل (نه مجازی/شبکه‌ای) ---
    available_printers = get_locally_connected_printers()
    if COMECER_PRINTER_NAME and COMECER_PRINTER_NAME not in available_printers:
        available_printers.append(COMECER_PRINTER_NAME)

    Label(settings_win, text="Connected printer:", bg='#adad85', font=UI_TOPBAR_FONT).grid(
        row=0, column=0, padx=6, pady=(10, 4), sticky='w')
    printer_var = StringVar(value=COMECER_PRINTER_NAME or (available_printers[0] if available_printers else ""))
    printer_combo = ttk.Combobox(settings_win, textvariable=printer_var, values=available_printers,
                                 width=30, state="readonly" if available_printers else "normal")
    printer_combo.grid(row=0, column=1, columnspan=2, padx=6, pady=(10, 4), sticky='w')

    def add_setting_row(r, label_text, initial_value):
        Label(settings_win, text=label_text, bg='#adad85', font=UI_TOPBAR_FONT).grid(
            row=r, column=0, padx=6, pady=4, sticky='w')
        e = Entry(settings_win, width=14, justify='center', bg="#D5DBDB")
        e.insert(0, str(initial_value))
        e.grid(row=r, column=1, padx=6, pady=4, sticky='w')
        return e

    e_top = add_setting_row(1, "Top Margin (in):", PRINT_MARGIN_TOP_IN)
    e_left = add_setting_row(2, "Left Margin (in):", PRINT_MARGIN_LEFT_IN)
    e_bottom = add_setting_row(3, "Bottom Margin (in):", PRINT_MARGIN_BOTTOM_IN)
    e_right = add_setting_row(4, "Right Margin (in):", PRINT_MARGIN_RIGHT_IN)
    e_font_size = add_setting_row(5, "Font Size (pt):", PRINT_FONT_SIZE_PT)
    e_font_name = add_setting_row(6, "Font Name:", PRINT_FONT_NAME)

    status_lbl = Label(settings_win, text="", bg='#adad85', fg="#C0392B",
                       font=("Segoe UI", 8), wraplength=320, justify='left')
    status_lbl.grid(row=7, column=0, columnspan=3, padx=6, pady=(2, 0), sticky='w')

    def save_settings():
        global COMECER_PRINTER_NAME, PRINT_MARGIN_TOP_IN, PRINT_MARGIN_LEFT_IN
        global PRINT_MARGIN_BOTTOM_IN, PRINT_MARGIN_RIGHT_IN, PRINT_FONT_SIZE_PT, PRINT_FONT_NAME
        try:
            new_top = float(e_top.get())
            new_left = float(e_left.get())
            new_bottom = float(e_bottom.get())
            new_right = float(e_right.get())
            new_font_size = int(e_font_size.get())
        except ValueError:
            status_lbl.config(text="Margins and font size must be numbers.")
            return
        COMECER_PRINTER_NAME = printer_var.get().strip() or None
        PRINT_MARGIN_TOP_IN = new_top
        PRINT_MARGIN_LEFT_IN = new_left
        PRINT_MARGIN_BOTTOM_IN = new_bottom
        PRINT_MARGIN_RIGHT_IN = new_right
        PRINT_FONT_SIZE_PT = new_font_size
        PRINT_FONT_NAME = e_font_name.get().strip() or PRINT_FONT_NAME
        settings_win.destroy()

    btn_row = Frame(settings_win, bg='#adad85')
    btn_row.grid(row=8, column=0, columnspan=3, pady=(8, 10))
    Button(btn_row, text="Test Print", width=12, command=print_text).grid(row=0, column=0, padx=4)
    Button(btn_row, text="Save", width=12, bg="#1E8449", fg="white", command=save_settings).grid(
        row=0, column=1, padx=4)
    Button(btn_row, text="Cancel", width=12, command=settings_win.destroy).grid(row=0, column=2, padx=4)


# ---------------- پنجره Advance (مدیریت محصولات: نام + حرف BachNo) ----------------
def open_advance_window():
    global PRODUCTS

    adv_win = Toplevel(window)
    adv_win.title("Advance")
    adv_win.configure(bg='#adad85')
    adv_win.resizable(False, False)
    adv_win.transient(window)

    Label(adv_win, text="Product list (Name : BachNo prefix):", bg='#adad85',
         font=UI_TOPBAR_FONT).grid(row=0, column=0, columnspan=4, padx=6, pady=(10, 4), sticky='w')

    products_list = Listbox(adv_win, width=32, height=8, exportselection=False)
    products_list.grid(row=1, column=0, columnspan=4, padx=6, pady=4, sticky='w')

    def refresh_list():
        products_list.delete(0, "end")
        for p_name, p_letter in PRODUCTS.items():
            products_list.insert("end", f"{p_name} : {p_letter}")

    refresh_list()

    Label(adv_win, text="Name:", bg='#adad85', font=UI_TOPBAR_FONT).grid(
        row=2, column=0, padx=6, pady=4, sticky='w')
    e_name = Entry(adv_win, width=16, justify='center', bg="#D5DBDB")
    e_name.grid(row=2, column=1, padx=6, pady=4, sticky='w')

    Label(adv_win, text="Letter:", bg='#adad85', font=UI_TOPBAR_FONT).grid(
        row=2, column=2, padx=6, pady=4, sticky='w')
    # عرض بیشتر تا پیشوندهای چندکاراکتری مثل "C020" یا "S058" هم به‌راحتی جا شوند
    e_letter = Entry(adv_win, width=10, justify='center', bg="#D5DBDB")
    e_letter.grid(row=2, column=3, padx=6, pady=4, sticky='w')

    status_lbl = Label(adv_win, text="", bg='#adad85', fg="#C0392B",
                       font=("Segoe UI", 8), wraplength=340, justify='left')
    status_lbl.grid(row=3, column=0, columnspan=4, padx=6, pady=(0, 4), sticky='w')

    def on_list_select(event=None):
        sel = products_list.curselection()
        if not sel:
            return
        item_text = products_list.get(sel[0])
        p_name, p_letter = [p.strip() for p in item_text.split(":", 1)]
        e_name.delete(0, "end")
        e_name.insert(0, p_name)
        e_letter.delete(0, "end")
        e_letter.insert(0, p_letter)

    products_list.bind("<<ListboxSelect>>", on_list_select)

    def refresh_dropdown():
        select_combo.config(values=list(PRODUCTS.keys()))

    def add_or_update_product():
        p_name = e_name.get().strip()
        p_letter = e_letter.get().strip()
        if not p_name:
            status_lbl.config(text="Name cannot be empty.")
            return
        if not p_letter:
            status_lbl.config(text="Letter cannot be empty.")
            return
        # دیگر فقط یک حرف نگه داشته نمی‌شود — کل پیشوند (حرف+عدد، مثل C020 یا
        # S058) که بعد از BachNo: می‌آید نگه داشته می‌شود (تا سقف معقول).
        p_letter = p_letter[:MAX_BATCH_PREFIX_LEN]
        PRODUCTS[p_name] = p_letter
        if not save_products(PRODUCTS):
            status_lbl.config(text="Could not save to disk (this session's list is still updated).")
        else:
            status_lbl.config(text="")
        refresh_list()
        refresh_dropdown()

    Button(adv_win, text="+ Add / Update", bg="#1E8449", fg="white",
          command=add_or_update_product).grid(row=2, column=4, padx=6, pady=4)

    # --------- انتخاب محصول برای اعمال روی لیبل پرینتر ---------
    Label(adv_win, text="Select for print label:", bg='#adad85', font=UI_TOPBAR_FONT).grid(
        row=4, column=0, columnspan=2, padx=6, pady=(12, 4), sticky='w')

    default_selection = CURRENT_PRODUCT_NAME if CURRENT_PRODUCT_NAME in PRODUCTS else (
        next(iter(PRODUCTS.keys())) if PRODUCTS else "")
    select_var = StringVar(value=default_selection)
    select_combo = ttk.Combobox(adv_win, textvariable=select_var, values=list(PRODUCTS.keys()),
                                width=20, state="readonly")
    select_combo.grid(row=4, column=2, columnspan=2, padx=6, pady=(12, 4), sticky='w')

    def apply_selection():
        p_name = select_var.get().strip()
        if not p_name or p_name not in PRODUCTS:
            status_lbl.config(text="Please select a product from the list.")
            return
        apply_product_selection(p_name, PRODUCTS[p_name])
        adv_win.destroy()

    adv_btn_row = Frame(adv_win, bg='#adad85')
    adv_btn_row.grid(row=5, column=0, columnspan=4, pady=(10, 10))
    Button(adv_btn_row, text="Apply", width=12, bg="#1E8449", fg="white",
          command=apply_selection).grid(row=0, column=0, padx=4)
    Button(adv_btn_row, text="Close", width=12, command=adv_win.destroy).grid(row=0, column=1, padx=4)


btn_action_frame = Frame(frame2, bg="black")
btn_action_frame.grid(row=0, column=1, padx=(4, 6))

btn_print = Button(btn_action_frame, width=12, text="PRINT", fg="white", bg="red", command=print_text)
btn_print.grid(row=0, column=0, pady=(0, 2))


# ---------------- دکمه توقف/ادامه‌ی خواندن زنده activity ----------------
def comecer_toggle_hold():
    comecer_state["paused"] = not comecer_state["paused"]
    if comecer_state["paused"]:
        # هنگام توقف، آخرین مقدار دریافتی مخصوص VIK-203 (نه هر رکورد آخری که از
        # هر چمبری رسیده) را ثابت در خط Activity: نگه می‌داریم.
        last = comecer_last_reading_by_chamber.get(CHAMBER_ID_FOR_VIK203)
        if last is not None and last.live_activity_mci is not None:
            comecer_update_activity_line(format_activity_mci(last.live_activity_mci))
        btn_comecer_hold.config(text="▶ Resume", bg="grey", fg="white")
    else:
        btn_comecer_hold.config(text="⏸ Stop", bg="green", fg="white")


btn_comecer_hold = Button(btn_action_frame, width=12, text="⏸ Stop", fg="white", bg="green",
                          command=comecer_toggle_hold)
btn_comecer_hold.grid(row=1, column=0)






# لوگوی پارس ایزوتوپ-----------------------------------

# --- تنظیم خودکار عرض پنجره ---------------------------------------------
# تا این‌جا تمام ویجت‌های frame0/frame1/frame2 ساخته شده‌اند، پس می‌توانیم
# عرض واقعی مورد نیاز محتوا را بگیریم و پنجره را دقیقاً هم‌اندازه‌ی آن کنیم.
# این کار همان فاصله‌ی خالیِ سمت راست (که با خط آبی در عکس مشخص شده) را حذف
# می‌کند و آن را با حاشیه‌ی سمت چپ یکسان می‌کند، بدون این‌که هیچ ویجتی از
# کادر نمایش خارج شود (چون عرض بر اساس نیاز واقعی ویجت‌ها محاسبه می‌شود).
window.update_idletasks()
FIT_WINDOW_WIDTH = window.winfo_reqwidth()
FIT_WINDOW_HEIGHT = window.winfo_reqheight()
window.geometry(f"{FIT_WINDOW_WIDTH}x{FIT_WINDOW_HEIGHT}+350+10")
# ---------------------------------------------------------------------

img1 = ImageTk.PhotoImage(Image.open(resource_path("firstlogo.png")).resize((FIT_WINDOW_WIDTH, FIT_WINDOW_HEIGHT)))

# صفحه‌ی خوش‌آمد (Splash) — همه‌چیز داخل یک فریم واحد است تا بعداً بتوان
# کل صفحه را یک‌جا و به‌صورت نرم (اسلاید) جمع کرد، نه این‌که ناگهان محو شود.
welcome_frame = Frame(window, bg='#adad85')
welcome_frame.place(x=0, y=0, width=FIT_WINDOW_WIDTH, height=FIT_WINDOW_HEIGHT)

# یک Canvas واحد هم لوگو را نشان می‌دهد و هم انیمیشن مستقیماً رویش رسم می‌شود؛
# چون هر دو روی یک سطح‌اند، دیگر هیچ پس‌زمینه‌ی جداگانه‌ای عکس زیرش را نمی‌پوشاند.
splash_canvas = Canvas(welcome_frame, width=FIT_WINDOW_WIDTH, height=FIT_WINDOW_HEIGHT,
                       highlightthickness=0, bd=0)
splash_canvas.place(x=-2, y=-2)
splash_canvas.create_image(0, 0, image=img1, anchor='nw', tags="bg_logo")


def _draw_radiation_symbol(cx, cy, r, angle_offset):
    """رسم نماد استاندارد رادیواکتیو (زرد/مشکی)، مستقیماً روی همان Canvas لوگو."""
    yellow = "#F5C518"
    dark = "#2b2b1f"
    splash_canvas.delete("radiation")
    splash_canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=dark, width=6,
                              tags="radiation")
    for i in range(3):
        a0 = math.radians(angle_offset + i * 120 - 30)
        a1 = math.radians(angle_offset + i * 120 + 30)
        pts = [cx, cy]
        for s in range(11):
            a = a0 + (a1 - a0) * s / 10
            pts += [cx + r * math.cos(a), cy - r * math.sin(a)]
        splash_canvas.create_polygon(pts, fill=yellow, outline="", tags="radiation")
    splash_canvas.create_oval(cx - r * 0.22, cy - r * 0.22, cx + r * 0.22, cy + r * 0.22,
                              fill=dark, outline="", tags="radiation")


_splash_state = {"step": 0}
_SPLASH_CX = FIT_WINDOW_WIDTH / 2
_SPLASH_CY = FIT_WINDOW_HEIGHT / 2   # دقیقاً وسط صفحه (هم افقی هم عمودی)
_SPLASH_BASE_R = min(FIT_WINDOW_WIDTH, FIT_WINDOW_HEIGHT) * 0.22   # چند برابر بزرگ‌تر از نسخه‌ی قبلی


def _animate_splash():
    step = _splash_state["step"]
    r = _SPLASH_BASE_R + _SPLASH_BASE_R * 0.12 * math.sin(step / 6)
    _draw_radiation_symbol(_SPLASH_CX, _SPLASH_CY, r, angle_offset=step * 7)
    _splash_state["step"] += 1
    if step < 45:   # ~45 فریم × 40ms ≈ 1.8 ثانیه انیمیشن کوتاه
        window.after(40, _animate_splash)
    else:
        splash_canvas.delete("radiation")   # پایان انیمیشن؛ فقط لوگوی اصلی باقی می‌ماند


# -----------------------------------------
# دکمه start صفحه welcome — دقیقاً مثل قبل، در جای ثابت خودش

def on_click():
    _slide_out_welcome()


startbtn = add_debug(Button(welcome_frame, text="START", bg="#235ED4", font=(
    "0 jadid bold", 8, "bold"), width=10, height=2, command=on_click), 'startbtn')
# محل دکمه START: کمی پایین‌تر از کلمه FDG در تصویر لوگو، و از نظر افقی دقیقاً وسط صفحه.
# مقدار اصلیِ y=271 برای ارتفاع ثابت 740 پیکسل تنظیم شده بود؛ چون الان ارتفاع
# پنجره پویا (FIT_WINDOW_HEIGHT) است، همان نسبت قبلی حفظ شده تا مستقل از دستگاه/تنظیمات
# صفحه، باز هم درست زیر FDG بیفتد. (چون به تصویر واقعی logo دسترسی بصری ندارم، اگر
# دقیقاً روی/بالای متن FDG افتاد، همین ضریب 271/740 را کمی کم یا زیاد کنید.)
START_BTN_Y = int(FIT_WINDOW_HEIGHT * (550 / 740))
startbtn.place(relx=0.5, y=START_BTN_Y, anchor='n')


def _slide_out_welcome(step=0):
    """انتقال نرم بین کلیک روی START و باز شدن صفحه‌ی اصلی: کل صفحه‌ی خوش‌آمد
    به‌آرامی به سمت بالا جمع می‌شود (نه محو ناگهانی) و صفحه‌ی اصلی که از قبل
    زیر آن آماده بوده، به‌تدریج نمایان می‌شود."""
    steps = 18
    if step > steps:
        welcome_frame.destroy()
        return
    offset = int(FIT_WINDOW_HEIGHT * (step / steps) ** 2)   # شتاب‌گیری نرم به سمت پایان
    welcome_frame.place(x=0, y=-offset, width=FIT_WINDOW_WIDTH, height=FIT_WINDOW_HEIGHT)
    window.after(16, lambda: _slide_out_welcome(step + 1))


# حالا که صفحه‌ی اصلی و صفحه‌ی خوش‌آمد (روی آن) هر دو کامل ساخته شده‌اند،
# پنجره برای اولین بار نمایش داده می‌شود — بدون هیچ فلیکر یا دیده‌شدن لحظه‌ای صفحه‌ی اصلی.
window.deiconify()
_animate_splash()

# -----------------------------------------
# لیست ردیف بالا مربوط به اکتیویته کل و حجم کل و .... 
listuprow=[entry0, entry01, entry02, entry03]

# لیست ورودی زمان بین تزریق ها GBI----------

listGBI=[entryGB1,entryGB2,entryGB3,entryGB4,
entryGB5,entryGB6,entryGB7,entryGB8,entryGB9,entryGB10,entryGB11,entryGB12]
# ردیف لیبل مراکز
list0=[label_payam, label_rajaii, label_emam, label_shariati, label_khatam, label_mahak, label_ferdos,
label_entry_undef1, label_entry_undef2, label_entry_undef3, label_entry_undef4, label_entry_undef5]
# تعداد دوز درخواستی
list1 = [entry11, entry21, entry31, entry41,
         entry51, entry61, entry71, entry81, entry91, entry10_1, entry11_1,entry12_1]
# زمان تزریق اول
list2 = [entry12, entry22, entry32, entry42,
         entry52, entry62, entry72, entry82, entry92, entry10_2, entry11_2,entry12_2]
# اکتیویته پائین
list3 = [entry13, entry23, entry33, entry43,
         entry53, entry63, entry73, entry83, entry93, entry10_3, entry11_3,entry12_3]
# اکتیویته بالا
list4 = [entry14, entry24, entry34, entry44,
         entry54, entry64, entry74, entry84, entry94, entry10_4, entry11_4,entry12_4]
# حجم لازم
list5 = [entry15, entry25, entry35, entry45,
         entry55, entry65, entry75, entry85, entry95, entry10_5, entry11_5,entry12_5]
# تزریق بعدی
list6 = [entry16, entry26, entry36, entry46,
         entry56, entry66, entry76, entry86, entry96, entry10_6, entry11_6,entry12_6]
#  درصد کاهش
list7=[entry_percent]
# لیست دکمه های افزایش
list8=[btn_plus_payam, btn_plus_rajaii, btn_plus_emam, btn_plus_shariati,
btn_plus_khatam,btn_plus_mahak, btn_plus_ferdos, btn_plus_undef1,btn_plus_undef2]
# لیست دکمه های کاهش
list9=[btn_minus_payam, btn_minus_rajaii, btn_minus_emam, btn_minus_shariati,
btn_minus_khatam,btn_minus_mahak, btn_minus_ferdos, btn_minus_undef1,btn_minus_undef2]


concatedlist = listuprow + list0 + list1 + list2 + list3 + list4 + list5 + list6 + list7 + list8 + list9

setup_entry_bindings()


def on_app_close():
    """بستن تمیز اتصال Comecer هنگام بستن پنجره اصلی برنامه."""
    if comecer_reader_holder["reader"] is not None:
        comecer_reader_holder["reader"].stop()
    window.destroy()


window.protocol("WM_DELETE_WINDOW", on_app_close)
window.mainloop()
