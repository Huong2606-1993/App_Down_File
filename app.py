# -*- coding: utf-8 -*-
"""
APP.PY - Tai anh theo ngay va theo ten nguoi gui, co mat khau bao ve.
Cau truc luu: uploads/<YYYY-MM-DD>/<ten_nguoi>/<file>

Cac sua doi so voi ban goc (khac phuc loi tai 2 anh tro len / nhieu nguoi
cung tai cung luc):
  1. Gioi han + bat loi kich thuoc file (MAX_CONTENT_LENGTH + error handler 413).
  2. Luu tung file trong try/except rieng - 1 file loi khong lam hong ca luot tai.
  3. Bao loi ro rang cho nguoi dung thay vi im lang / trang trang.
  4. (Xem file Procfile di kem) tang timeout + dung nhieu worker/thread cho
     Gunicorn de nhieu nguoi tai cung luc khong bi chan lan nhau.
"""
import os
import re
import hmac
import datetime
from flask import (
    Flask, request, render_template_string, redirect,
    url_for, send_from_directory, flash, make_response
)
from werkzeug.exceptions import RequestEntityTooLarge

app = Flask(__name__)
app.secret_key = "doi-chuoi-nay-thanh-gi-do-bi-mat"

# ==== DOI MAT KHAU O DAY ====
APP_PASSWORD = "MCDYHL123"
# =============================

# Gioi han tong dung luong 1 luot upload (tat ca file cong lai). Tang/giam so
# nay tuy nhu cau - 60MB du cho ~6-8 anh dien thoai (moi anh ~5-8MB).
MAX_UPLOAD_MB = 120
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp", "heic", "pdf",
               "doc", "docx", "xls", "xlsx", "csv",
               "xlsm", "xlsb", "xlt", "xltx", "xltm", "xla", "xlam"}
NAME_COOKIE = "ten_nguoi_gui"
AUTH_COOKIE = "da_dang_nhap"
AUTH_VALUE = "ok_" + hmac.new(app.secret_key.encode(), APP_PASSWORD.encode(), "sha256").hexdigest()[:16]


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def safe_name(text, default="Khach"):
    text = (text or "").strip()
    if not text:
        return default
    text = re.sub(r"[^\w\s\-]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", "_", text).strip("_")
    return text[:50] or default


def today_str():
    return datetime.date.today().strftime("%Y-%m-%d")


def is_authed():
    return request.cookies.get(AUTH_COOKIE) == AUTH_VALUE


PASSWORD_FORM = """
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nhap mat khau</title>
<style>
body { font-family: Arial, sans-serif; background:#f4f6f8; margin:0; padding:20px;
       display:flex; align-items:center; justify-content:center; min-height:90vh; }
.box { max-width:380px; width:100%; background:#fff; border-radius:12px;
       box-shadow:0 2px 10px rgba(0,0,0,0.08); padding:26px; }
h2 { color:#1F4E78; margin-top:0; }
input[type=password] { width:100%; padding:12px; font-size:15px; border:1px solid #ccc;
                    border-radius:8px; box-sizing:border-box; margin-bottom:14px; }
button { background:#1F4E78; color:#fff; border:none; padding:12px 22px;
         border-radius:8px; font-size:15px; cursor:pointer; width:100%; }
.err { background:#fdecec; color:#8a2f2f; padding:10px; border-radius:8px; margin-bottom:14px; font-size:14px; }
</style>
</head>
<body>
<div class="box">
  <h2>Nhap mat khau de vao</h2>
  {% if loi %}<div class="err">Mat khau khong dung, thu lai.</div>{% endif %}
  <form method="POST" action="{{ url_for('kiem_tra_mat_khau') }}">
    <input type="password" name="mk" placeholder="Mat khau" required autofocus>
    <button type="submit">Vao</button>
  </form>
</div>
</body>
</html>
"""

NAME_FORM = """
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nhap ten</title>
<style>
body { font-family: Arial, sans-serif; background:#f4f6f8; margin:0; padding:20px;
       display:flex; align-items:center; justify-content:center; min-height:90vh; }
.box { max-width:400px; width:100%; background:#fff; border-radius:12px;
       box-shadow:0 2px 10px rgba(0,0,0,0.08); padding:26px; }
h2 { color:#1F4E78; margin-top:0; }
input[type=text] { width:100%; padding:12px; font-size:15px; border:1px solid #ccc;
                    border-radius:8px; box-sizing:border-box; margin-bottom:14px; }
button { background:#1F4E78; color:#fff; border:none; padding:12px 22px;
         border-radius:8px; font-size:15px; cursor:pointer; width:100%; }
</style>
</head>
<body>
<div class="box">
  <h2>Nhap ten cua ban</h2>
  <form method="POST" action="{{ url_for('set_name') }}">
    <input type="text" name="ten" placeholder="Vi du: Huong, Cuong, ..." required autofocus>
    <button type="submit">Bat dau</button>
  </form>
</div>
</body>
</html>
"""

PAGE = """
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tai anh / tai lieu</title>
<style>
body { font-family: Arial, sans-serif; background:#f4f6f8; margin:0; padding:20px; }
.box { max-width:560px; margin:0 auto 24px auto; background:#fff; border-radius:12px;
       box-shadow:0 2px 10px rgba(0,0,0,0.08); padding:22px; }
h2 { color:#1F4E78; margin-top:0; }
.topbar { max-width:560px; margin:0 auto 14px auto; display:flex;
          justify-content:space-between; align-items:center; font-size:14px; color:#555; }
.topbar a { color:#1F4E78; text-decoration:none; margin-left:12px; }
label.file-label { display:block; margin:14px 0 6px; font-size:14px; color:#444; font-weight:bold; }
input[type=file] { width:100%; margin:0 0 4px 0; box-sizing:border-box; }
.hint { font-size:12px; color:#888; margin:0 0 14px; }
button, .btn { background:#1F4E78; color:#fff; border:none; padding:12px 22px;
               border-radius:8px; font-size:15px; cursor:pointer; width:100%; text-align:center;
               display:block; text-decoration:none; box-sizing:border-box; margin-top:6px; }
button:disabled { background:#9db3c4; cursor:not-allowed; }
.flash { background:#e8f5e9; color:#256029; padding:10px; border-radius:8px; margin-bottom:14px; }
.flash.err { background:#fdecec; color:#8a2f2f; }
#tien-trinh { display:none; margin-top:10px; font-size:13px; color:#1F4E78; text-align:center; }
details { margin-bottom:10px; }
summary { cursor:pointer; font-weight:bold; color:#1F4E78; padding:8px 0; }
.person { margin:6px 0 6px 14px; }
.person-name { font-weight:bold; color:#333; margin:8px 0 4px; }
ul { list-style:none; padding:0; margin:0 0 6px 0; }
li { display:flex; justify-content:space-between; align-items:center;
     padding:8px 0; border-bottom:1px solid #eee; font-size:14px; }
li a { color:#1F4E78; text-decoration:none; word-break:break-all; margin-right:10px; }
.del { background:#c0392b; padding:5px 10px; font-size:12px; width:auto; }
.empty { color:#888; }
</style>
</head>
<body>

<div class="topbar">
  <span>Xin chao, <b>{{ ten }}</b></span>
  <span>
    <a href="{{ url_for('doi_ten') }}">Doi ten</a>
    <a href="{{ url_for('dang_xuat') }}">Dang xuat</a>
  </span>
</div>

<div class="box">
  <h2>Tai anh / tai lieu len</h2>
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for cat, msg in messages %}
        <div class="flash {{ 'err' if cat == 'error' else '' }}">{{ msg }}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}

  <form id="form-upload" method="POST" action="{{ url_for('upload') }}" enctype="multipart/form-data">
    <label class="file-label">Chon anh / PDF / Word / Excel co san</label>
    <input type="file" name="files" accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.csv,.xlsm,.xlsb,.xlt,.xltx,.xltm,.xla,.xlam" multiple>
    <p class="hint">Bam vao day de chon cung luc nhieu file (anh, PDF, Word, Excel) - toi da {{ max_mb }}MB tong cong.</p>

    <label class="file-label">Hoac chup anh moi bang camera</label>
    <input type="file" name="files" accept="image/*" capture="environment">
    <p class="hint">Chi chup duoc 1 anh moi lan nhan nut nay (gioi han cua camera).</p>

    <button type="submit" id="btn-upload">Tai len</button>
    <div id="tien-trinh">Dang tai len, vui long doi va DUNG dong trang nay...</div>
  </form>
</div>

<div class="box">
  <h2>Danh sach da tai len</h2>
  {% if cau_truc %}
    {% for ngay, nguoi_dict in cau_truc %}
    <details {% if loop.first %}open{% endif %}>
      <summary>{{ ngay }} ({{ nguoi_dict|length }} nguoi)</summary>
      {% for nguoi, files in nguoi_dict %}
      <div class="person">
        <div class="person-name">{{ nguoi }} ({{ files|length }} file)</div>
        <ul>
          {% for f in files %}
          <li>
            <a href="{{ url_for('download', ngay=ngay, nguoi=nguoi, filename=f) }}">{{ f }}</a>
            <form method="POST" action="{{ url_for('delete', ngay=ngay, nguoi=nguoi, filename=f) }}"
                  onsubmit="return confirm('Xoa file nay?');" style="margin:0;">
              <button type="submit" class="del">Xoa</button>
            </form>
          </li>
          {% endfor %}
        </ul>
      </div>
      {% endfor %}
    </details>
    {% endfor %}
  {% else %}
    <p class="empty">Chua co file nao.</p>
  {% endif %}
</div>

<script>
// Vo hieu hoa nut + hien chu "dang tai" ngay khi bam Tai len, de nguoi dung
// khong bam nhieu lan / khong tuong nham la app bi treo khi dang tai anh lon.
document.getElementById('form-upload').addEventListener('submit', function () {
  document.getElementById('btn-upload').disabled = true;
  document.getElementById('btn-upload').innerText = 'Dang tai len...';
  document.getElementById('tien-trinh').style.display = 'block';
});
</script>

</body>
</html>
"""


def get_current_name():
    return request.cookies.get(NAME_COOKIE, "")


@app.errorhandler(RequestEntityTooLarge)
def handle_too_large(e):
    # Truoc day khi vuot gioi han dung luong, Flask nem loi 413 khong co
    # thong bao ro rang -> nguoi dung tuong app "khong tai duoc". Gio bao
    # thang cho ho biet ly do va quay lai trang chinh.
    flash(f"File qua nang! Tong dung luong 1 luot tai khong duoc vuot qua {MAX_UPLOAD_MB}MB. "
          f"Hay tai it anh hon moi luot, hoac giam do phan giai anh truoc khi tai.", "error")
    return redirect(url_for("index"))


@app.route("/")
def index():
    if not is_authed():
        return render_template_string(PASSWORD_FORM, loi=False)

    ten = get_current_name()
    if not ten:
        return render_template_string(NAME_FORM)

    cau_truc = []
    if os.path.isdir(UPLOAD_DIR):
        ngay_list = sorted(os.listdir(UPLOAD_DIR), reverse=True)
        for ngay in ngay_list:
            ngay_path = os.path.join(UPLOAD_DIR, ngay)
            if not os.path.isdir(ngay_path):
                continue
            nguoi_list = sorted(os.listdir(ngay_path))
            nguoi_dict = []
            for nguoi in nguoi_list:
                nguoi_path = os.path.join(ngay_path, nguoi)
                if not os.path.isdir(nguoi_path):
                    continue
                files = sorted(os.listdir(nguoi_path), reverse=True)
                if files:
                    nguoi_dict.append((nguoi, files))
            if nguoi_dict:
                cau_truc.append((ngay, nguoi_dict))

    return render_template_string(PAGE, ten=ten, cau_truc=cau_truc, max_mb=MAX_UPLOAD_MB)


@app.route("/kiem-tra-mat-khau", methods=["POST"])
def kiem_tra_mat_khau():
    mk = request.form.get("mk", "")
    if hmac.compare_digest(mk, APP_PASSWORD):
        resp = make_response(redirect(url_for("index")))
        resp.set_cookie(AUTH_COOKIE, AUTH_VALUE, max_age=60 * 60 * 24 * 30)
        return resp
    return render_template_string(PASSWORD_FORM, loi=True)


@app.route("/dang-xuat")
def dang_xuat():
    resp = make_response(redirect(url_for("index")))
    resp.delete_cookie(AUTH_COOKIE)
    resp.delete_cookie(NAME_COOKIE)
    return resp


@app.route("/set-name", methods=["POST"])
def set_name():
    if not is_authed():
        return redirect(url_for("index"))
    ten = safe_name(request.form.get("ten"))
    resp = make_response(redirect(url_for("index")))
    resp.set_cookie(NAME_COOKIE, ten, max_age=60 * 60 * 24 * 365)
    return resp


@app.route("/doi-ten")
def doi_ten():
    resp = make_response(redirect(url_for("index")))
    resp.delete_cookie(NAME_COOKIE)
    return resp


@app.route("/upload", methods=["POST"])
def upload():
    if not is_authed():
        return redirect(url_for("index"))
    ten = get_current_name()
    if not ten:
        return redirect(url_for("index"))

    ngay = today_str()
    thu_muc = os.path.join(UPLOAD_DIR, ngay, ten)
    os.makedirs(thu_muc, exist_ok=True)

    incoming = request.files.getlist("files")
    saved = 0
    skipped = 0
    failed = 0
    for file in incoming:
        if not file or not file.filename:
            continue
        if not allowed_file(file.filename):
            skipped += 1
            continue
        try:
            ts = datetime.datetime.now().strftime("%H%M%S_%f")
            clean_name = "".join(c for c in file.filename if c.isalnum() or c in "._-")
            final_name = f"{ts}_{clean_name}"
            file.save(os.path.join(thu_muc, final_name))
            saved += 1
        except Exception as e:
            # 1 file loi (dia day, ten file la, mat ket noi giua chung) khong
            # duoc lam hong nhung file con lai trong cung luot tai.
            failed += 1
            app.logger.error(f"Loi luu file '{file.filename}': {e}")

    if saved and not failed and not skipped:
        flash(f"Da tai len thanh cong {saved} file vao thu muc {ngay}/{ten}!")
    elif saved:
        msg = f"Da tai len {saved} file thanh cong."
        if skipped:
            msg += f" {skipped} file bi bo qua (dinh dang khong ho tro)."
        if failed:
            msg += f" {failed} file bi loi khi luu, hay thu tai lai file do."
        flash(msg, "error" if failed else None)
    else:
        flash("Khong co file hop le nao duoc luu. Kiem tra lai dinh dang anh/pdf, "
              "hoac thu tai tung anh mot neu mang yeu.", "error")
    return redirect(url_for("index"))


@app.route("/download/<ngay>/<nguoi>/<path:filename>")
def download(ngay, nguoi, filename):
    if not is_authed():
        return redirect(url_for("index"))
    thu_muc = os.path.join(UPLOAD_DIR, ngay, nguoi)
    return send_from_directory(thu_muc, filename, as_attachment=True)


@app.route("/delete/<ngay>/<nguoi>/<path:filename>", methods=["POST"])
def delete(ngay, nguoi, filename):
    if not is_authed():
        return redirect(url_for("index"))
    path = os.path.join(UPLOAD_DIR, ngay, nguoi, filename)
    if os.path.exists(path):
        os.remove(path)
    flash("Da xoa file.")
    return redirect(url_for("index"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
