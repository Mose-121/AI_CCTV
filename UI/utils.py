"""
utils.py — RTSP URL utilities and video timestamp parsing.
"""
from config import *


def infer_rtsp_variants(rtsp_url: str) -> Tuple[str, str]:
    """Return (main_url, sub_url) heuristically; fallback to same URL if unknown."""
    if not rtsp_url:
        return rtsp_url, rtsp_url
    try:
        u = urlparse(rtsp_url)
        qs = dict(parse_qsl(u.query))
        path = u.path or ""

        if "realmonitor" in path and "channel" in qs:
            qs_main = dict(qs); qs_main["subtype"] = "0"
            qs_sub  = dict(qs); qs_sub["subtype"]  = "1"
            main = urlunparse((u.scheme, u.netloc, path, u.params, urlencode(qs_main), u.fragment))
            sub  = urlunparse((u.scheme, u.netloc, path, u.params, urlencode(qs_sub),  u.fragment))
            return main, sub

        if "/Streaming/Channels/" in path:
            try:
                ch = path.split("/Streaming/Channels/")[-1]
                if ch.isdigit() and len(ch) == 3:
                    base = rtsp_url[:-3]
                    if ch.endswith("1"):
                        return base + ch, base + ch[:-1] + "2"
                    if ch.endswith("2"):
                        return base + ch[:-1] + "1", base + ch
            except Exception:
                pass

        if "/unicast/" in path and "/s" in path and path.endswith("/live"):
            parts = path.split("/")
            s_idx = [i for i, p in enumerate(parts) if p.startswith("s") and p[1:].isdigit()]
            if s_idx:
                i = s_idx[-1]
                main_p = list(parts); main_p[i] = "s1"
                sub_p  = list(parts); sub_p[i]  = "s2"
                main = urlunparse((u.scheme, u.netloc, "/".join(main_p), u.params, u.query, u.fragment))
                sub  = urlunparse((u.scheme, u.netloc, "/".join(sub_p),  u.params, u.query, u.fragment))
                return main, sub

        if "h264Preview_" in path:
            if path.endswith("_main"):
                return rtsp_url, rtsp_url.replace("_main", "_sub")
            if path.endswith("_sub"):
                return rtsp_url.replace("_sub", "_main"), rtsp_url

        if "axis-media/media.amp" in path:
            qs_main = dict(qs); qs_sub = dict(qs)
            qs_main.setdefault("resolution", "1920x1080")
            qs_sub.setdefault("resolution", "640x360")
            main = urlunparse((u.scheme, u.netloc, path, u.params, urlencode(qs_main), u.fragment))
            sub  = urlunparse((u.scheme, u.netloc, path, u.params, urlencode(qs_sub),  u.fragment))
            return main, sub

    except Exception as e:
        logger.error(f"Error inferring RTSP variants: {e}")
        return rtsp_url, rtsp_url
    return rtsp_url, rtsp_url


def build_rtsp_url(brand: str, host: str, port: str, user: str, pw: str,
                   channel: str, stream: str, profile: str, subtype: str, custom_path: str) -> str:
    """Build brand-specific RTSP url; for Generic use custom_path."""
    auth = f"{user}:{pw}@" if user and pw else (f"{user}@" if user else "")
    hostport = f"{host}:{port}" if port else host
    b = (brand or "").lower()
    ch = channel or "1"
    st = (stream or "").lower()
    pf = (profile or "").lower()
    sb = subtype or "0"

    if b == "dahua":
        return f"rtsp://{auth}{hostport}/cam/realmonitor?channel={ch}&subtype={sb}"
    if b == "hikvision":
        chnum = int(ch) if ch.isdigit() else 1
        path = f"/Streaming/Channels/{chnum}01" if st != "sub" else f"/Streaming/Channels/{chnum}02"
        return f"rtsp://{auth}{hostport}{path}"
    if b == "uniview":
        s = "s1" if st != "sub" else "s2"
        return f"rtsp://{auth}{hostport}/unicast/c{ch}/{s}/live"
    if b == "axis":
        res = "1920x1080" if st != "sub" else "640x360"
        return f"rtsp://{auth}{hostport}/axis-media/media.amp?camera={ch}&videocodec=h264&resolution={res}"
    if b == "reolink":
        suffix = "main" if st != "sub" else "sub"
        idx = int(ch) if ch.isdigit() else 1
        return f"rtsp://{auth}{hostport}/h264Preview_{idx:02d}_{suffix}"
    if b == "ezviz":
        base = "/h264_stream" if pf != "live" else "/live"
        return f"rtsp://{auth}{hostport}{base}"
    if b == "onvif-generic":
        if pf == "live":
            return f"rtsp://{auth}{hostport}/live/ch{ch}/0"
        path = f"/Streaming/Channels/{ch}01" if st != "sub" else f"/Streaming/Channels/{ch}02"
        return f"rtsp://{auth}{hostport}{path}"
    if b == "generic" and custom_path:
        cp = custom_path if custom_path.startswith("/") else f"/{custom_path}"
        return f"rtsp://{auth}{hostport}{cp}"
    return f"rtsp://{auth}{hostport}"


def _parse_video_start_time(date_str: str, filename: str) -> Optional[datetime]:
    """
    Parses the start time from a video filename.
    Returns an AWARE datetime object (Asia/Bangkok).
    """
    try:
        bangkok_tz = pytz.timezone('Asia/Bangkok')
        match = FILENAME_TIME_RE.search(filename)

        start_dt_obj = None
        if match:
            hh, mm, ss = match.groups()
            start_str = f"{date_str} {hh}:{mm}:{ss}"
            start_dt_obj = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
        else:
            start_dt_obj = datetime.strptime(f"{date_str} 00:00:00", "%Y-%m-%d %H:%M:%S")

        return bangkok_tz.localize(start_dt_obj)
    except Exception as e:
        logger.error(f"Could not parse time from {filename}: {e}")
        return None
