#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PrintBridge — 上传文件→本机 CUPS 打印 (Canon TS8080)
HA 面板 iframe 内嵌或局域网直接访问: http://<mac>:8899
"""
import subprocess, tempfile, shutil, time
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

PRINTER = "Canon_TS8080"
MAX_BYTES = 60 * 1024 * 1024  # 60MB
ALLOWED = {".pdf", ".txt", ".md", ".doc", ".docx", ".rtf",
           ".jpg", ".jpeg", ".png", ".heic", ".webp", ".bmp", ".tiff", ".gif", ".ps"}

app = FastAPI(title="PrintBridge")


def to_pdf(src: Path) -> Path:
    """把各种格式转成可打印的 PDF，返回打印用的文件路径"""
    ext = src.suffix.lower()
    if ext == ".pdf":
        return src
    if ext == ".ps":
        return src
    out = src.with_suffix(".pdf")
    try:
        if ext in (".txt", ".md"):
            with open(out, "wb") as f:
                subprocess.run(["cupsfilter", "-m", "application/pdf", str(src)],
                               stdout=f, check=True, timeout=120)
        elif ext in (".doc", ".docx", ".rtf"):
            subprocess.run(["textutil", "-convert", "pdf", "-output", str(out), str(src)],
                           check=True, timeout=120)
        elif ext in (".jpg", ".jpeg", ".png", ".heic", ".webp", ".bmp", ".tiff", ".gif"):
            subprocess.run(["sips", "-s", "format", "pdf", str(src), "--out", str(out)],
                           check=True, timeout=180)
        else:
            return None
    except Exception as e:
        raise HTTPException(500, f"转换失败: {e}")
    if not out.exists():
        raise HTTPException(500, "转换后未产出文件")
    return out


@app.get("/status")
def printer_status():
    """查询打印机实时状态"""
    try:
        r = subprocess.run(["lpstat", "-p", PRINTER],
                           capture_output=True, text=True, timeout=10)
        out = r.stdout.strip()
        # 解析状态
        if "闲置" in out or "idle" in out.lower():
            return {"online": True, "status": "在线", "detail": "就绪"}
        elif "正在打印" in out or "printing" in out.lower():
            return {"online": True, "status": "忙碌", "detail": "正在打印"}
        elif "已停止" in out or "stopped" in out.lower():
            # 检查具体原因（缺纸、卡纸等）
            detail = out.split("原因:")[-1].strip() if "原因:" in out else "已停止"
            if "media-empty" in out or "缺纸" in out or "paper" in out.lower():
                detail = "缺纸"
            elif "jam" in out or "卡纸" in out:
                detail = "卡纸"
            elif "offline" in out:
                detail = "离线"
            return {"online": False, "status": "离线", "detail": detail}
        elif r.returncode != 0:
            return {"online": False, "status": "异常", "detail": r.stderr.strip()[:50]}
        else:
            return {"online": False, "status": "未知", "detail": out[:50]}
    except Exception as e:
        return {"online": False, "status": "异常", "detail": str(e)[:50]}


@app.get("/", response_class=HTMLResponse)
def index():
    return Path(__file__).parent.joinpath("web", "index.html").read_text(encoding="utf-8")


@app.post("/print")
async def print_file(
    file: UploadFile = File(...),
    copies: int = Form(1),
    color: str = Form("color"),      # color | gray
    duplex: str = Form("off"),       # off | long | short
    media: str = Form("A4"),         # A4 | A5 | Letter | 4x6 | 5x7 | B5 | Legal | Postcard
    paper: str = Form("plain"),      # plain | photo | envelope
    quality: str = Form("normal"),   # draft | normal | high
):
    if not file.filename:
        raise HTTPException(400, "未选择文件")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(400, f"不支持的文件类型 {ext or '无扩展名'}，支持: {', '.join(sorted(ALLOWED))}")
    if not 1 <= copies <= 99:
        raise HTTPException(400, "份数需在 1-99 之间")
    if color not in ("color", "gray"):
        raise HTTPException(400, "颜色参数无效")
    if duplex not in ("off", "long", "short"):
        raise HTTPException(400, "双面参数无效")
    if media not in ("A4", "A5", "Letter", "4x6", "5x7", "B5", "Legal", "Postcard"):
        raise HTTPException(400, "纸张参数无效")
    if paper not in ("plain", "photo", "envelope"):
        raise HTTPException(400, "介质参数无效")
    if quality not in ("draft", "normal", "high"):
        raise HTTPException(400, "质量参数无效")

    tmpdir = Path(tempfile.mkdtemp(prefix="pb_"))
    try:
        src = tmpdir / ("upload" + ext)
        data = await file.read()
        if len(data) > MAX_BYTES:
            raise HTTPException(400, "文件超过 60MB 限制")
        src.write_bytes(data)

        job = to_pdf(src)
        lp_args = ["lp", "-d", PRINTER, "-n", str(copies)]
        if color == "gray":
            lp_args += ["-o", "ColorModel=Gray"]
        if duplex == "long":
            lp_args += ["-o", "Duplex=DuplexNoTumble"]
        elif duplex == "short":
            lp_args += ["-o", "Duplex=DuplexTumble"]
        lp_args += ["-o", f"PageSize={media}"]
        if quality != "normal":
            lp_args += ["-o", f"cupsPrintQuality={quality.capitalize()}"]
        if paper == "photo":
            lp_args += ["-o", "MediaType=Photographic"]
        elif paper == "envelope":
            lp_args += ["-o", "MediaType=Envelope"]
        lp_args.append(str(job))

        t0 = time.time()
        r = subprocess.run(lp_args, capture_output=True, text=True, timeout=300)
        elapsed = round(time.time() - t0, 1)
        if r.returncode != 0:
            raise HTTPException(500, f"打印失败: {r.stderr.strip() or r.stdout.strip()}")
        job_id = (r.stdout.strip().split("请求id是")[-1]
                  if "请求id是" in r.stdout else r.stdout.strip())
        return {"ok": True, "job": job_id, "elapsed": elapsed, "copies": copies,
                "color": color, "duplex": duplex, "media": media,
                "paper": paper, "quality": quality, "file": file.filename}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8899)