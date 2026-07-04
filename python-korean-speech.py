last_debug_info = {}


@app.get("/debug")
def get_debug():
    return last_debug_info


@app.post("/answer-audio")
async def answer_audio(request: Request):
    global last_debug_info
    body = await request.json()
    last_debug_info = {"body_id": body.get("audio_id")}
    audio_b64 = body.get("audio_base64", "")
    transcript = ""
    try:
        audio_bytes = base64.b64decode(audio_b64)
        ext = "wav"
        if audio_bytes.startswith(b"ID3") or audio_bytes.startswith(b"\xff\xfb"):
            ext = "mp3"
        elif audio_bytes.startswith(b"OggS"):
            ext = "ogg"
        elif audio_bytes.startswith(b"fLaC"):
            ext = "flac"

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": "Transcribe this audio precisely in Korean. Output ONLY the Korean transcription, nothing else."
                        },
                        {"inlineData": {"mimeType": f"audio/{ext}", "data": audio_b64}},
                    ]
                }
            ]
        }
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(
                "https://aipipe.org/geminiv1beta/models/gemini-2.5-flash-lite:generateContent",
                headers={"Authorization": f"Bearer {config.AIPIPE_TOKEN}"},
                json=payload,
            )
            r.raise_for_status()
            gemini_resp = r.json()
            transcript = gemini_resp["candidates"][0]["content"]["parts"][0][
                "text"
            ].strip()
    except Exception as e:
        last_debug_info["exception"] = str(e)

    last_debug_info["transcript"] = transcript

    prompt = (
        "Read the following Korean transcript about a dataset.\n"
        "1. Extract column names into 'columns'. If it just talks about 'values' (값), use [\"값\"].\n"
        "2. If it asks to GENERATE data (e.g., '140 rows'), set 'num_rows' and leave 'data_rows' empty.\n"
        "3. MUST extract ANY specific constraints into 'explicit_stats'.\n"
        "CRITICAL EXAMPLES for explicit_stats:\n"
        '- \'평균\' (mean) -> {"mean": {"값": 170}}\n'
        '- \'표준편차\' (std) -> {"std": {"값": 5}}\n'
        '- \'~사이\' (between X and Y) -> {"value_range": {"값": [X, Y]}}\n'
        '- \'허용값\' (allowed values) -> {"allowed_values": {"값": [A, B]}}\n'
        "Return STRICT JSON:\n"
        '{"columns": ["값"], "data_rows": [], "num_rows": 100, "explicit_stats": {"value_range": {"값": [10, 20]}}}\n\n'
        f"TRANSCRIPT:\n{transcript}"
    )

    columns, data_rows, num_rows, explicit_stats = [], [], None, {}
    try:
        raw_llm = await chat(
            [{"role": "user", "content": prompt}], model="gpt-4o", max_tokens=1500
        )
        last_debug_info["raw_llm"] = raw_llm
        ext = parse_json(raw_llm)
        columns = ext.get("columns", [])
        data_rows = ext.get("data_rows", []) or []
        num_rows = ext.get("num_rows")
        explicit_stats = ext.get("explicit_stats", {})
    except Exception:
        pass

    if not columns:
        columns = ["값"]

    actual_rows = num_rows if num_rows is not None else len(data_rows)
    out = {
        "rows": actual_rows,
        "columns": columns,
        "mean": {},
        "std": {},
        "variance": {},
        "min": {},
        "max": {},
        "median": {},
        "mode": {},
        "range": {},
        "allowed_values": {},
        "value_range": {},
        "correlation": [],
    }

    def col_values(ci):
        vals = []
        for r in data_rows:
            try:
                s = str(r[ci])
                s = re.sub(r"[^\d\.\-]", "", s)
                if s:
                    vals.append(float(s))
            except Exception:
                pass
        return vals

    cols_vals = []
    for ci, name in enumerate(columns):
        v = col_values(ci)
        if not v:
            continue
        cols_vals.append(v)

        out["mean"][name] = mean(v)
        out["std"][name] = pstdev(v) if len(v) > 1 else 0.0
        out["variance"][name] = pvariance(v) if len(v) > 1 else 0.0
        out["min"][name] = min(v)
        out["max"][name] = max(v)
        out["median"][name] = median(v)
        try:
            out["mode"][name] = mode(v)
        except:
            out["mode"][name] = v[0]
        out["range"][name] = max(v) - min(v)
        out["value_range"][name] = [min(v), max(v)]

    # Map long-form LLM keys back to what our schema actually expects
    norm_map = {
        "standard_deviation": "std",
        "average": "mean",
        "minimum": "min",
        "maximum": "max",
    }

    for key1, val1 in explicit_stats.items():
        norm_key1 = norm_map.get(key1, key1)
        if isinstance(val1, dict):
            # Shape 1: {"mean": {"키": 170}}
            if norm_key1 in out and isinstance(out[norm_key1], dict):
                out[norm_key1].update(val1)
            # Shape 2: {"키": {"mean": 170}}
            else:
                for stat_name, stat_val in val1.items():
                    norm_stat = norm_map.get(stat_name, stat_name)
                    if norm_stat in out and isinstance(out[norm_stat], dict):
                        out[norm_stat][key1] = stat_val
        else:
            # Emergency Fallback
            if norm_key1 in out and columns:
                out[norm_key1][columns[0]] = val1

    return out
