import time
import zlib
import secrets
from pathlib import Path
import streamlit.components.v1 as components
import base64
import csv
import hashlib
import io
import json
import math
import random
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import pandas as pd
import requests
import streamlit as st


st.set_page_config(
    page_title="Sleep Free",
    page_icon="🌙",
    layout="wide",
)

KST = timezone(timedelta(hours=9))
API = "https://pokeapi.co/api/v2"

POKEMON = [
    ("이상해씨", 1, "일반"),
    ("파이리", 4, "일반"),
    ("꼬부기", 7, "일반"),
    ("피카츄", 25, "희귀"),
    ("삐삐", 35, "희귀"),
    ("식스테일", 37, "희귀"),
    ("푸린", 39, "희귀"),
    ("나옹", 52, "일반"),
    ("고라파덕", 54, "일반"),
    ("가디", 58, "희귀"),
    ("캐이시", 63, "희귀"),
    ("고오스", 92, "희귀"),
    ("잉어킹", 129, "일반"),
    ("이브이", 133, "희귀"),
    ("잠만보", 143, "초희귀"),
    ("미뇽", 147, "초희귀"),
    ("뮤", 151, "환상"),
    ("치코리타", 152, "희귀"),
    ("브케인", 155, "희귀"),
    ("리아코", 158, "희귀"),
    ("토게피", 175, "희귀"),
    ("메리프", 179, "일반"),
    ("마릴", 183, "일반"),
    ("우파", 194, "일반"),
    ("깜지곰", 216, "일반"),
    ("나무지기", 252, "희귀"),
    ("아차모", 255, "희귀"),
    ("물짱이", 258, "희귀"),
    ("랄토스", 280, "희귀"),
    ("아공이", 371, "초희귀"),
    ("모부기", 387, "희귀"),
    ("불꽃숭이", 390, "희귀"),
    ("팽도리", 393, "희귀"),
    ("꼬링크", 403, "일반"),
    ("딥상어동", 443, "초희귀"),
    ("리오르", 447, "희귀"),
    ("주리비얀", 495, "희귀"),
    ("뚜꾸리", 498, "희귀"),
    ("수댕이", 501, "희귀"),
    ("도치마론", 650, "희귀"),
    ("푸호꼬", 653, "희귀"),
    ("개구마르", 656, "희귀"),
    ("나몰빼미", 722, "희귀"),
    ("냐오불", 725, "희귀"),
    ("누리공", 728, "희귀"),
    ("흥나숭", 810, "희귀"),
    ("염버니", 813, "희귀"),
    ("울머기", 816, "희귀"),
    ("나오하", 906, "희귀"),
    ("뜨아거", 909, "희귀"),
    ("꾸왁스", 912, "희귀"),
]

DEX = {
    number: (name, rarity)
    for name, number, rarity in POKEMON
}

METRICS = [
    ("quality", "수면의 질 점수 (0~100)", 100),
    ("asleep", "실제 수면 시간 (분)", 4320),
    ("latency", "잠들기까지 걸린 시간 (분)", 4320),
    ("snoring", "코골이 시간 (분)", 4320),
    ("awake", "깨어 있던 시간 (분)", 4320),
    ("light", "얕은 수면 (분)", 4320),
    ("deep", "깊은 수면 (분)", 4320),
    ("rem", "REM 수면 (분)", 4320),
]


# =====================================
# 기본 함수
# =====================================

def now():
    return datetime.now(KST)


def parse_dt(value):
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=KST)
    return parsed.astimezone(KST)


def dt_join(date, time):
    return datetime.combine(date, time, tzinfo=KST)


def new_id():
    return str(uuid.uuid4())


# =====================================
# 포켓몬 데이터
# =====================================

@st.cache_data(ttl=86400, show_spinner=False)
def api_json(url):
    response = requests.get(url, timeout=12)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=86400, show_spinner=False)
def species_ids():
    numbers = []
    url = f"{API}/pokemon-species?limit=1000"

    while url:
        data = api_json(url)
        numbers.extend(
            int(item["url"].rstrip("/").split("/")[-1])
            for item in data["results"]
        )
        url = data.get("next")

    if not numbers:
        raise ValueError("포켓몬 목록을 불러오지 못했어요.")

    return numbers


@st.cache_data(ttl=86400, show_spinner=False)
def species_info(number):
    species = api_json(
        f"{API}/pokemon-species/{number}"
    )

    name = next(
        (
            item["name"]
            for item in species["names"]
            if item["language"]["name"] == "ko"
        ),
        species["name"],
    )

    if species.get("is_mythical"):
        rarity = "환상"
    elif species.get("is_legendary"):
        rarity = "전설"
    elif species.get("capture_rate", 255) <= 45:
        rarity = "초희귀"
    elif species.get("capture_rate", 255) <= 100:
        rarity = "희귀"
    else:
        rarity = "일반"

    default = next(
        (
            item for item in species["varieties"]
            if item["is_default"]
        ),
        species["varieties"][0],
    )

    image_id = int(
        default["pokemon"]["url"]
        .rstrip("/")
        .split("/")[-1]
    )

    return {
        "number": number,
        "name": name,
        "rarity": rarity,
        "image_id": image_id,
        "chain_url": (
            species.get("evolution_chain") or {}
        ).get("url"),
    }


def pokemon(number, level=1, shiny=False, info=None):
    if info is None:
        if number in DEX:
            name, rarity = DEX[number]
            info = {
                "name": name,
                "rarity": rarity,
                "image_id": number,
            }
        else:
            info = species_info(number)

    return {
        "uid": new_id(),
        "number": number,
        "name": info["name"],
        "rarity": info["rarity"],
        "image_id": info.get("image_id", number),
        "level": level,
        "base_level": level,
        "total_xp": 0.0,
        "xp": 0.0,
        "shiny": shiny,
        "ball": "몬스터볼",
    }


# =====================================
# 경험치와 성장
# =====================================

def level_from_xp(base_level, total_xp):
    level = base_level
    remaining = max(0.0, float(total_xp))

    while level < 100 and remaining + 1e-9 >= level:
        remaining -= level
        level += 1

    return level, max(0.0, remaining)


def sync_growth(p):
    totals = {
        mon["uid"]: 0.0
        for mon in p["collection"]
    }
    rewarded_dates = set()

    records = sorted(
        p["cycles"],
        key=lambda record: (
            record.get("end", ""),
            record["uid"],
        ),
    )

    for record in records:
        partner_uid = record.get("partner_uid")
        quality = record.get("quality")

        if partner_uid not in totals or quality is None:
            continue

        try:
            quality = float(quality)
            day = parse_dt(
                record["end"]
            ).date().isoformat()
        except (ValueError, TypeError, KeyError):
            continue

        if (
            day in rewarded_dates
            or not math.isfinite(quality)
            or not 0 <= quality <= 100
        ):
            continue

        rewarded_dates.add(day)
        totals[partner_uid] += quality

    for mon in p["collection"]:
        mon["total_xp"] = totals[mon["uid"]] + mon.get("coin_xp", 0) + mon.get("candy_xp", 0) + mon.get("battle_xp", 0)
        mon["level"], mon["xp"] = level_from_xp(
            mon["base_level"],
            mon["total_xp"],
        )


def growth_status(mon):
    if mon["shiny"]:
        st.success("✨ 이로치 포켓몬")

    st.write(
        f"**Lv.{mon['level']}** · "
        f"누적 수면 경험치 **{mon['total_xp']:g} XP**"
    )

    if mon["level"] < 100:
        required = mon["level"]
        st.progress(
            min(1.0, mon["xp"] / required)
        )
        st.caption(
            f"다음 레벨: {mon['xp']:g} / {required} XP"
        )
    else:
        st.success("최대 레벨 100에 도달했어요!")


# =====================================
# 진화
# =====================================

@st.cache_data(ttl=86400, show_spinner=False)
def evolution_options(number):
    info = species_info(number)

    if not info["chain_url"]:
        return []

    chain = api_json(info["chain_url"])["chain"]

    def search(node):
        current_number = int(
            node["species"]["url"]
            .rstrip("/")
            .split("/")[-1]
        )

        if current_number == number:
            options = []

            for child in node.get("evolves_to", []):
                target = int(
                    child["species"]["url"]
                    .rstrip("/")
                    .split("/")[-1]
                )

                details = (
                    child.get("evolution_details") or []
                )

                levels = [
                    detail["min_level"]
                    for detail in details
                    if detail.get("min_level") is not None
                ]

                required = min(levels) if levels else 20

                options.append({
                    "number": target,
                    "level": required,
                })

            return options

        for child in node.get("evolves_to", []):
            result = search(child)
            if result:
                return result

        return []

    return search(chain)


def evolution_panel(mon):
    with st.expander("✨ 진화 확인"):
        visible = st.checkbox(
            "진화 조건 표시",
            key=f"evo_show_{mon['uid']}",
        )

        if not visible:
            return

        st.caption(
            "레벨 진화는 API의 요구 레벨을 사용해요. "
            "돌·친밀도 등 특수 조건은 Lv.20으로 단순화해요."
        )

        try:
            options = evolution_options(mon["number"])

            if not options:
                st.write("다음 진화 단계가 없어요.")

            for option in options:
                info = species_info(option["number"])

                st.write(
                    f"{mon['name']} → {info['name']} "
                    f"· 필요 Lv.{option['level']}"
                )

                clicked = st.button(
                    f"✨ {info['name']}(으)로 진화",
                    key=(
                        f"evolve_{mon['uid']}_"
                        f"{option['number']}"
                    ),
                    disabled=(
                        mon["level"] < option["level"]
                    ),
                )

                if clicked and mon["level"] >= option["level"]:
                    mon.update({
                        key: info[key]
                        for key in (
                            "number", "name",
                            "rarity", "image_id",
                        )
                    })
                    success(
                        f"{info['name']}(으)로 진화했어요!"
                    )

        except (
            requests.RequestException,
            ValueError,
            KeyError,
            TypeError,
        ):
            st.warning(
                "진화 정보를 불러오지 못했어요. "
                "잠시 후 다시 시도해 주세요."
            )


# =====================================
# 프로필
# =====================================

def fresh_profile():
    starter = pokemon(143, level=1)

    return {
        "collection": [starter],
        "partner_uid": starter["uid"],
        "goal_hours": 8.0,
        "sleep_start": None,
        "records": [],
        "cycles": [],
        "naps": [],
        "day_checks": [],
    }


def migrate(source):
    p = dict(source) if isinstance(source, dict) else {}

    for key in (
        "records", "cycles", "naps", "day_checks"
    ):
        if not isinstance(p.get(key), list):
            p[key] = []

        p[key] = [
            dict(
                record,
                uid=str(record.get("uid") or new_id()),
            )
            for record in p[key]
            if isinstance(record, dict)
        ]

    collection = p.get("collection")

    if not isinstance(collection, list):
        collection = []

    cleaned = []
    used_uids = set()

    for item in collection:
        if not isinstance(item, dict):
            continue

        number = item.get("number")

        if type(number) is not int or not 1 <= number <= 100000:
            continue

        name, rarity = DEX.get(
            number,
            (
                str(
                    item.get("name", f"포켓몬 {number}")
                )[:100],
                str(item.get("rarity", "일반"))[:20],
            ),
        )

        level = item.get("level", 1)
        base_level = item.get("base_level", level)

        if (
            type(level) is not int
            or not 1 <= level <= 100
            or type(base_level) is not int
            or not 1 <= base_level <= 100
        ):
            raise ValueError(
                "포켓몬 레벨은 1~100이어야 합니다."
            )

        entry = pokemon(
            number,
            level=level,
            info={
                "name": name,
                "rarity": rarity,
                "image_id": item.get("image_id", number),
            },
        )

        item_uid = str(item.get("uid") or new_id())

        if item_uid in used_uids:
            item_uid = new_id()

        used_uids.add(item_uid)

        entry.update({
            "uid": item_uid,
            "base_level": base_level,
            "shiny": bool(item.get("shiny", False)),
            "ball": str(item.get("ball", "몬스터볼")),
            "move_layout": list(dict.fromkeys(mid for mid in item.get("move_layout", []) if type(mid) is int and mid > 0))[:4] if isinstance(item.get("move_layout", []), list) else [],
            "coin_xp": item.get("coin_xp", 0) if type(item.get("coin_xp", 0)) is int and 0 <= item.get("coin_xp", 0) <= 5000 else 0,
            "candy_xp": item.get("candy_xp", 0) if type(item.get("candy_xp", 0)) is int and 0 <= item.get("candy_xp", 0) <= 5000 else 0,
            "battle_xp": item.get("battle_xp", 0) if type(item.get("battle_xp", 0)) is int and 0 <= item.get("battle_xp", 0) <= 5000 else 0,
        })

        cleaned.append(entry)

    if not cleaned:
        cleaned = [pokemon(143)]

    p["collection"] = cleaned

    if p.get("partner_uid") not in [
        mon["uid"] for mon in cleaned
    ]:
        p["partner_uid"] = cleaned[0]["uid"]

    try:
        goal = float(
            p.get("goal_hours", p.get("target", 8))
        )
        p["goal_hours"] = (
            goal
            if math.isfinite(goal) and 1 <= goal <= 14
            else 8.0
        )
    except (ValueError, TypeError):
        p["goal_hours"] = 8.0

    p.setdefault("sleep_start", p.get("active_start"))

    for record in p["records"]:
        record.setdefault(
            "goal",
            record.get("target", p["goal_hours"]),
        )
        record.setdefault("awake_minutes", 0)
        record.setdefault("feeling", "미입력")
        record.setdefault("memo", "")

    for record in p["cycles"]:
        for field, _, _ in METRICS:
            record.setdefault(field, None)

    sync_growth(p)
    return p


# =====================================
# 로그인·자동 저장
# =====================================

class SaveConnectionError(Exception):
    pass


def cloud_config():
    try:
        url = str(
            st.secrets["SUPABASE_URL"]
        ).rstrip("/")

        key = str(
            st.secrets.get("SUPABASE_KEY")
            or st.secrets.get("SUPABASE_PUBLISHABLE_KEY")
            or ""
        )

    except (KeyError, FileNotFoundError):
        return None

    host = urlparse(url)

    if (
        host.scheme != "https"
        or not host.hostname
        or not host.hostname.endswith(".supabase.co")
    ):
        raise SaveConnectionError(
            "SUPABASE_URL을 확인해 주세요."
        )

    if not key or key.startswith("sb_secret_"):
        raise SaveConnectionError(
            "SUPABASE_KEY에는 publishable key 또는 "
            "anon public key를 넣어 주세요."
        )

    if key.count(".") == 2:
        try:
            encoded = key.split(".")[1]
            claims = json.loads(
                base64.urlsafe_b64decode(
                    encoded + "=" * (-len(encoded) % 4)
                )
            )
        except (ValueError, TypeError):
            claims = {}

        if claims.get("role") == "service_role":
            raise SaveConnectionError(
                "관리자 키 대신 publishable 또는 "
                "anon public 키를 사용해 주세요."
            )

    return url, key


def cloud_request(
    method,
    route,
    *,
    authenticated=True,
    retry=True,
    **kwargs,
):
    config = cloud_config()

    if config is None:
        raise SaveConnectionError(
            "Streamlit Secrets를 설정해 주세요."
        )

    url, key = config

    headers = {
        "apikey": key,
        "Content-Type": "application/json",
    }
    headers.update(kwargs.pop("headers", {}))

    if authenticated:
        auth = st.session_state.get("_sfc_auth")

        if not auth:
            raise SaveConnectionError(
                "다시 로그인해 주세요."
            )

        headers["Authorization"] = (
            "Bearer " + auth["access_token"]
        )

    try:
        response = requests.request(
            method,
            url + route,
            headers=headers,
            timeout=(4, 8),
            **kwargs,
        )
    except requests.RequestException:
        raise SaveConnectionError(
            "서버 연결에 실패했어요. 인터넷 연결과 "
            "Supabase 프로젝트 상태를 확인해 주세요."
        ) from None

    if (
        response.status_code == 401
        and authenticated
        and retry
    ):
        refreshed = cloud_request(
            "POST",
            "/auth/v1/token?grant_type=refresh_token",
            authenticated=False,
            json={
                "refresh_token":
                    st.session_state["_sfc_auth"][
                        "refresh_token"
                    ]
            },
        )

        st.session_state["_sfc_auth"] = refreshed

        return cloud_request(
            method,
            route,
            authenticated=True,
            retry=False,
            headers={
                k: v
                for k, v in headers.items()
                if k not in ("Authorization", "apikey")
            },
            **kwargs,
        )

    if not response.ok:
        if (
            "/auth/" in route
            and response.status_code in (400, 401, 422)
        ):
            raise SaveConnectionError(
                "이메일·비밀번호 또는 계정의 "
                "확인 상태를 확인해 주세요."
            )

        if response.status_code == 429:
            raise SaveConnectionError(
                "요청이 많아요. 잠시 후 다시 시도해 주세요."
            )

        if response.status_code == 409:
            raise SaveConnectionError(
                "다른 탭에서 먼저 기록을 저장했어요. "
                "백업한 다음 새로고침해 주세요."
            )

        raise SaveConnectionError(
            "저장 공간에 접근하지 못했어요. "
            "sleep_free_saves 테이블과 사용자 권한을 "
            "확인해 주세요. 프로젝트가 일시정지됐다면 "
            "Supabase 대시보드에서 복원해 주세요."
        )

    if not response.content:
        return None

    try:
        return response.json()
    except ValueError:
        raise SaveConnectionError(
            "서버 응답이 올바르지 않아요."
        ) from None


def cloud_fingerprint(payload):
    text = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        allow_nan=False,
    )

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def cloud_payload():
    return {
        "version": "sleep-free-pokemon-3",
        "profiles": st.session_state.sf_profiles,
        "active_profile": st.session_state.sf_user,
        "wallet": wallet(),
        "page": st.session_state.get("sf_page", "home"),
    }


def cloud_save():
    if not st.session_state.get("_sfc_loaded"):
        return

    payload = json.loads(json.dumps(cloud_payload()))
    fingerprint = None

    try:
        fingerprint = cloud_fingerprint(payload)

        if fingerprint == st.session_state.get("_sfc_hash"):
            return

        user_id = (
            st.session_state["_sfc_auth"]["user"]["id"]
        )
        expected = st.session_state.get("_sfc_updated_at")

        if expected is None:
            rows = cloud_request(
                "POST",
                "/rest/v1/sleep_free_saves",
                headers={
                    "Prefer": "return=representation"
                },
                json={
                    "user_id": user_id,
                    "save_data": payload,
                },
            )

        else:
            rows = cloud_request(
                "PATCH",
                "/rest/v1/sleep_free_saves",
                params={
                    "user_id": "eq." + user_id,
                    "updated_at": "eq." + expected,
                },
                headers={
                    "Prefer": "return=representation"
                },
                json={
                    "save_data": payload,
                    "updated_at": now().isoformat(),
                },
            )

        if not rows or len(rows) != 1:
            raise SaveConnectionError(
                "다른 탭이나 기기에서 먼저 기록이 바뀌었어요. "
                "자동 덮어쓰기를 멈췄어요. "
                "현재 기록을 백업한 뒤 새로고침해 주세요."
            )

        st.session_state["_sfc_updated_at"] = (
            rows[0]["updated_at"]
        )
        st.session_state.pop("_sfc_pending_save", None)
        st.session_state["_sfc_hash"] = fingerprint
        st.session_state["_sfc_saved"] = (
            now().strftime("%m/%d %H:%M:%S")
        )

    except (
        SaveConnectionError,
        ValueError,
        KeyError,
        TypeError,
    ) as error:
        try:
            remote = cloud_request("GET", "/rest/v1/sleep_free_saves",
                params={"user_id": "eq." + st.session_state["_sfc_auth"]["user"]["id"],
                        "select": "save_data,updated_at"})
            if fingerprint and remote and cloud_fingerprint(remote[0]["save_data"]) == fingerprint:
                st.session_state["_sfc_updated_at"] = remote[0]["updated_at"]
                st.session_state["_sfc_hash"] = fingerprint
                st.session_state.pop("_sfc_pending_save", None)
                return
        except (SaveConnectionError, KeyError, TypeError, ValueError):
            pass
        st.session_state["_sfc_pending_save"] = True
        st.warning("변경 내용을 유지하고 있어요. " + str(error))

        st.download_button(
            "미저장 기록 백업",
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            ),
            file_name="sleep_free_unsaved.json",
            mime="application/json",
            key="_sfc_unsaved_download",
        )

        st.caption(
            "아직 저장되지 않은 변경이 있어요. "
            "연결을 복구한 뒤 재시도하거나 "
            "JSON을 먼저 다운로드해 주세요."
        )

        if st.button(
            "자동 저장 다시 시도",
            key="_sfc_retry_save",
        ):
            st.rerun()

        st.stop()


_browser_auth = components.declare_component(
    "sleep_free_browser_auth", path=str(Path(__file__).parent / "auth_component")
)


def remember_session():
    auth = st.session_state.get("_sfc_auth")
    action = "write" if auth else "read"
    token = auth.get("refresh_token", "") if auth else ""
    if st.session_state.get("_sfc_clear_browser"):
        action, token = "clear", ""
    result = _browser_auth(action=action, token=token, key="browser_auth")
    if not result:
        st.caption("로그인 정보를 확인하고 있어요…")
        st.stop()
    if result.get("error"):
        st.warning("브라우저 저장소가 차단되어 새로고침 시 다시 로그인해야 해요.")
        return
    if action == "clear":
        if result.get("action") != "clear":
            st.stop()
        st.session_state.pop("_sfc_clear_browser", None)
        st.session_state["_sfc_browser_checked"] = True
        return
    if auth:
        # Wait for the browser to acknowledge the new rotated token.
        if result.get("action") != "write" or result.get("token") != token:
            st.stop()
        return
    if st.session_state.get("_sfc_browser_checked"):
        return
    st.session_state["_sfc_browser_checked"] = True
    saved = result.get("token")
    if saved:
        try:
            restored = cloud_request(
                "POST", "/auth/v1/token?grant_type=refresh_token",
                authenticated=False, json={"refresh_token": saved},
            )
            if not (restored or {}).get("access_token"):
                raise SaveConnectionError("로그인이 만료됐어요.")
            st.session_state["_sfc_auth"] = restored
            st.rerun()
        except SaveConnectionError:
            st.session_state["_sfc_clear_browser"] = True
            st.rerun()



# PokeAPI species/evolution CSV snapshot, 2026-11-07. [name, id, rarity, minimum encounter level]
ENCOUNTER_CATALOG = [
    ['이상해씨', 1, '일반', 1],
    ['이상해풀', 2, '초희귀', 16],
    ['이상해꽃', 3, '초희귀', 32],
    ['파이리', 4, '일반', 1],
    ['리자드', 5, '초희귀', 16],
    ['리자몽', 6, '초희귀', 36],
    ['꼬부기', 7, '일반', 1],
    ['어니부기', 8, '초희귀', 16],
    ['거북왕', 9, '초희귀', 36],
    ['캐터피', 10, '일반', 1],
    ['단데기', 11, '일반', 7],
    ['버터플', 12, '초희귀', 15],
    ['뿔충이', 13, '일반', 1],
    ['딱충이', 14, '일반', 7],
    ['독침붕', 15, '초희귀', 15],
    ['구구', 16, '일반', 1],
    ['피죤', 17, '일반', 18],
    ['피죤투', 18, '초희귀', 36],
    ['꼬렛', 19, '일반', 1],
    ['레트라', 20, '일반', 20],
    ['깨비참', 21, '일반', 1],
    ['깨비드릴조', 22, '희귀', 20],
    ['아보', 23, '일반', 1],
    ['아보크', 24, '희귀', 22],
    ['피카츄', 25, '희귀', 20],
    ['라이츄', 26, '희귀', 21],
    ['모래두지', 27, '일반', 1],
    ['고지', 28, '희귀', 20],
    ['니드런♀', 29, '일반', 1],
    ['니드리나', 30, '일반', 16],
    ['니드퀸', 31, '초희귀', 20],
    ['니드런♂', 32, '일반', 1],
    ['니드리노', 33, '일반', 16],
    ['니드킹', 34, '초희귀', 20],
    ['삐삐', 35, '희귀', 20],
    ['픽시', 36, '초희귀', 21],
    ['식스테일', 37, '희귀', 5],
    ['나인테일', 38, '희귀', 20],
    ['푸린', 39, '희귀', 20],
    ['푸크린', 40, '희귀', 21],
    ['주뱃', 41, '일반', 1],
    ['골뱃', 42, '희귀', 22],
    ['뚜벅쵸', 43, '일반', 1],
    ['냄새꼬', 44, '일반', 21],
    ['라플레시아', 45, '초희귀', 22],
    ['파라스', 46, '일반', 1],
    ['파라섹트', 47, '희귀', 24],
    ['콘팡', 48, '일반', 1],
    ['도나리', 49, '희귀', 31],
    ['디그다', 50, '일반', 1],
    ['닥트리오', 51, '희귀', 26],
    ['나옹', 52, '일반', 1],
    ['페르시온', 53, '희귀', 20],
    ['고라파덕', 54, '일반', 1],
    ['골덕', 55, '희귀', 33],
    ['망키', 56, '일반', 1],
    ['성원숭', 57, '희귀', 28],
    ['가디', 58, '희귀', 5],
    ['윈디', 59, '희귀', 20],
    ['발챙이', 60, '일반', 1],
    ['슈륙챙이', 61, '일반', 25],
    ['강챙이', 62, '초희귀', 26],
    ['캐이시', 63, '희귀', 5],
    ['윤겔라', 64, '희귀', 16],
    ['후딘', 65, '희귀', 20],
    ['알통몬', 66, '일반', 1],
    ['근육몬', 67, '희귀', 28],
    ['괴력몬', 68, '초희귀', 29],
    ['모다피', 69, '일반', 1],
    ['우츠동', 70, '일반', 21],
    ['우츠보트', 71, '초희귀', 22],
    ['왕눈해', 72, '일반', 1],
    ['독파리', 73, '희귀', 30],
    ['꼬마돌', 74, '일반', 1],
    ['데구리', 75, '일반', 25],
    ['딱구리', 76, '초희귀', 26],
    ['포니타', 77, '일반', 1],
    ['날쌩마', 78, '희귀', 40],
    ['야돈', 79, '일반', 1],
    ['야도란', 80, '희귀', 20],
    ['코일', 81, '일반', 1],
    ['레어코일', 82, '희귀', 30],
    ['파오리', 83, '초희귀', 15],
    ['두두', 84, '일반', 1],
    ['두트리오', 85, '초희귀', 31],
    ['쥬쥬', 86, '일반', 1],
    ['쥬레곤', 87, '희귀', 34],
    ['질퍽이', 88, '일반', 1],
    ['질뻐기', 89, '희귀', 38],
    ['셀러', 90, '일반', 1],
    ['파르셀', 91, '희귀', 20],
    ['고오스', 92, '희귀', 5],
    ['고우스트', 93, '희귀', 25],
    ['팬텀', 94, '초희귀', 26],
    ['롱스톤', 95, '초희귀', 15],
    ['슬리프', 96, '일반', 1],
    ['슬리퍼', 97, '희귀', 26],
    ['크랩', 98, '일반', 1],
    ['킹크랩', 99, '희귀', 28],
    ['찌리리공', 100, '일반', 1],
    ['붐볼', 101, '희귀', 20],
    ['아라리', 102, '희귀', 5],
    ['나시', 103, '초희귀', 20],
    ['탕구리', 104, '일반', 1],
    ['텅구리', 105, '희귀', 28],
    ['시라소몬', 106, '초희귀', 20],
    ['홍수몬', 107, '초희귀', 20],
    ['내루미', 108, '초희귀', 15],
    ['또가스', 109, '일반', 1],
    ['또도가스', 110, '희귀', 35],
    ['뿔카노', 111, '일반', 1],
    ['코뿌리', 112, '희귀', 42],
    ['럭키', 113, '초희귀', 20],
    ['덩쿠리', 114, '초희귀', 15],
    ['캥카', 115, '초희귀', 15],
    ['쏘드라', 116, '일반', 1],
    ['시드라', 117, '희귀', 32],
    ['콘치', 118, '일반', 1],
    ['왕콘치', 119, '희귀', 33],
    ['별가사리', 120, '일반', 1],
    ['아쿠스타', 121, '희귀', 20],
    ['마임맨', 122, '초희귀', 20],
    ['스라크', 123, '초희귀', 15],
    ['루주라', 124, '초희귀', 30],
    ['에레브', 125, '초희귀', 30],
    ['마그마', 126, '초희귀', 30],
    ['쁘사이저', 127, '초희귀', 15],
    ['켄타로스', 128, '초희귀', 15],
    ['잉어킹', 129, '일반', 1],
    ['갸라도스', 130, '초희귀', 20],
    ['라프라스', 131, '초희귀', 15],
    ['메타몽', 132, '초희귀', 15],
    ['이브이', 133, '희귀', 5],
    ['샤미드', 134, '초희귀', 20],
    ['쥬피썬더', 135, '초희귀', 20],
    ['부스터', 136, '초희귀', 20],
    ['폴리곤', 137, '초희귀', 15],
    ['암나이트', 138, '초희귀', 15],
    ['암스타', 139, '초희귀', 40],
    ['투구', 140, '초희귀', 15],
    ['투구푸스', 141, '초희귀', 40],
    ['프테라', 142, '초희귀', 15],
    ['잠만보', 143, '초희귀', 20],
    ['프리져', 144, '전설', 35],
    ['썬더', 145, '전설', 35],
    ['파이어', 146, '전설', 35],
    ['미뇽', 147, '초희귀', 15],
    ['신뇽', 148, '초희귀', 30],
    ['망나뇽', 149, '초희귀', 55],
    ['뮤츠', 150, '전설', 35],
    ['뮤', 151, '환상', 45],
    ['치코리타', 152, '희귀', 5],
    ['베이리프', 153, '초희귀', 16],
    ['메가니움', 154, '초희귀', 32],
    ['브케인', 155, '희귀', 5],
    ['마그케인', 156, '초희귀', 15],
    ['블레이범', 157, '초희귀', 36],
    ['리아코', 158, '희귀', 5],
    ['엘리게이', 159, '초희귀', 18],
    ['장크로다일', 160, '초희귀', 30],
    ['꼬리선', 161, '일반', 1],
    ['다꼬리', 162, '희귀', 15],
    ['부우부', 163, '일반', 1],
    ['야부엉', 164, '희귀', 20],
    ['레디바', 165, '일반', 1],
    ['레디안', 166, '희귀', 18],
    ['페이검', 167, '일반', 1],
    ['아리아도스', 168, '희귀', 22],
    ['크로뱃', 169, '희귀', 23],
    ['초라기', 170, '일반', 1],
    ['랜턴', 171, '희귀', 27],
    ['피츄', 172, '일반', 1],
    ['삐', 173, '일반', 1],
    ['푸푸린', 174, '일반', 1],
    ['토게피', 175, '희귀', 5],
    ['토게틱', 176, '희귀', 20],
    ['네이티', 177, '일반', 1],
    ['네이티오', 178, '희귀', 25],
    ['메리프', 179, '일반', 1],
    ['보송송', 180, '일반', 15],
    ['전룡', 181, '초희귀', 30],
    ['아르코', 182, '초희귀', 22],
    ['마릴', 183, '일반', 20],
    ['마릴리', 184, '희귀', 21],
    ['꼬지모', 185, '희귀', 20],
    ['왕구리', 186, '초희귀', 26],
    ['통통코', 187, '일반', 1],
    ['두코', 188, '일반', 18],
    ['솜솜코', 189, '초희귀', 27],
    ['에이팜', 190, '초희귀', 15],
    ['해너츠', 191, '일반', 1],
    ['해루미', 192, '일반', 20],
    ['왕자리', 193, '희귀', 5],
    ['우파', 194, '일반', 1],
    ['누오', 195, '희귀', 20],
    ['에브이', 196, '초희귀', 20],
    ['블래키', 197, '초희귀', 20],
    ['니로우', 198, '초희귀', 15],
    ['야도킹', 199, '희귀', 20],
    ['무우마', 200, '초희귀', 15],
    ['안농', 201, '일반', 1],
    ['마자용', 202, '초희귀', 15],
    ['키링키', 203, '희귀', 5],
    ['피콘', 204, '일반', 1],
    ['쏘콘', 205, '희귀', 31],
    ['노고치', 206, '일반', 1],
    ['글라이거', 207, '희귀', 5],
    ['강철톤', 208, '초희귀', 20],
    ['블루', 209, '일반', 1],
    ['그랑블루', 210, '희귀', 23],
    ['침바루', 211, '초희귀', 15],
    ['핫삼', 212, '초희귀', 20],
    ['단단지', 213, '일반', 1],
    ['헤라크로스', 214, '초희귀', 15],
    ['포푸니', 215, '희귀', 5],
    ['깜지곰', 216, '일반', 1],
    ['링곰', 217, '희귀', 30],
    ['마그마그', 218, '일반', 1],
    ['마그카르고', 219, '희귀', 38],
    ['꾸꾸리', 220, '일반', 1],
    ['메꾸리', 221, '희귀', 33],
    ['코산호', 222, '희귀', 5],
    ['총어', 223, '일반', 1],
    ['대포무노', 224, '희귀', 25],
    ['딜리버드', 225, '초희귀', 15],
    ['만타인', 226, '초희귀', 20],
    ['무장조', 227, '초희귀', 15],
    ['델빌', 228, '일반', 1],
    ['헬가', 229, '초희귀', 24],
    ['킹드라', 230, '초희귀', 33],
    ['코코리', 231, '일반', 1],
    ['코리갑', 232, '희귀', 25],
    ['폴리곤2', 233, '초희귀', 20],
    ['노라키', 234, '초희귀', 15],
    ['루브도', 235, '초희귀', 15],
    ['배루키', 236, '희귀', 5],
    ['카포에라', 237, '초희귀', 20],
    ['뽀뽀라', 238, '초희귀', 15],
    ['에레키드', 239, '초희귀', 15],
    ['마그비', 240, '초희귀', 15],
    ['밀탱크', 241, '초희귀', 15],
    ['해피너스', 242, '초희귀', 21],
    ['라이코', 243, '전설', 35],
    ['앤테이', 244, '전설', 35],
    ['스이쿤', 245, '전설', 35],
    ['애버라스', 246, '초희귀', 15],
    ['데기라스', 247, '초희귀', 30],
    ['마기라스', 248, '초희귀', 55],
    ['루기아', 249, '전설', 35],
    ['칠색조', 250, '전설', 35],
    ['세레비', 251, '환상', 45],
    ['나무지기', 252, '희귀', 5],
    ['나무돌이', 253, '초희귀', 16],
    ['나무킹', 254, '초희귀', 36],
    ['아차모', 255, '희귀', 5],
    ['영치코', 256, '초희귀', 16],
    ['번치코', 257, '초희귀', 36],
    ['물짱이', 258, '희귀', 5],
    ['늪짱이', 259, '초희귀', 16],
    ['대짱이', 260, '초희귀', 36],
    ['포챠나', 261, '일반', 1],
    ['그라에나', 262, '일반', 18],
    ['지그제구리', 263, '일반', 1],
    ['직구리', 264, '희귀', 20],
    ['개무소', 265, '일반', 1],
    ['실쿤', 266, '일반', 7],
    ['뷰티플라이', 267, '초희귀', 15],
    ['카스쿤', 268, '일반', 7],
    ['독케일', 269, '초희귀', 15],
    ['연꽃몬', 270, '일반', 1],
    ['로토스', 271, '일반', 14],
    ['로파파', 272, '초희귀', 20],
    ['도토링', 273, '일반', 1],
    ['잎새코', 274, '일반', 14],
    ['다탱구', 275, '초희귀', 20],
    ['테일로', 276, '일반', 1],
    ['스왈로', 277, '초희귀', 22],
    ['갈모매', 278, '일반', 1],
    ['패리퍼', 279, '초희귀', 25],
    ['랄토스', 280, '희귀', 5],
    ['킬리아', 281, '일반', 20],
    ['가디안', 282, '초희귀', 30],
    ['비구술', 283, '일반', 1],
    ['비나방', 284, '희귀', 22],
    ['버섯꼬', 285, '일반', 1],
    ['버섯모', 286, '희귀', 23],
    ['게을로', 287, '일반', 1],
    ['발바로', 288, '일반', 18],
    ['게을킹', 289, '초희귀', 36],
    ['토중몬', 290, '일반', 1],
    ['아이스크', 291, '일반', 20],
    ['껍질몬', 292, '초희귀', 20],
    ['소곤룡', 293, '일반', 1],
    ['노공룡', 294, '일반', 20],
    ['폭음룡', 295, '초희귀', 40],
    ['마크탕', 296, '일반', 1],
    ['하리뭉', 297, '일반', 24],
    ['루리리', 298, '일반', 1],
    ['코코파스', 299, '일반', 1],
    ['에나비', 300, '일반', 1],
    ['델케티', 301, '희귀', 20],
    ['깜까미', 302, '초희귀', 15],
    ['입치트', 303, '초희귀', 15],
    ['가보리', 304, '일반', 1],
    ['갱도라', 305, '희귀', 32],
    ['보스로라', 306, '초희귀', 42],
    ['요가랑', 307, '일반', 1],
    ['요가램', 308, '희귀', 37],
    ['썬더라이', 309, '일반', 1],
    ['썬더볼트', 310, '초희귀', 26],
    ['플러시', 311, '일반', 1],
    ['마이농', 312, '일반', 1],
    ['볼비트', 313, '일반', 1],
    ['네오비트', 314, '일반', 1],
    ['로젤리아', 315, '일반', 20],
    ['꼴깍몬', 316, '일반', 1],
    ['꿀꺽몬', 317, '희귀', 26],
    ['샤프니아', 318, '일반', 1],
    ['샤크니아', 319, '희귀', 30],
    ['고래왕자', 320, '일반', 1],
    ['고래왕', 321, '희귀', 40],
    ['둔타', 322, '일반', 1],
    ['폭타', 323, '일반', 33],
    ['코터스', 324, '희귀', 5],
    ['피그점프', 325, '일반', 1],
    ['피그킹', 326, '희귀', 32],
    ['얼루기', 327, '일반', 1],
    ['톱치', 328, '일반', 1],
    ['비브라바', 329, '일반', 35],
    ['플라이곤', 330, '초희귀', 45],
    ['선인왕', 331, '일반', 1],
    ['밤선인', 332, '희귀', 32],
    ['파비코', 333, '일반', 1],
    ['파비코리', 334, '초희귀', 35],
    ['쟝고', 335, '희귀', 5],
    ['세비퍼', 336, '희귀', 5],
    ['루나톤', 337, '초희귀', 15],
    ['솔록', 338, '초희귀', 15],
    ['미꾸리', 339, '일반', 1],
    ['메깅', 340, '희귀', 30],
    ['가재군', 341, '일반', 1],
    ['가재장군', 342, '일반', 30],
    ['오뚝군', 343, '일반', 1],
    ['점토도리', 344, '희귀', 36],
    ['릴링', 345, '초희귀', 15],
    ['릴리요', 346, '초희귀', 40],
    ['아노딥스', 347, '초희귀', 15],
    ['아말도', 348, '초희귀', 40],
    ['빈티나', 349, '일반', 1],
    ['밀로틱', 350, '희귀', 20],
    ['캐스퐁', 351, '초희귀', 15],
    ['켈리몬', 352, '일반', 1],
    ['어둠대신', 353, '일반', 1],
    ['다크펫', 354, '초희귀', 37],
    ['해골몽', 355, '일반', 1],
    ['미라몽', 356, '희귀', 37],
    ['트로피우스', 357, '일반', 1],
    ['치렁', 358, '초희귀', 20],
    ['앱솔', 359, '초희귀', 15],
    ['마자', 360, '일반', 1],
    ['눈꼬마', 361, '일반', 1],
    ['얼음귀신', 362, '희귀', 42],
    ['대굴레오', 363, '일반', 1],
    ['씨레오', 364, '일반', 32],
    ['씨카이저', 365, '초희귀', 44],
    ['진주몽', 366, '일반', 1],
    ['헌테일', 367, '희귀', 20],
    ['분홍장이', 368, '희귀', 20],
    ['시라칸', 369, '초희귀', 15],
    ['사랑동이', 370, '일반', 1],
    ['아공이', 371, '초희귀', 15],
    ['쉘곤', 372, '초희귀', 30],
    ['보만다', 373, '초희귀', 50],
    ['메탕', 374, '초희귀', 15],
    ['메탕구', 375, '초희귀', 20],
    ['메타그로스', 376, '초희귀', 45],
    ['레지락', 377, '전설', 35],
    ['레지아이스', 378, '전설', 35],
    ['레지스틸', 379, '전설', 35],
    ['라티아스', 380, '전설', 35],
    ['라티오스', 381, '전설', 35],
    ['가이오가', 382, '전설', 35],
    ['그란돈', 383, '전설', 35],
    ['레쿠쟈', 384, '전설', 35],
    ['지라치', 385, '환상', 45],
    ['테오키스', 386, '환상', 45],
    ['모부기', 387, '희귀', 5],
    ['수풀부기', 388, '초희귀', 18],
    ['토대부기', 389, '초희귀', 32],
    ['불꽃숭이', 390, '희귀', 5],
    ['파이숭이', 391, '초희귀', 15],
    ['초염몽', 392, '초희귀', 36],
    ['팽도리', 393, '희귀', 5],
    ['팽태자', 394, '초희귀', 16],
    ['엠페르트', 395, '초희귀', 36],
    ['찌르꼬', 396, '일반', 1],
    ['찌르버드', 397, '일반', 14],
    ['찌르호크', 398, '초희귀', 34],
    ['비버니', 399, '일반', 1],
    ['비버통', 400, '일반', 15],
    ['귀뚤뚜기', 401, '일반', 1],
    ['귀뚤톡크', 402, '초희귀', 15],
    ['꼬링크', 403, '일반', 1],
    ['럭시오', 404, '일반', 15],
    ['렌트라', 405, '초희귀', 30],
    ['꼬몽울', 406, '일반', 1],
    ['로즈레이드', 407, '희귀', 21],
    ['두개도스', 408, '초희귀', 15],
    ['램펄드', 409, '초희귀', 30],
    ['방패톱스', 410, '초희귀', 15],
    ['바리톱스', 411, '초희귀', 30],
    ['도롱충이', 412, '일반', 1],
    ['도롱마담', 413, '초희귀', 20],
    ['나메일', 414, '초희귀', 20],
    ['세꿀버리', 415, '일반', 1],
    ['비퀸', 416, '초희귀', 21],
    ['파치리스', 417, '일반', 1],
    ['브이젤', 418, '일반', 1],
    ['플로젤', 419, '희귀', 26],
    ['체리버', 420, '일반', 1],
    ['체리꼬', 421, '희귀', 25],
    ['깝질무', 422, '일반', 1],
    ['트리토돈', 423, '희귀', 30],
    ['겟핸보숭', 424, '초희귀', 20],
    ['흔들풍손', 425, '일반', 1],
    ['둥실라이드', 426, '희귀', 28],
    ['이어롤', 427, '일반', 1],
    ['이어롭', 428, '희귀', 20],
    ['무우마직', 429, '초희귀', 20],
    ['돈크로우', 430, '초희귀', 20],
    ['나옹마', 431, '일반', 1],
    ['몬냥이', 432, '희귀', 38],
    ['랑딸랑', 433, '일반', 1],
    ['스컹뿡', 434, '일반', 1],
    ['스컹탱크', 435, '희귀', 34],
    ['동미러', 436, '일반', 1],
    ['동탁군', 437, '희귀', 33],
    ['꼬지지', 438, '일반', 1],
    ['흉내내', 439, '일반', 1],
    ['핑복', 440, '일반', 1],
    ['페라페', 441, '초희귀', 15],
    ['화강돌', 442, '희귀', 5],
    ['딥상어동', 443, '초희귀', 15],
    ['한바이트', 444, '초희귀', 24],
    ['한카리아스', 445, '초희귀', 48],
    ['먹고자', 446, '희귀', 5],
    ['리오르', 447, '희귀', 5],
    ['루카리오', 448, '초희귀', 20],
    ['히포포타스', 449, '일반', 1],
    ['하마돈', 450, '희귀', 34],
    ['스콜피', 451, '일반', 1],
    ['드래피온', 452, '초희귀', 40],
    ['삐딱구리', 453, '일반', 1],
    ['독개굴', 454, '희귀', 37],
    ['무스틈니', 455, '일반', 1],
    ['형광어', 456, '일반', 1],
    ['네오라이트', 457, '희귀', 31],
    ['타만타', 458, '초희귀', 15],
    ['눈쓰개', 459, '일반', 1],
    ['눈설왕', 460, '희귀', 40],
    ['포푸니라', 461, '초희귀', 20],
    ['자포코일', 462, '초희귀', 31],
    ['내룸벨트', 463, '초희귀', 20],
    ['거대코뿌리', 464, '초희귀', 43],
    ['덩쿠림보', 465, '초희귀', 20],
    ['에레키블', 466, '초희귀', 31],
    ['마그마번', 467, '초희귀', 31],
    ['토게키스', 468, '초희귀', 21],
    ['메가자리', 469, '초희귀', 20],
    ['리피아', 470, '초희귀', 20],
    ['글레이시아', 471, '초희귀', 20],
    ['글라이온', 472, '초희귀', 20],
    ['맘모꾸리', 473, '희귀', 34],
    ['폴리곤Z', 474, '초희귀', 21],
    ['엘레이드', 475, '초희귀', 21],
    ['대코파스', 476, '희귀', 20],
    ['야느와르몽', 477, '초희귀', 38],
    ['눈여아', 478, '희귀', 20],
    ['로토무', 479, '초희귀', 15],
    ['유크시', 480, '전설', 35],
    ['엠라이트', 481, '전설', 35],
    ['아그놈', 482, '전설', 35],
    ['디아루가', 483, '전설', 35],
    ['펄기아', 484, '전설', 35],
    ['히드런', 485, '전설', 35],
    ['레지기가스', 486, '전설', 35],
    ['기라티나', 487, '전설', 35],
    ['크레세리아', 488, '전설', 35],
    ['피오네', 489, '환상', 45],
    ['마나피', 490, '환상', 45],
    ['다크라이', 491, '환상', 45],
    ['쉐이미', 492, '환상', 45],
    ['아르세우스', 493, '환상', 45],
    ['비크티니', 494, '환상', 45],
    ['주리비얀', 495, '희귀', 5],
    ['샤비', 496, '초희귀', 17],
    ['샤로다', 497, '초희귀', 36],
    ['뚜꾸리', 498, '희귀', 5],
    ['차오꿀', 499, '초희귀', 17],
    ['염무왕', 500, '초희귀', 36],
    ['수댕이', 501, '희귀', 5],
    ['쌍검자비', 502, '초희귀', 17],
    ['대검귀', 503, '초희귀', 36],
    ['보르쥐', 504, '일반', 1],
    ['보르그', 505, '일반', 20],
    ['요테리', 506, '일반', 1],
    ['하데리어', 507, '일반', 16],
    ['바랜드', 508, '초희귀', 32],
    ['쌔비냥', 509, '일반', 1],
    ['레파르다스', 510, '희귀', 20],
    ['야나프', 511, '일반', 1],
    ['야나키', 512, '희귀', 20],
    ['바오프', 513, '일반', 1],
    ['바오키', 514, '희귀', 20],
    ['앗차프', 515, '일반', 1],
    ['앗차키', 516, '희귀', 20],
    ['몽나', 517, '일반', 1],
    ['몽얌나', 518, '희귀', 20],
    ['콩둘기', 519, '일반', 1],
    ['유토브', 520, '일반', 21],
    ['켄호로우', 521, '초희귀', 32],
    ['줄뮤마', 522, '일반', 1],
    ['제브라이카', 523, '희귀', 27],
    ['단굴', 524, '일반', 1],
    ['암트르', 525, '일반', 25],
    ['기가이어스', 526, '초희귀', 26],
    ['또르박쥐', 527, '일반', 1],
    ['맘박쥐', 528, '초희귀', 20],
    ['두더류', 529, '일반', 1],
    ['몰드류', 530, '희귀', 31],
    ['다부니', 531, '일반', 1],
    ['으랏차', 532, '일반', 1],
    ['토쇠골', 533, '희귀', 25],
    ['노보청', 534, '초희귀', 26],
    ['동챙이', 535, '일반', 1],
    ['두까비', 536, '일반', 25],
    ['두빅굴', 537, '초희귀', 36],
    ['던지미', 538, '초희귀', 15],
    ['타격귀', 539, '초희귀', 15],
    ['두르보', 540, '일반', 1],
    ['두르쿤', 541, '일반', 20],
    ['모아머', 542, '초희귀', 21],
    ['마디네', 543, '일반', 1],
    ['휠구', 544, '일반', 22],
    ['펜드라', 545, '초희귀', 30],
    ['소미안', 546, '일반', 1],
    ['엘풍', 547, '희귀', 20],
    ['치릴리', 548, '일반', 1],
    ['드레디어', 549, '희귀', 20],
    ['배쓰나이', 550, '초희귀', 15],
    ['깜눈크', 551, '일반', 1],
    ['악비르', 552, '희귀', 29],
    ['악비아르', 553, '초희귀', 40],
    ['달막화', 554, '일반', 1],
    ['불비달마', 555, '희귀', 20],
    ['마라카치', 556, '일반', 1],
    ['돌살이', 557, '일반', 1],
    ['암팰리스', 558, '희귀', 34],
    ['곤율랭', 559, '일반', 1],
    ['곤율거니', 560, '희귀', 39],
    ['심보러', 561, '초희귀', 15],
    ['데스마스', 562, '일반', 1],
    ['데스니칸', 563, '희귀', 34],
    ['프로토가', 564, '초희귀', 15],
    ['늑골라', 565, '초희귀', 37],
    ['아켄', 566, '초희귀', 15],
    ['아케오스', 567, '초희귀', 37],
    ['깨봉이', 568, '일반', 1],
    ['더스트나', 569, '희귀', 36],
    ['조로아', 570, '희귀', 5],
    ['조로아크', 571, '초희귀', 30],
    ['치라미', 572, '일반', 1],
    ['치라치노', 573, '희귀', 20],
    ['고디탱', 574, '일반', 1],
    ['고디보미', 575, '희귀', 32],
    ['고디모아젤', 576, '희귀', 41],
    ['유니란', 577, '일반', 1],
    ['듀란', 578, '희귀', 32],
    ['란쿨루스', 579, '희귀', 41],
    ['꼬지보리', 580, '일반', 1],
    ['스완나', 581, '초희귀', 35],
    ['바닐프티', 582, '일반', 1],
    ['바닐리치', 583, '일반', 35],
    ['배바닐라', 584, '초희귀', 47],
    ['사철록', 585, '일반', 1],
    ['바라철록', 586, '희귀', 34],
    ['에몽가', 587, '일반', 1],
    ['딱정곤', 588, '일반', 1],
    ['슈바르고', 589, '희귀', 20],
    ['깜놀버슬', 590, '일반', 1],
    ['뽀록나', 591, '희귀', 39],
    ['탱그릴', 592, '일반', 1],
    ['탱탱겔', 593, '희귀', 40],
    ['맘복치', 594, '희귀', 5],
    ['파쪼옥', 595, '일반', 1],
    ['전툴라', 596, '희귀', 36],
    ['철시드', 597, '일반', 1],
    ['너트령', 598, '희귀', 40],
    ['기어르', 599, '일반', 1],
    ['기기어르', 600, '희귀', 38],
    ['기기기어르', 601, '초희귀', 49],
    ['저리어', 602, '일반', 1],
    ['저리릴', 603, '희귀', 39],
    ['저리더프', 604, '초희귀', 40],
    ['리그레', 605, '일반', 1],
    ['벰크', 606, '희귀', 42],
    ['불켜미', 607, '일반', 1],
    ['램프라', 608, '희귀', 41],
    ['샹델라', 609, '초희귀', 42],
    ['터검니', 610, '희귀', 5],
    ['액슨도', 611, '희귀', 38],
    ['액스라이즈', 612, '초희귀', 48],
    ['코고미', 613, '일반', 1],
    ['툰베어', 614, '희귀', 37],
    ['프리지오', 615, '초희귀', 15],
    ['쪼마리', 616, '일반', 1],
    ['어지리더', 617, '희귀', 20],
    ['메더', 618, '희귀', 5],
    ['비조푸', 619, '일반', 1],
    ['비조도', 620, '초희귀', 50],
    ['크리만', 621, '초희귀', 15],
    ['골비람', 622, '일반', 1],
    ['골루그', 623, '희귀', 43],
    ['자망칼', 624, '일반', 1],
    ['절각참', 625, '초희귀', 52],
    ['버프론', 626, '초희귀', 15],
    ['수리둥보', 627, '일반', 1],
    ['워글', 628, '희귀', 54],
    ['벌차이', 629, '일반', 1],
    ['버랜지나', 630, '희귀', 54],
    ['앤티골', 631, '희귀', 5],
    ['아이앤트', 632, '희귀', 5],
    ['모노두', 633, '초희귀', 15],
    ['디헤드', 634, '초희귀', 50],
    ['삼삼드래', 635, '초희귀', 64],
    ['활화르바', 636, '초희귀', 15],
    ['불카모스', 637, '초희귀', 59],
    ['코바르온', 638, '전설', 35],
    ['테라키온', 639, '전설', 35],
    ['비리디온', 640, '전설', 35],
    ['토네로스', 641, '전설', 35],
    ['볼트로스', 642, '전설', 35],
    ['레시라무', 643, '전설', 35],
    ['제크로무', 644, '전설', 35],
    ['랜드로스', 645, '전설', 35],
    ['큐레무', 646, '전설', 35],
    ['케르디오', 647, '환상', 45],
    ['메로엣타', 648, '환상', 45],
    ['게노세크트', 649, '환상', 45],
    ['도치마론', 650, '희귀', 5],
    ['도치보구', 651, '초희귀', 16],
    ['브리가론', 652, '초희귀', 36],
    ['푸호꼬', 653, '희귀', 5],
    ['테르나', 654, '초희귀', 16],
    ['마폭시', 655, '초희귀', 36],
    ['개구마르', 656, '희귀', 5],
    ['개굴반장', 657, '초희귀', 16],
    ['개굴닌자', 658, '초희귀', 36],
    ['파르빗', 659, '일반', 1],
    ['파르토', 660, '일반', 20],
    ['화살꼬빈', 661, '일반', 1],
    ['불화살빈', 662, '일반', 17],
    ['파이어로', 663, '초희귀', 35],
    ['분이벌레', 664, '일반', 1],
    ['분떠도리', 665, '일반', 9],
    ['비비용', 666, '초희귀', 15],
    ['레오꼬', 667, '일반', 1],
    ['화염레오', 668, '희귀', 35],
    ['플라베베', 669, '일반', 1],
    ['플라엣테', 670, '일반', 19],
    ['플라제스', 671, '초희귀', 20],
    ['메이클', 672, '일반', 1],
    ['고고트', 673, '초희귀', 32],
    ['판짱', 674, '일반', 1],
    ['부란다', 675, '희귀', 32],
    ['트리미앙', 676, '일반', 1],
    ['냐스퍼', 677, '일반', 1],
    ['냐오닉스', 678, '희귀', 25],
    ['단칼빙', 679, '일반', 1],
    ['쌍검킬', 680, '희귀', 35],
    ['킬가르도', 681, '초희귀', 36],
    ['슈쁘', 682, '일반', 1],
    ['프레프티르', 683, '일반', 20],
    ['나룸퍼프', 684, '일반', 1],
    ['나루림', 685, '일반', 20],
    ['오케이징', 686, '일반', 1],
    ['칼라마네로', 687, '희귀', 30],
    ['거북손손', 688, '일반', 1],
    ['거북손데스', 689, '초희귀', 39],
    ['수레기', 690, '일반', 1],
    ['드래캄', 691, '희귀', 48],
    ['완철포', 692, '일반', 1],
    ['블로스터', 693, '희귀', 37],
    ['목도리키텔', 694, '일반', 1],
    ['일레도리자드', 695, '희귀', 20],
    ['티고라스', 696, '초희귀', 15],
    ['견고라스', 697, '초희귀', 39],
    ['아마루스', 698, '초희귀', 15],
    ['아마루르가', 699, '초희귀', 39],
    ['님피아', 700, '초희귀', 20],
    ['루차불', 701, '희귀', 5],
    ['데덴네', 702, '일반', 1],
    ['멜리시', 703, '희귀', 5],
    ['미끄메라', 704, '초희귀', 15],
    ['미끄네일', 705, '초희귀', 40],
    ['미끄래곤', 706, '초희귀', 50],
    ['클레피', 707, '희귀', 5],
    ['나목령', 708, '일반', 1],
    ['대로트', 709, '희귀', 20],
    ['호바귀', 710, '일반', 1],
    ['펌킨인', 711, '희귀', 20],
    ['꽁어름', 712, '일반', 1],
    ['크레베이스', 713, '희귀', 37],
    ['음뱃', 714, '일반', 1],
    ['음번', 715, '초희귀', 48],
    ['제르네아스', 716, '전설', 35],
    ['이벨타르', 717, '전설', 35],
    ['지가르데', 718, '전설', 35],
    ['디안시', 719, '환상', 45],
    ['후파', 720, '환상', 45],
    ['볼케니온', 721, '환상', 45],
    ['나몰빼미', 722, '희귀', 5],
    ['빼미스로우', 723, '초희귀', 17],
    ['모크나이퍼', 724, '초희귀', 34],
    ['냐오불', 725, '희귀', 5],
    ['냐오히트', 726, '초희귀', 17],
    ['어흥염', 727, '초희귀', 34],
    ['누리공', 728, '희귀', 5],
    ['키요공', 729, '초희귀', 17],
    ['누리레느', 730, '초희귀', 34],
    ['콕코구리', 731, '일반', 1],
    ['크라파', 732, '일반', 14],
    ['왕큰부리', 733, '초희귀', 28],
    ['영구스', 734, '일반', 1],
    ['형사구스', 735, '일반', 20],
    ['턱지충이', 736, '일반', 1],
    ['전지충이', 737, '일반', 20],
    ['투구뿌논', 738, '초희귀', 21],
    ['오기지게', 739, '일반', 1],
    ['모단단게', 740, '희귀', 20],
    ['춤추새', 741, '초희귀', 15],
    ['에블리', 742, '일반', 1],
    ['에리본', 743, '희귀', 25],
    ['암멍이', 744, '일반', 1],
    ['루가루암', 745, '희귀', 25],
    ['약어리', 746, '희귀', 5],
    ['시마사리', 747, '일반', 1],
    ['더시마사리', 748, '희귀', 38],
    ['머드나기', 749, '일반', 1],
    ['만마드', 750, '희귀', 30],
    ['물거미', 751, '일반', 1],
    ['깨비물거미', 752, '희귀', 22],
    ['짜랑랑', 753, '일반', 1],
    ['라란티스', 754, '희귀', 34],
    ['자마슈', 755, '일반', 1],
    ['마셰이드', 756, '희귀', 24],
    ['야도뇽', 757, '일반', 1],
    ['염뉴트', 758, '초희귀', 33],
    ['포곰곰', 759, '일반', 1],
    ['이븐곰', 760, '희귀', 27],
    ['달콤아', 761, '일반', 1],
    ['달무리나', 762, '일반', 18],
    ['달코퀸', 763, '초희귀', 20],
    ['큐아링', 764, '희귀', 5],
    ['하랑우탄', 765, '초희귀', 15],
    ['내던숭이', 766, '초희귀', 15],
    ['꼬시레', 767, '희귀', 5],
    ['갑주무사', 768, '초희귀', 30],
    ['모래꿍', 769, '일반', 1],
    ['모래성이당', 770, '희귀', 42],
    ['해무기', 771, '희귀', 5],
    ['타입:널', 772, '전설', 35],
    ['실버디', 773, '전설', 36],
    ['메테노', 774, '초희귀', 15],
    ['자말라', 775, '초희귀', 15],
    ['폭거북스', 776, '희귀', 5],
    ['토게데마루', 777, '일반', 1],
    ['따라큐', 778, '초희귀', 15],
    ['치갈기', 779, '희귀', 5],
    ['할비롱', 780, '희귀', 5],
    ['타타륜', 781, '초희귀', 15],
    ['짜랑꼬', 782, '초희귀', 15],
    ['짜랑고우', 783, '초희귀', 35],
    ['짜랑고우거', 784, '초희귀', 45],
    ['카푸꼬꼬꼭', 785, '전설', 35],
    ['카푸나비나', 786, '전설', 35],
    ['카푸브루루', 787, '전설', 35],
    ['카푸느지느', 788, '전설', 35],
    ['코스모그', 789, '전설', 35],
    ['코스모움', 790, '전설', 43],
    ['솔가레오', 791, '전설', 53],
    ['루나아라', 792, '전설', 53],
    ['텅비드', 793, '초희귀', 15],
    ['매시붕', 794, '초희귀', 15],
    ['페로코체', 795, '초희귀', 15],
    ['전수목', 796, '초희귀', 15],
    ['철화구야', 797, '초희귀', 15],
    ['종이신도', 798, '초희귀', 15],
    ['악식킹', 799, '초희귀', 15],
    ['네크로즈마', 800, '전설', 35],
    ['마기아나', 801, '환상', 45],
    ['마샤도', 802, '환상', 45],
    ['베베놈', 803, '초희귀', 15],
    ['아고용', 804, '초희귀', 20],
    ['차곡차곡', 805, '초희귀', 15],
    ['두파팡', 806, '초희귀', 15],
    ['제라오라', 807, '환상', 45],
    ['멜탄', 808, '환상', 45],
    ['멜메탈', 809, '환상', 46],
    ['흥나숭', 810, '희귀', 5],
    ['채키몽', 811, '초희귀', 16],
    ['고릴타', 812, '초희귀', 35],
    ['염버니', 813, '희귀', 5],
    ['래비풋', 814, '초희귀', 16],
    ['에이스번', 815, '초희귀', 35],
    ['울머기', 816, '희귀', 5],
    ['누겔레온', 817, '초희귀', 16],
    ['인텔리레온', 818, '초희귀', 35],
    ['탐리스', 819, '일반', 1],
    ['요씽리스', 820, '희귀', 24],
    ['파라꼬', 821, '일반', 1],
    ['파크로우', 822, '일반', 18],
    ['아머까오', 823, '초희귀', 38],
    ['두루지벌레', 824, '일반', 1],
    ['레돔벌레', 825, '일반', 10],
    ['이올브', 826, '초희귀', 30],
    ['훔처우', 827, '일반', 1],
    ['폭슬라이', 828, '일반', 18],
    ['꼬모카', 829, '일반', 1],
    ['백솜모카', 830, '희귀', 20],
    ['우르', 831, '일반', 1],
    ['배우르', 832, '일반', 24],
    ['깨물부기', 833, '일반', 1],
    ['갈가부기', 834, '희귀', 22],
    ['멍파치', 835, '일반', 1],
    ['펄스멍', 836, '초희귀', 25],
    ['탄동', 837, '일반', 1],
    ['탄차곤', 838, '일반', 18],
    ['석탄산', 839, '초희귀', 34],
    ['과사삭벌레', 840, '일반', 1],
    ['애프룡', 841, '초희귀', 20],
    ['단지래플', 842, '초희귀', 20],
    ['모래뱀', 843, '일반', 1],
    ['사다이사', 844, '일반', 36],
    ['윽우지', 845, '초희귀', 15],
    ['찌로꼬치', 846, '일반', 1],
    ['꼬치조', 847, '희귀', 26],
    ['일레즌', 848, '희귀', 5],
    ['스트린더', 849, '초희귀', 30],
    ['태우지네', 850, '일반', 1],
    ['다태우지네', 851, '희귀', 28],
    ['때때무노', 852, '일반', 1],
    ['케오퍼스', 853, '초희귀', 20],
    ['데인차', 854, '일반', 1],
    ['포트데스', 855, '희귀', 20],
    ['몸지브림', 856, '일반', 1],
    ['손지브림', 857, '일반', 32],
    ['브리무음', 858, '초희귀', 42],
    ['메롱꿍', 859, '일반', 1],
    ['쏘겨모', 860, '일반', 32],
    ['오롱털', 861, '초희귀', 42],
    ['가로막구리', 862, '초희귀', 35],
    ['나이킹', 863, '희귀', 28],
    ['산호르곤', 864, '초희귀', 38],
    ['창파나이트', 865, '초희귀', 20],
    ['마임꽁꽁', 866, '초희귀', 42],
    ['데스판', 867, '희귀', 20],
    ['마빌크', 868, '일반', 1],
    ['마휘핑', 869, '희귀', 20],
    ['대여르', 870, '초희귀', 15],
    ['찌르성게', 871, '희귀', 5],
    ['누니머기', 872, '일반', 1],
    ['모스노우', 873, '희귀', 20],
    ['돌헨진', 874, '희귀', 5],
    ['빙큐보', 875, '희귀', 5],
    ['에써르', 876, '초희귀', 15],
    ['모르페코', 877, '일반', 1],
    ['끼리동', 878, '일반', 1],
    ['대왕끼리동', 879, '희귀', 34],
    ['파치래곤', 880, '초희귀', 15],
    ['파치르돈', 881, '초희귀', 15],
    ['어래곤', 882, '초희귀', 15],
    ['어치르돈', 883, '초희귀', 15],
    ['두랄루돈', 884, '초희귀', 15],
    ['드라꼰', 885, '초희귀', 15],
    ['드래런치', 886, '초희귀', 50],
    ['드래펄트', 887, '초희귀', 60],
    ['자시안', 888, '전설', 35],
    ['자마젠타', 889, '전설', 35],
    ['무한다이노', 890, '전설', 35],
    ['치고마', 891, '전설', 35],
    ['우라오스', 892, '전설', 36],
    ['자루도', 893, '환상', 45],
    ['레지에레키', 894, '전설', 35],
    ['레지드래고', 895, '전설', 35],
    ['블리자포스', 896, '전설', 35],
    ['레이스포스', 897, '전설', 35],
    ['버드렉스', 898, '전설', 35],
    ['신비록', 899, '일반', 20],
    ['사마자르', 900, '일반', 20],
    ['다투곰', 901, '희귀', 31],
    ['대쓰여너', 902, '일반', 20],
    ['포푸니크', 903, '일반', 20],
    ['장침바루', 904, '일반', 20],
    ['러브로스', 905, '전설', 35],
    ['나오하', 906, '희귀', 5],
    ['나로테', 907, '초희귀', 16],
    ['마스카나', 908, '초희귀', 36],
    ['뜨아거', 909, '희귀', 5],
    ['악뜨거', 910, '초희귀', 16],
    ['라우드본', 911, '초희귀', 36],
    ['꾸왁스', 912, '희귀', 5],
    ['아꾸왁', 913, '초희귀', 16],
    ['웨이니발', 914, '초희귀', 36],
    ['맛보돈', 915, '일반', 1],
    ['퍼퓨돈', 916, '희귀', 18],
    ['타랜툴라', 917, '일반', 1],
    ['트래피더', 918, '일반', 15],
    ['콩알뚜기', 919, '일반', 1],
    ['엑스레그', 920, '초희귀', 24],
    ['빠모', 921, '일반', 1],
    ['빠모트', 922, '희귀', 18],
    ['빠르모트', 923, '초희귀', 20],
    ['두리쥐', 924, '일반', 1],
    ['파밀리쥐', 925, '희귀', 25],
    ['쫀도기', 926, '일반', 1],
    ['바우첼', 927, '희귀', 26],
    ['미니브', 928, '일반', 1],
    ['올리뇨', 929, '일반', 25],
    ['올리르바', 930, '초희귀', 35],
    ['시비꼬', 931, '일반', 1],
    ['베베솔트', 932, '일반', 1],
    ['스태솔트', 933, '일반', 24],
    ['콜로솔트', 934, '초희귀', 38],
    ['카르본', 935, '희귀', 5],
    ['카디나르마', 936, '초희귀', 20],
    ['파라블레이즈', 937, '초희귀', 20],
    ['빈나두', 938, '일반', 1],
    ['찌리배리', 939, '희귀', 20],
    ['찌리비', 940, '일반', 1],
    ['찌리비크', 941, '희귀', 25],
    ['오라티프', 942, '일반', 1],
    ['마피티프', 943, '희귀', 30],
    ['땃쭈르', 944, '일반', 1],
    ['태깅구르', 945, '희귀', 28],
    ['그푸리', 946, '일반', 1],
    ['공푸리', 947, '초희귀', 20],
    ['들눈해', 948, '일반', 1],
    ['육파리', 949, '희귀', 30],
    ['절벼게', 950, '일반', 1],
    ['캡싸이', 951, '일반', 1],
    ['스코빌런', 952, '희귀', 20],
    ['구르데', 953, '일반', 1],
    ['베라카스', 954, '초희귀', 20],
    ['하느라기', 955, '일반', 1],
    ['클레스퍼트라', 956, '희귀', 35],
    ['어리짱', 957, '일반', 1],
    ['벼리짱', 958, '희귀', 24],
    ['두드리짱', 959, '초희귀', 38],
    ['바다그다', 960, '일반', 1],
    ['바닥트리오', 961, '희귀', 26],
    ['떨구새', 962, '초희귀', 15],
    ['맨돌핀', 963, '일반', 1],
    ['돌핀맨', 964, '초희귀', 38],
    ['부르롱', 965, '일반', 1],
    ['부르르룸', 966, '희귀', 40],
    ['모토마', 967, '일반', 1],
    ['꿈트렁', 968, '초희귀', 15],
    ['초롱순', 969, '희귀', 5],
    ['킬라플로르', 970, '초희귀', 35],
    ['망망이', 971, '일반', 1],
    ['묘두기', 972, '희귀', 30],
    ['꼬이밍고', 973, '희귀', 5],
    ['터벅고래', 974, '일반', 1],
    ['우락고래', 975, '희귀', 20],
    ['가비루사', 976, '희귀', 5],
    ['어써러셔', 977, '초희귀', 15],
    ['싸리용', 978, '희귀', 5],
    ['저승갓숭', 979, '초희귀', 29],
    ['토오', 980, '희귀', 20],
    ['키키링', 981, '초희귀', 20],
    ['노고고치', 982, '초희귀', 20],
    ['대도각참', 983, '초희귀', 53],
    ['위대한엄니', 984, '초희귀', 15],
    ['우렁찬꼬리', 985, '희귀', 5],
    ['사나운버섯', 986, '희귀', 5],
    ['날개치는머리', 987, '초희귀', 15],
    ['땅을기는날개', 988, '초희귀', 15],
    ['모래털가죽', 989, '초희귀', 15],
    ['무쇠바퀴', 990, '초희귀', 15],
    ['무쇠보따리', 991, '희귀', 5],
    ['무쇠손', 992, '희귀', 5],
    ['무쇠머리', 993, '초희귀', 15],
    ['무쇠독나방', 994, '초희귀', 15],
    ['무쇠가시', 995, '초희귀', 15],
    ['드니차', 996, '초희귀', 15],
    ['드니꽁', 997, '초희귀', 35],
    ['드닐레이브', 998, '초희귀', 54],
    ['모으령', 999, '초희귀', 15],
    ['타부자고', 1000, '초희귀', 20],
    ['총지엔', 1001, '전설', 35],
    ['파오젠', 1002, '전설', 35],
    ['딩루', 1003, '전설', 35],
    ['위유이', 1004, '전설', 35],
    ['고동치는달', 1005, '초희귀', 15],
    ['무쇠무인', 1006, '초희귀', 15],
    ['코라이돈', 1007, '전설', 35],
    ['미라이돈', 1008, '전설', 35],
    ['굽이치는물결', 1009, '초희귀', 15],
    ['무쇠잎새', 1010, '초희귀', 15],
    ['과미르', 1011, '초희귀', 20],
    ['차데스', 1012, '일반', 1],
    ['그우린차', 1013, '희귀', 20],
    ['조타구', 1014, '전설', 35],
    ['이야후', 1015, '전설', 35],
    ['기로치', 1016, '전설', 35],
    ['오거폰', 1017, '전설', 35],
    ['브리두라스', 1018, '초희귀', 20],
    ['과미드라', 1019, '초희귀', 21],
    ['꿰뚫는화염', 1020, '초희귀', 15],
    ['날뛰는우레', 1021, '초희귀', 15],
    ['무쇠암석', 1022, '초희귀', 15],
    ['무쇠감투', 1023, '초희귀', 15],
    ['테라파고스', 1024, '전설', 35],
    ['복숭악동', 1025, '환상', 45],
]


BALLS = {
    "몬스터볼": {"price": 20, "power": 1.0},
    "슈퍼볼": {"price": 50, "power": 1.5},
    "하이퍼볼": {"price": 100, "power": 2.0},
    "마스터볼": {"price": 2000, "power": 100.0},
}
RARITY_LEVEL = {"일반": 1, "희귀": 5, "초희귀": 15, "전설": 35, "환상": 45}
SALE_BASE = {"일반": 10, "희귀": 30, "초희귀": 100, "전설": 400, "환상": 700}


def wallet():
    return st.session_state.setdefault("_sfc_wallet", {
        "coins": 100, "balls": {k: 0 for k in BALLS},
        "reward_days": {}, "codes": [], "sold_uids": [],
    })


def action_ready():
    # One accepted economy action per second, across all game buttons.
    tick = time.monotonic()
    if tick - st.session_state.get("_sfc_action_time", -100) < 1.0:
        st.info("처리 중이에요. 잠깐 기다린 뒤 눌러 주세요.")
        return False
    st.session_state["_sfc_action_time"] = tick
    return True


CANDIES = {
    "small": {"name": "작은 경험치 사탕", "xp": 10, "price": 100},
    "medium": {"name": "중간 경험치 사탕", "xp": 50, "price": 450},
    "large": {"name": "큰 경험치 사탕", "xp": 200, "price": 1600},
}


def candy_inventory():
    inventory = wallet().setdefault("candies", {})
    for kind in CANDIES:
        inventory.setdefault(kind, 0)
    return inventory


def buy_candies(kind, quantity):
    if kind not in CANDIES or type(quantity) is not int or not 1 <= quantity <= 10000:
        return False
    cost = CANDIES[kind]["price"] * quantity
    if wallet()["coins"] < cost or not action_ready():
        return False
    wallet()["coins"] -= cost
    candy_inventory()[kind] += quantity
    return True


def xp_to_max_level(mon):
    return max(0.0, sum(range(mon["level"], 100)) - mon["xp"])


def use_candies(mon_uid, kind, quantity):
    profile = current()
    sync_growth(profile)
    mon = next((m for m in profile["collection"] if m["uid"] == mon_uid), None)
    if not mon or mon["level"] >= 100 or kind not in CANDIES:
        return None
    if type(quantity) is not int or quantity < 1:
        return None
    needed = xp_to_max_level(mon)
    maximum = math.ceil(needed / CANDIES[kind]["xp"])
    if quantity > min(candy_inventory()[kind], maximum) or not action_ready():
        return None
    gained = min(CANDIES[kind]["xp"] * quantity, math.ceil(needed))
    old_level = mon["level"]
    candy_inventory()[kind] -= quantity
    mon["candy_xp"] = mon.get("candy_xp", 0) + gained
    sync_growth(profile)
    return {"old_level": old_level, "new_level": mon["level"], "gained": gained}


def home_candy_panel(mon):
    st.subheader("🍬 경험치 사탕 사용")
    inventory = candy_inventory()
    st.caption(" · ".join(f"{details['name']} {inventory[k]:,}개" for k, details in CANDIES.items()))
    if mon["level"] >= 100:
        st.info("이 포켓몬은 최고 레벨 Lv.100이에요.")
        return
    available = [k for k in CANDIES if inventory[k] > 0]
    if not available:
        st.info("보유한 경험치 사탕이 없어요. 오른쪽 위 상점에서 구매해 주세요.")
        return
    kind = st.selectbox(
        "먹일 사탕", available,
        format_func=lambda k: f"{CANDIES[k]['name']} · {CANDIES[k]['xp']} XP · 보유 {inventory[k]}개",
        key=f"candy_kind_{mon['uid']}",
    )
    maximum = min(inventory[kind], math.ceil(xp_to_max_level(mon) / CANDIES[kind]["xp"]))
    amount_key = f"candy_use_amount_{mon['uid']}_{kind}"
    if amount_key in st.session_state:
        st.session_state[amount_key] = max(1, min(maximum, int(st.session_state[amount_key])))
    quantity = int(st.number_input("사용 수량", min_value=1, max_value=maximum, value=1, step=1, key=amount_key))
    gained = min(CANDIES[kind]["xp"] * quantity, math.ceil(xp_to_max_level(mon)))
    predicted, progress = level_from_xp(mon["base_level"], mon["total_xp"] + gained)
    st.write(f"**{mon['name']} · Lv.{mon['level']} → Lv.{predicted} · 경험치 +{gained:,} XP**")
    st.caption("최고 레벨에 도달하면 초과 경험치는 반영되지 않으며 사용한 사탕은 소모돼요. 진화는 조건 충족 후 직접 선택해 주세요.")
    if st.button(
        f"🍬 {mon['name']}에게 {quantity:,}개 먹이기",
        key=f"feed_candy_{mon['uid']}_{kind}_{mon['level']}",
        use_container_width=True,
    ):
        result = use_candies(mon["uid"], kind, quantity)
        if result:
            success(f"🍬 {mon['name']}에게 경험치 +{result['gained']} XP! Lv.{result['old_level']} → Lv.{result['new_level']}")



# PokeAPI data snapshot 2026-11-08; default forms and supported level-up moves.
BATTLE_DATA = json.loads(zlib.decompress(base64.b64decode('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')))

# Battle rules use neutral nature, IV 15, EV 0; supported move effects only.
STAT_LABELS = {2: "공격", 3: "방어", 4: "특수공격", 5: "특수방어", 6: "스피드", 7: "명중", 8: "회피"}
STATUS_LABELS = {"": "정상", "sleep": "수면", "paralysis": "마비", "burn": "화상", "poison": "독", "toxic": "맹독", "freeze": "얼음"}


def move_data(move_id):
    return BATTLE_DATA["moves"][str(move_id)]


def species_battle_data(mon):
    return BATTLE_DATA["mons"][str(mon["number"])]


def learned_moves(mon):
    rows = species_battle_data(mon)["learn"]
    return list(dict.fromkeys(mid for level, mid in rows if level <= mon["level"])) or [165]


def equipped_moves(mon):
    options = learned_moves(mon)
    saved = [mid for mid in mon.get("move_layout", []) if mid in options]
    if saved:
        return list(dict.fromkeys(saved))[:4]
    attacks = [mid for mid in options if move_data(mid)["class"] != 1]
    types = species_battle_data(mon)["types"]
    attacks.sort(key=lambda mid: (move_data(mid)["type"] in types, move_data(mid)["power"], options.index(mid)), reverse=True)
    picked = attacks[:2]
    for mid in reversed(options):
        if mid not in picked:
            picked.append(mid)
        if len(picked) >= 4:
            break
    return picked[:4] or [165]


def fighter(mon):
    base = species_battle_data(mon)
    level = mon["level"]
    stats = [math.floor((2 * value + 15) * level / 100) + (level + 10 if i == 0 else 5) for i, value in enumerate(base["stats"])]
    if mon["number"] == 292:
        stats[0] = 1
    return {"uid": mon["uid"], "name": mon["name"], "number": mon["number"], "level": level, "shiny": mon.get("shiny", False), "image_id": mon.get("image_id", mon["number"]),
            "types": base["types"], "stats": stats, "hp": stats[0], "max_hp": stats[0],
            "status": "", "status_turns": 0, "toxic_turn": 0, "flinch": False,
            "stages": {str(i): 0 for i in range(2, 9)},
            "moves": [{"id": mid, "pp": move_data(mid)["pp"]} for mid in equipped_moves(mon)]}


def type_multiplier(attack_type, defender_types):
    result = 1.0
    for target in defender_types:
        result *= BATTLE_DATA["chart"].get(f"{attack_type},{target}", 1.0)
    return result


def stage_multiplier(stage, accuracy=False):
    stage = max(-6, min(6, int(stage)))
    base = 3 if accuracy else 2
    return (base + stage) / base if stage >= 0 else base / (base - stage)


def effective_stat(actor, stat_id, critical=False, attacking=False):
    stage = actor["stages"].get(str(stat_id), 0)
    if critical:
        stage = max(0, stage) if attacking else min(0, stage)
    result = actor["stats"][stat_id - 1] * stage_multiplier(stage)
    if stat_id == 6 and actor["status"] == "paralysis":
        result *= .5
    return max(1, result)


def battle_log(battle, text):
    battle["log"].append(text)
    battle["log"] = battle["log"][-20:]


def ensure_battle():
    profile = current()
    wild = profile.get("encounter")
    if not wild:
        return None
    battle = profile.get("battle")
    if isinstance(battle, dict) and battle.get("encounter_uid") == wild["uid"] and battle.get("version") == 1:
        return battle
    chosen = profile.get("home_selected_uid", profile["partner_uid"])
    ally = next((m for m in profile["collection"] if m["uid"] == chosen), partner())
    battle = {"version": 1, "encounter_uid": wild["uid"], "ally": fighter(ally), "wild": fighter(wild),
              "turn": 0, "log": [f"{ally['name']}과(와) 야생 {wild['name']}의 전투 시작!"]}
    profile["battle"] = battle
    return battle


def major_status(actor, target, status, battle, move=None):
    if target["hp"] <= 0 or target["status"]:
        return False
    immune = (status == "paralysis" and 13 in target["types"] or
              status in ("poison", "toxic") and any(t in target["types"] for t in (4, 9)) or
              status == "burn" and 10 in target["types"] or status == "freeze" and 15 in target["types"])
    if move and move["idname"] in ("sleep-powder", "poison-powder", "stun-spore", "spore") and 12 in target["types"]:
        immune = True
    if move and move["idname"] == "thunder-wave" and type_multiplier(13, target["types"]) == 0:
        immune = True
    if immune:
        battle_log(battle, f"{target['name']}은(는) 타입 때문에 {STATUS_LABELS[status]}에 면역이에요.")
        return False
    target["status"] = status
    target["status_turns"] = random.randint(1, 3) if status == "sleep" else 0
    target["toxic_turn"] = 0
    battle_log(battle, f"{target['name']}에게 {STATUS_LABELS[status]} 발생!")
    return True


def can_act(actor, battle):
    if actor["flinch"]:
        actor["flinch"] = False
        battle_log(battle, f"{actor['name']}은(는) 풀이 죽어 움직이지 못했어요.")
        return False
    if actor["status"] == "sleep":
        if actor["status_turns"] > 0:
            actor["status_turns"] -= 1
            battle_log(battle, f"{actor['name']}은(는) 잠들어 있어요.")
            return False
        actor["status"] = ""
        battle_log(battle, f"{actor['name']}이(가) 깨어났어요!")
    if actor["status"] == "freeze":
        if random.random() < .2:
            actor["status"] = ""
            battle_log(battle, f"{actor['name']}의 얼음이 녹았어요!")
        else:
            battle_log(battle, f"{actor['name']}은(는) 얼어서 움직일 수 없어요.")
            return False
    if actor["status"] == "paralysis" and random.random() < .25:
        battle_log(battle, f"{actor['name']}은(는) 마비로 움직이지 못했어요.")
        return False
    return True


def damage_value(actor, target, move, critical=False, roll=1.0):
    effect = move["effect"]
    multiplier = 1 if effect == -1 else type_multiplier(move["type"], target["types"])
    if multiplier == 0:
        return 0
    if effect in (41, 42, 88):
        return max(1, target["hp"] // 2) if effect == 41 else 40 if effect == 42 else actor["level"]
    attack_stat, defense_stat = (2, 3) if move["class"] == 2 else (4, 5)
    attack = effective_stat(actor, attack_stat, critical, True)
    defense = effective_stat(target, defense_stat, critical, False)
    power = move["power"]
    damage = math.floor(math.floor((2 * actor["level"] / 5 + 2) * power * attack / defense) / 50) + 2
    stab = 1.5 if move["type"] in actor["types"] and effect != -1 else 1
    burn = .5 if actor["status"] == "burn" and move["class"] == 2 else 1
    return max(1, math.floor(damage * stab * multiplier * burn * (1.5 if critical else 1) * roll))


def _resolve_move_effect(actor, target, move_id, battle):
    if actor["hp"] <= 0 or target["hp"] <= 0 or not can_act(actor, battle):
        return
    move = move_data(move_id)
    slot = next((m for m in actor["moves"] if m["id"] == move_id and m["pp"] > 0), None)
    if move_id != 165:
        if slot is None:
            return
        slot["pp"] -= 1
    battle_log(battle, f"{actor['name']}의 {move['name']}!")
    battle["_last_move_used"] = [actor["uid"], move_id]
    stage = actor["stages"].get("7", 0) - target["stages"].get("8", 0)
    accuracy = move["accuracy"] * stage_multiplier(stage, True)
    if move["effect"] not in (18, 79, -1) and move["target"] != 7 and random.random() * 100 >= accuracy:
        battle_log(battle, "공격이 빗나갔어요.")
        return
    effect = move["effect"]
    if effect == 86:
        battle_log(battle, "아무 일도 일어나지 않았어요.")
        return
    if effect == 26:
        for side in (actor, target):
            side["stages"] = {str(i): 0 for i in range(2, 9)}
        battle_log(battle, "모든 능력치 변화가 원래대로 돌아왔어요.")
        return
    if effect == 38:
        actor["hp"] = actor["max_hp"]
        actor["status"] = "sleep"
        actor["status_turns"] = 2
        battle_log(battle, f"{actor['name']}은(는) 체력을 모두 회복하고 잠들었어요.")
        return
    if move["healing"] > 0:
        recovered = min(actor["max_hp"] - actor["hp"], max(1, actor["max_hp"] * move["healing"] // 100))
        actor["hp"] += recovered
        battle_log(battle, f"{actor['name']}의 HP +{recovered}")
    damage = 0
    if move["class"] != 1:
        hits = 2 if effect == 45 else random.randint(2, 5) if effect == 30 else 1
        crit_chance = [1/24, 1/8, 1/2, 1][min(3, max(0, move["crit"]))]
        critical = effect not in (41, 42, 88) and random.random() < crit_chance
        hit_count = 0
        for _ in range(hits):
            if target["hp"] <= 0:
                break
            amount = damage_value(actor, target, move, critical, random.randint(85, 100) / 100)
            if effect == 102:
                amount = min(amount, max(0, target["hp"] - 1))
            dealt = min(target["hp"], amount)
            target["hp"] -= dealt
            damage += dealt
            hit_count += 1
        battle_log(battle, f"{target['name']}의 HP -{damage}" + (f" · {hit_count}회 공격" if hits > 1 else ""))
        multiplier = type_multiplier(move["type"], target["types"]) if effect != -1 else 1
        if multiplier == 0:
            battle_log(battle, "타입 면역! 효과가 없어요.")
            return
        if multiplier > 1:
            battle_log(battle, f"효과가 굉장해요! ×{multiplier:g}")
        elif multiplier < 1:
            battle_log(battle, f"효과가 별로예요. ×{multiplier:g}")
        if critical and damage:
            battle_log(battle, "급소에 맞았어요!")
        if target["status"] == "freeze" and move["type"] == 10 and damage:
            target["status"] = ""
            battle_log(battle, "불꽃 공격으로 얼음이 녹았어요.")
    if move["drain"] > 0 and damage:
        recovered = min(actor["max_hp"] - actor["hp"], max(1, damage * move["drain"] // 100))
        actor["hp"] += recovered
        battle_log(battle, f"흡수로 HP +{recovered}")
    elif move["drain"] < 0 and damage:
        recoil = max(1, damage * -move["drain"] // 100)
        actor["hp"] = max(0, actor["hp"] - recoil)
        battle_log(battle, f"반동으로 HP -{recoil}")
    if effect == -1:
        actor["hp"] = max(0, actor["hp"] - max(1, actor["max_hp"] // 4))
        battle_log(battle, "발버둥의 반동을 받았어요.")
    if target["hp"] <= 0:
        return
    status = "toxic" if effect == 34 else move["ailment"]
    if status in STATUS_LABELS and status:
        chance = (move["ailment_chance"] or move["chance"] or 100) if move["class"] == 1 else (move["ailment_chance"] or move["chance"])
        if random.random() * 100 < chance:
            major_status(actor, target, status, battle, move)
    if move["changes"]:
        receiver = actor if move["target"] == 7 else target
        chance = 100 if move["class"] == 1 else move["stat_chance"] or move["chance"]
        if random.random() * 100 < chance:
            for stat, change in move["changes"]:
                key = str(stat)
                if key not in receiver["stages"]:
                    continue
                old = receiver["stages"][key]
                receiver["stages"][key] = max(-6, min(6, old + change))
                actual = receiver["stages"][key] - old
                battle_log(battle, f"{receiver['name']}의 {STAT_LABELS[stat]} {actual:+d}단계")
    if move["flinch"] and random.random() * 100 < move["flinch"]:
        target["flinch"] = True


def battle_frame(battle):
    return {"ally_hp": battle["ally"]["hp"], "wild_hp": battle["wild"]["hp"],
            "ally_status": STATUS_LABELS[battle["ally"]["status"]],
            "wild_status": STATUS_LABELS[battle["wild"]["status"]]}


def begin_battle_scene(battle):
    frame = battle_frame(battle)
    battle["scene_start"] = {"ally": frame["ally_hp"], "wild": frame["wild_hp"],
                             "ally_status": frame["ally_status"], "wild_status": frame["wild_status"]}
    battle["scene_events"] = []
    battle["scene_id"] = new_id()


def apply_move(actor, target, move_id, battle):
    side = "ally" if actor["uid"] == battle["ally"]["uid"] else "wild"
    other = "wild" if side == "ally" else "ally"
    previous_hp = target["hp"]
    battle.pop("_last_move_used", None)
    _resolve_move_effect(actor, target, move_id, battle)
    used = battle.pop("_last_move_used", None) == [actor["uid"], move_id]
    move = move_data(move_id)
    damage = max(0, previous_hp - target["hp"])
    event = dict(battle_frame(battle), actor=side, target=other,
                 kind=("attack" if move["class"] != 1 else "status") if used else "wait",
                 damage=damage,
                 text=f"{actor['name']}의 {move['name']}!" + (f" HP −{damage}" if damage else "") if used else battle["log"][-1])
    battle.setdefault("scene_events", []).append(event)


def award_battle_xp(battle):
    ledger = wallet().setdefault("battle_rewarded", [])
    encounter_id = battle["encounter_uid"]
    if encounter_id in ledger:
        return None
    ledger.append(encounter_id)
    profile = current()
    sync_growth(profile)
    mon = next((m for m in profile["collection"] if m["uid"] == battle["ally"]["uid"]), None)
    if mon is None:
        return None
    old_level = mon["level"]
    base = BATTLE_DATA["mons"][str(battle["wild"]["number"])].get("base_experience", 64)
    raw_xp = max(1, base * battle["wild"]["level"] // 7)
    gained = min(raw_xp, math.ceil(xp_to_max_level(mon)))
    mon["battle_xp"] = mon.get("battle_xp", 0) + gained
    sync_growth(profile)
    text = f"{mon['name']} 경험치 +{gained} XP · Lv.{old_level} → Lv.{mon['level']}"
    if old_level == 100:
        text = f"{mon['name']}은(는) 최고 레벨 Lv.100이에요."
    return {"xp": gained, "old_level": old_level, "new_level": mon["level"], "text": text}


def wild_move(battle):
    actor, target = battle["wild"], battle["ally"]
    options = [slot["id"] for slot in actor["moves"] if slot["pp"] > 0]
    if not options:
        return 165
    weights = []
    for mid in options:
        move = move_data(mid)
        if move["class"] != 1:
            weight = max(1, damage_value(actor, target, move))
        elif move["healing"] > 0 or move["effect"] == 38:
            weight = 30 if actor["hp"] < actor["max_hp"] / 2 else 1
        elif move["ailment"] != "none":
            weight = 20 if not target["status"] else 1
        else:
            weight = 5
        weights.append(weight)
    return random.choices(options, weights=weights)[0]


def end_battle_turn(battle):
    before_residual = battle_frame(battle)
    for actor in (battle["ally"], battle["wild"]):
        actor["flinch"] = False
        if actor["hp"] <= 0:
            continue
        status = actor["status"]
        if status not in ("burn", "poison", "toxic"):
            continue
        if status == "toxic":
            actor["toxic_turn"] += 1
            damage = max(1, actor["max_hp"] * actor["toxic_turn"] // 16)
        else:
            damage = max(1, actor["max_hp"] // (16 if status == "burn" else 8))
        actor["hp"] = max(0, actor["hp"] - damage)
        battle_log(battle, f"{actor['name']}은(는) {STATUS_LABELS[status]}으로 HP -{damage}")
    after_residual = battle_frame(battle)
    if before_residual != after_residual:
        battle.setdefault("scene_events", []).append(dict(after_residual, actor=None, target=None, kind="residual", damage=0, text="턴 종료 · 상태이상으로 체력이 변했어요."))
    battle["turn"] += 1
    profile = current()
    if battle["wild"]["hp"] <= 0:
        battle_log(battle, "야생 포켓몬을 쓰러뜨렸어요!")
        reward = award_battle_xp(battle)
        if reward:
            battle["reward"] = reward
            battle_log(battle, reward["text"])
        profile["battle_last_log"] = battle["log"]
        profile["battle_result_scene"] = json.loads(json.dumps(battle))
        profile["encounter"] = None
        profile["battle"] = None
        st.session_state.sf_message_kind = "success"
        st.session_state.sf_message = "전투 승리! " + (reward["text"] if reward else "경험치는 이미 지급됐어요.")
    elif battle["ally"]["hp"] <= 0:
        battle_log(battle, "내 포켓몬이 쓰러졌어요. 이 만남에서는 더 행동할 수 없어요.")
        st.session_state.sf_message_kind = "warning"
        st.session_state.sf_message = "내 포켓몬이 쓰러졌어요. 야생 포켓몬을 보내주고 다음 만남을 준비해 주세요."


def battle_turn(move_id):
    battle = ensure_battle()
    if not battle or min(battle["ally"]["hp"], battle["wild"]["hp"]) <= 0:
        return False
    available = [slot["id"] for slot in battle["ally"]["moves"] if slot["pp"] > 0]
    if move_id not in available and not (move_id == 165 and not available):
        return False
    begin_battle_scene(battle)
    foe_move = wild_move(battle)
    ally, wild = battle["ally"], battle["wild"]
    ally_order = (move_data(move_id)["priority"], effective_stat(ally, 6), random.random())
    wild_order = (move_data(foe_move)["priority"], effective_stat(wild, 6), random.random())
    order = [(ally, wild, move_id), (wild, ally, foe_move)] if ally_order >= wild_order else [(wild, ally, foe_move), (ally, wild, move_id)]
    for actor, target, selected in order:
        if actor["hp"] > 0 and target["hp"] > 0:
            apply_move(actor, target, selected, battle)
    end_battle_turn(battle)
    return True


def wild_counter_after_ball():
    battle = current().get("battle")
    if not battle or min(battle["ally"]["hp"], battle["wild"]["hp"]) <= 0:
        return
    begin_battle_scene(battle)
    battle_log(battle, "볼에서 나왔다! 야생 포켓몬의 반격!")
    apply_move(battle["wild"], battle["ally"], wild_move(battle), battle)
    end_battle_turn(battle)


def move_summary(mid):
    m = move_data(mid)
    effect = m["effect"]
    parts = [BATTLE_DATA["types"].get(str(m["type"]), "?"), {1: "변화", 2: "물리", 3: "특수"}[m["class"]],
             f"위력 {m['power'] or '—'}", f"명중 {m['accuracy']}%", f"PP {m['pp']}"]
    if m["priority"]:
        parts.append(f"우선도 {m['priority']:+d}")
    if m["ailment"] in STATUS_LABELS and m["ailment"]:
        chance = m["ailment_chance"] or m["chance"] or (100 if m["class"] == 1 else 0)
        parts.append(f"{STATUS_LABELS['toxic' if effect == 34 else m['ailment']]} {chance}%")
    if m["healing"]:
        parts.append(f"최대 HP {m['healing']}% 회복")
    if effect == 38:
        parts.append("HP 전부 회복 후 2회 행동 수면")
    if m["drain"]:
        parts.append(f"준 피해의 {abs(m['drain'])}% {'흡수' if m['drain'] > 0 else '반동'}")
    if effect == 102:
        parts.append("HP를 최소 1 남김")
    if effect in (41, 42, 88):
        parts.append({41: "상대 현재 HP의 절반 피해", 42: "고정 40 피해", 88: "내 레벨만큼 피해"}[effect])
    if effect == 30:
        parts.append("2~5회 연속 공격")
    if effect == 45:
        parts.append("2회 연속 공격")
    if m["flinch"]:
        parts.append(f"풀죽음 {m['flinch']}%")
    if m["changes"]:
        target = "자신" if m["target"] == 7 else "상대"
        chance = 100 if m["class"] == 1 else m["stat_chance"] or m["chance"]
        parts.append(target + " " + ", ".join(f"{STAT_LABELS.get(stat, '?')} {change:+d}" for stat, change in m["changes"]) + f"단계 ({chance}%)")
    if effect == 26:
        parts.append("모든 능력치 변화 초기화")
    if effect in (18, 79):
        parts.append("명중·회피 변화와 관계없이 명중")
    if effect == 86:
        parts.append("전투 효과 없음")
    if m["crit"]:
        parts.append("급소 확률 상승")
    return " · ".join(parts)


def home_moves_panel(mon):
    with st.expander("⚔️ 능력치 · 기술 배치"):
        actor = fighter(mon)
        st.write("타입: " + " / ".join(BATTLE_DATA["types"][str(t)] for t in actor["types"]))
        st.caption(" · ".join(f"{name} {value}" for name, value in zip(["HP", "공격", "방어", "특수공격", "특수방어", "스피드"], actor["stats"])))
        options = learned_moves(mon)
        chosen = st.multiselect("사용할 기술 · 1~4개", options, default=equipped_moves(mon),
                                format_func=lambda mid: move_data(mid)["name"],
                                key=f"moveset_{mon['uid']}_{mon['level']}")
        for mid in chosen:
            st.caption(move_data(mid)["name"] + " — " + move_summary(mid))
        if st.button("기술 배치 저장", key=f"save_moveset_{mon['uid']}"):
            if not 1 <= len(chosen) <= 4:
                st.error("기술을 1~4개 선택해 주세요.")
            else:
                mon["move_layout"] = chosen
                success("기술 배치를 저장했어요. 진행 중인 전투에는 다음 만남부터 적용돼요.")
        st.caption("최근 등록된 게임 버전의 레벨업 습득 기술 중 구현된 기술만 표시해요. 지원 기술이 없거나 PP를 모두 쓰면 발버둥을 사용해요.")


def battle_scene_html(battle, animate=True, start_delay=0):
    data = {"events": battle.get("scene_events", []) if animate else [], "delay": start_delay,
            "start": battle.get("scene_start", {}), "reward": battle.get("reward")}
    for side in ("ally", "wild"):
        actor = battle[side]
        source = next((m for m in current()["collection"] if m["uid"] == actor["uid"]), None)
        if source is None and (current().get("encounter") or {}).get("uid") == actor["uid"]:
            source = current()["encounter"]
        source = source or actor
        art = sprite(source.get("image_id", actor["number"]), source.get("shiny", False))
        data[side] = {"name": actor["name"], "level": actor["level"], "hp": actor["hp"],
                      "max_hp": actor["max_hp"], "status": STATUS_LABELS[actor["status"]],
                      "types": [BATTLE_DATA["types"][str(t)] for t in actor["types"]],
                      "image": "data:image/png;base64," + base64.b64encode(art).decode() if art else ""}
    encoded = json.dumps(data, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    template = '<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>\n*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,sans-serif;color:#eef5ff}.arena{position:relative;height:420px;overflow:hidden;border:1px solid #8ab4e040;border-radius:24px;background:radial-gradient(ellipse at 50% 90%,#3b6573 0%,#16364c 40%,#08172e 85%)}.arena:before{content:\'\';position:absolute;inset:0;background:radial-gradient(circle at 20% 20%,#ffffffaa 0 1px,transparent 2px),radial-gradient(circle at 70% 14%,#ffffff66 0 1px,transparent 2px),radial-gradient(circle at 53% 30%,#ffffff55 0 1px,transparent 2px)}.side{position:absolute;top:20px;width:43%;z-index:5}.side.ally{left:18px}.side.wild{right:18px}.side strong{font-size:clamp(14px,2.3vw,19px);display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.meta{display:flex;justify-content:space-between;color:#d4e4f7;font-size:11px;margin:6px 0}.track{height:10px;background:#0007;border:1px solid #ffffff30;border-radius:8px;overflow:hidden}.fill{height:100%;background:#70d9b1;transition:width .35s ease,color .35s}.hp{font-variant-numeric:tabular-nums;font-size:12px;color:#e3efff;margin-top:5px}.actor{position:absolute;width:clamp(120px,29vw,220px);height:220px;top:112px;display:grid;place-items:center;z-index:3;transform-origin:center bottom}.actor.ally{left:9%;--direction:1}.actor.wild{right:9%;--direction:-1}.art{height:100%;width:100%;display:grid;place-items:center;filter:drop-shadow(0 12px 7px #0007);animation:idle 2.8s ease-in-out infinite}.art img{width:100%;height:100%;object-fit:contain;image-rendering:auto}.actor.ally img{transform:scaleX(-1)}.fallback{font-size:80px}.platform{position:absolute;width:30%;height:45px;border:1px solid #acdffb50;background:radial-gradient(ellipse,#9fe6e638,transparent 70%);border-radius:50%;top:293px;z-index:1}.platform.left{left:9%}.platform.right{right:9%}.message{position:absolute;left:20px;right:20px;bottom:17px;min-height:57px;padding:12px 18px;border:1px solid #a5cfff36;border-radius:15px;background:#06182edb;font-size:clamp(13px,2.1vw,17px);text-align:center;display:grid;place-items:center;z-index:6}.tag{position:absolute;left:50%;top:164px;transform:translateX(-50%);font-size:11px;color:#d3e4f9;letter-spacing:.17em}.burst{position:absolute;width:62px;height:62px;border-radius:50%;background:radial-gradient(circle,#fff 0 12%,#ffe89b 15% 30%,#ffe49a00 65%);opacity:0;z-index:4;top:206px}.burst.left{left:calc(23% - 31px)}.burst.right{right:calc(23% - 31px)}.number{position:absolute;top:166px;opacity:0;font-size:30px;font-weight:850;text-shadow:0 3px 8px #000;color:#ffe1b1;z-index:7}.number.left{left:24%}.number.right{right:24%}.lunge{animation:lunge .52s cubic-bezier(.2,.7,.3,1)}.hurt .art{animation:hurt .5s ease-out}.support .art{animation:support .65s ease-out}.down .art{animation:down .6s forwards!important}.burst.show{animation:burst .4s ease-out}.number.show{animation:number .7s ease-out}.victory{position:absolute;left:0;right:0;top:155px;z-index:8;text-align:center;color:#ffdf93;font-weight:850;text-shadow:0 3px 10px #000;font-size:30px;pointer-events:none;opacity:0}.victory.show{animation:win .8s ease-out forwards}.victory small{display:block;font-size:15px;margin-top:9px;color:#f7edcf}@keyframes idle{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}@keyframes lunge{0%,100%{transform:translateX(0)}42%{transform:translateX(calc(var(--direction) * 68px)) translateY(-7px) scale(1.04)}64%{transform:translateX(calc(var(--direction) * 38px))}}@keyframes hurt{0%,100%{filter:brightness(1) drop-shadow(0 12px 7px #0007)}20%,60%{filter:brightness(2.5) drop-shadow(0 0 20px #ffcc75);transform:translateX(7px)}40%,80%{transform:translateX(-5px)}}@keyframes support{50%{filter:brightness(1.6) drop-shadow(0 0 22px #a7d8ff);transform:translateY(-10px)}}@keyframes down{to{transform:translateY(36px) scale(.8);opacity:.25;filter:grayscale(1)}}@keyframes burst{20%{opacity:1;transform:scale(1.3)}100%{opacity:0;transform:scale(1.7)}}@keyframes number{15%{opacity:1}100%{opacity:0;transform:translateY(-38px)}}@keyframes win{to{opacity:1;transform:translateY(-4px)}}@media(max-width:480px){.arena{height:380px;border-radius:16px}.actor{top:116px;width:37%;height:170px}.actor.ally{left:3%}.actor.wild{right:3%}.side{width:44%;top:16px}.side.ally{left:12px}.side.wild{right:12px}.platform{top:258px}.message{left:10px;right:10px;bottom:12px;padding:10px}.victory{font-size:24px;top:145px}.tag{top:150px}.burst{top:195px}@keyframes lunge{0%,100%{transform:translateX(0)}45%{transform:translateX(calc(var(--direction) * 38px)) translateY(-6px)}65%{transform:translateX(calc(var(--direction) * 20px))}}}@media(prefers-reduced-motion:reduce){.art,.lunge,.hurt .art,.support .art{animation:none!important}.number.show,.burst.show{animation-duration:.01ms}.victory.show{animation-duration:.01ms}}\n</style></head><body><section class="arena" aria-label="포켓몬 전투 장면"><div class="side ally"><strong id="allyName"></strong><div class="meta"><span id="allyTypes"></span><span id="allyStatus"></span></div><div class="track" role="progressbar" id="allyProgress"><div class="fill" id="allyBar"></div></div><div class="hp" id="allyHP"></div></div><div class="side wild"><strong id="wildName"></strong><div class="meta"><span id="wildTypes"></span><span id="wildStatus"></span></div><div class="track" role="progressbar" id="wildProgress"><div class="fill" id="wildBar"></div></div><div class="hp" id="wildHP"></div></div><div class="platform left"></div><div class="platform right"></div><div class="tag">WILD BATTLE</div><div class="actor ally" id="allyActor"><div class="art" id="allyArt"></div></div><div class="actor wild" id="wildActor"><div class="art" id="wildArt"></div></div><div class="burst left" id="allyBurst"></div><div class="burst right" id="wildBurst"></div><div class="number left" id="allyNumber"></div><div class="number right" id="wildNumber"></div><div class="victory" id="victory">VICTORY<small id="reward"></small></div><div class="message" id="message" aria-live="polite">기술을 선택하세요.</div></section><script>\nconst data=__BATTLE_SCENE_DATA__,timers=[];\nconst q=id=>document.getElementById(id),later=(delay,fn)=>timers.push(setTimeout(fn,delay));\nfor(const side of [\'ally\',\'wild\']){const mon=data[side];q(side+\'Name\').textContent=mon.name+\' · Lv.\'+mon.level;q(side+\'Types\').textContent=mon.types.join(\' / \');if(mon.image){const img=document.createElement(\'img\');img.src=mon.image;img.alt=mon.name;q(side+\'Art\').append(img)}else{const text=document.createElement(\'span\');text.className=\'fallback\';text.textContent=\'🌟\';q(side+\'Art\').append(text)}}\nfunction health(side,hp,status){const mon=data[side],bar=q(side+\'Bar\'),ratio=Math.max(0,Math.min(1,hp/mon.max_hp));bar.style.width=ratio*100+\'%\';bar.style.background=ratio>.5?\'#70d9b1\':ratio>.2?\'#f5ce6d\':\'#fa8e8e\';q(side+\'HP\').textContent=\'HP \'+Math.max(0,hp)+\' / \'+mon.max_hp;q(side+\'Status\').textContent=status||mon.status;q(side+\'Progress\').setAttribute(\'aria-valuenow\',String(hp));q(side+\'Progress\').setAttribute(\'aria-valuemin\',\'0\');q(side+\'Progress\').setAttribute(\'aria-valuemax\',String(mon.max_hp));q(side+\'Progress\').setAttribute(\'aria-label\',mon.name+\'의 체력\');if(hp<=0)q(side+\'Actor\').classList.add(\'down\')}\nfunction playClass(element,cls){if([\'lunge\',\'hurt\',\'support\'].includes(cls))element.classList.remove(\'lunge\',\'hurt\',\'support\');element.classList.remove(cls);void element.offsetWidth;element.classList.add(cls)}\nlet delay=300+(data.delay||0);\nconst events=data.events||[];\nfor(const side of [\'ally\',\'wild\'])health(side,events.length?data.start[side]:data[side].hp,events.length?data.start[side+\'_status\']:data[side].status);\nq(\'message\').textContent=events.length?\'턴 진행 중…\':\'기술이나 몬스터볼을 선택하세요.\';\nfor(const event of events){const at=delay;later(at,()=>{q(\'message\').textContent=event.text;if(event.actor){const actor=q(event.actor+\'Actor\');if(event.kind===\'attack\')playClass(actor,\'lunge\');else if(event.kind===\'status\')playClass(actor,\'support\')}});later(at+230,()=>{if(event.damage>0&&event.target){playClass(q(event.target+\'Actor\'),\'hurt\');playClass(q(event.target+\'Burst\'),\'show\');q(event.target+\'Number\').textContent=\'−\'+event.damage;playClass(q(event.target+\'Number\'),\'show\')}for(const side of [\'ally\',\'wild\'])health(side,event[side+\'_hp\'],event[side+\'_status\'])});delay+=850}\nlater(events.length?delay:0,()=>{for(const side of [\'ally\',\'wild\'])health(side,data[side].hp,data[side].status);q(\'message\').textContent=data.reward?data.reward.text:data.wild.hp<=0?\'야생 포켓몬이 쓰러졌어요.\':data.ally.hp<=0?\'내 포켓몬이 쓰러졌어요.\':\'다음 기술이나 몬스터볼을 선택하세요.\';if(data.reward){q(\'reward\').textContent=data.reward.text;playClass(q(\'victory\'),\'show\')}});\nwindow.addEventListener(\'pagehide\',()=>timers.forEach(clearTimeout));\n</script></body></html>\n'
    return template.replace("__BATTLE_SCENE_DATA__", encoded)


def render_battle_scene(battle, start_delay=0):
    scene_id = battle.get("scene_id", battle["encounter_uid"])
    animate = st.session_state.get("_sfc_battle_scene_seen") != scene_id
    st.session_state["_sfc_battle_scene_seen"] = scene_id
    components.html(battle_scene_html(battle, animate, start_delay), height=440, scrolling=False)


def render_battle_panel(scene_delay=0):
    battle = ensure_battle()
    if not battle:
        return None
    st.subheader(f"⚔️ 야생 배틀 · {battle['turn']}턴")
    render_battle_scene(battle, scene_delay)
    st.caption("홈에서 선택한 포켓몬과 기술 배치로 전투를 시작해요. 전투 중 바꾼 레벨·기술은 다음 만남부터 반영돼요.")
    if battle["ally"]["hp"] <= 0:
        st.warning("내 포켓몬이 쓰러져 기술과 볼을 사용할 수 없어요. 아래에서 야생 포켓몬을 보내주세요.")
    else:
        buttons = st.columns(2)
        active = [slot for slot in battle["ally"]["moves"] if slot["pp"] > 0]
        slots = battle["ally"]["moves"] if active else [{"id": 165, "pp": 1}]
        for i, slot in enumerate(slots):
            mid = slot["id"]
            move = move_data(mid)
            multiplier = type_multiplier(move["type"], battle["wild"]["types"])
            with buttons[i % 2]:
                if st.button(f"{move['name']} · PP {slot['pp']}" + (f" · 상성 ×{multiplier:g}" if move["class"] != 1 else ""),
                             key=f"battle_{battle['encounter_uid']}_{battle['turn']}_{mid}", disabled=slot["pp"] <= 0,
                             use_container_width=True):
                    if action_ready() and battle_turn(mid):
                        cloud_save()
                        st.rerun()
                st.caption(move_summary(mid))
    with st.expander("📜 전투 기록", expanded=True):
        for text in battle["log"][-8:]:
            st.write(text)
    with st.expander("전투 · 포획 규칙"):
        st.write("체력을 깎을수록 포획 보너스가 최대 약 3배, 수면·얼음은 2.5배, 마비·독·맹독·화상은 1.5배예요. 일반 볼의 최종 포획 확률 상한은 95%, 마스터볼은 100%예요. 야생 포켓몬이 쓰러지면 포획할 수 없어요.")
        st.caption("야생 포켓몬을 쓰러뜨리면 전투 참여 포켓몬이 경험치를 받아요. 종별 기본 경험치 × 야생 레벨 ÷ 7을 내림한 값을 사용하고, Lv.100까지 필요한 경험치까지만 반영해요. 같은 만남은 1회만 지급해요.")
        st.caption("볼을 던져 실패하면 야생 포켓몬이 반격하고 턴 종료 효과가 적용돼요. 포켓몬은 새 만남마다 회복되며 진행 중 HP·PP·상태는 저장돼요.")
        st.caption("PokeAPI의 종족값·타입·기술 수치 기반, 개체값 15·노력치 0·성격 보정 없음. 물리/특수, 자속 1.5배, 18타입 복합 상성, 명중, 우선도, 급소와 지원 기술의 추가 효과를 반영해요. 특성·도구·날씨·필드·변신 등은 미구현이며 원작 전투의 완전한 재현은 아니에요.")
    return battle


def catch_probability(mon, ball):
    bonus = 1.0
    battle = current().get("battle")
    if battle and battle.get("encounter_uid") == mon["uid"]:
        wild = battle["wild"]
        if wild["hp"] <= 0 or battle["ally"]["hp"] <= 0:
            return 0.0
        bonus = (3 * wild["max_hp"] - 2 * wild["hp"]) / wild["max_hp"]
        bonus *= 2.5 if wild["status"] in ("sleep", "freeze") else 1.5 if wild["status"] else 1
    if ball == "마스터볼":
        return 1.0
    base = {"일반": .78, "희귀": .52, "초희귀": .30, "전설": .10, "환상": .06}.get(mon["rarity"], .5)
    return min(.95, max(.01, base * BALLS[ball]["power"] * bonus / (1 + (mon["level"] - 1) * .025)))


def sale_price(mon):
    return int(SALE_BASE.get(mon["rarity"], 10) * (1 + (mon["level"] - 1) * .10) * (2 if mon.get("shiny") else 1))


def sleep_coin_reward(score):
    try:
        score = float(score)
    except (ValueError, TypeError):
        return 0
    if not math.isfinite(score) or not 0 <= score <= 100:
        return 0
    return 25 if score < 40 else 50 if score < 60 else 100 if score < 80 else 175 if score < 90 else 250


def reward_sleep(value):
    coins = sleep_coin_reward(value.get("quality"))
    if not coins:
        return 0
    try:
        day = parse_dt(value["end"]).date().isoformat()
    except (ValueError, TypeError, KeyError, OverflowError):
        return 0
    if day > now().date().isoformat() or day in wallet()["reward_days"]:
        return 0
    wallet()["reward_days"][day] = coins
    wallet()["coins"] += coins
    return coins


def refresh_login_if_needed():
    auth = st.session_state.get("_sfc_auth")
    if not auth:
        return
    try:
        expires_at = float(auth.get("expires_at", 0))
    except (TypeError, ValueError):
        return
    if not expires_at or expires_at > time.time() + 60:
        return
    try:
        refreshed = cloud_request(
            "POST", "/auth/v1/token?grant_type=refresh_token",
            authenticated=False, json={"refresh_token": auth["refresh_token"]},
        )
        if not (refreshed or {}).get("access_token"):
            raise SaveConnectionError("로그인 갱신에 실패했어요.")
        st.session_state["_sfc_auth"] = refreshed
    except (SaveConnectionError, KeyError) as error:
        st.warning("로그인 연결을 갱신하지 못했어요. 기록은 유지하고 있어요. " + str(error))
        if st.button("연결 다시 확인", key="refresh_auth_retry"):
            st.rerun()
        st.stop()


def cloud_login_gate():
    try:
        config = cloud_config()
    except SaveConnectionError as error:
        st.error(str(error))
        st.stop()

    if not config:
        st.title("🌙 Sleep Free 연결 설정")
        st.info(
            "Streamlit Secrets에 SUPABASE_URL과 "
            "SUPABASE_KEY를 입력해 주세요."
        )
        st.stop()

    refresh_login_if_needed()
    remember_session()

    if not st.session_state.get("_sfc_auth"):
        st.title("🌙 Sleep Free")
        st.caption(
            "회원가입 후 각자의 계정으로 "
            "포켓몬과 수면 기록을 저장해요."
        )

        if st.session_state.get("sf_profiles"):
            st.download_button(
                "로그인 전 기존 접속 기록 백업",
                json.dumps(
                    {
                        "version": "sleep-free-pokemon-3",
                        "profiles": st.session_state.sf_profiles,
                    },
                    ensure_ascii=False,
                ),
                file_name="sleep_free_before_login.json",
                mime="application/json",
            )

        login_tab, signup_tab = st.tabs(
            ["로그인", "회원가입"]
        )

        with login_tab:
            with st.form("_sfc_login_form"):
                email = st.text_input(
                    "이메일", key="_sfc_login_email"
                )
                password = st.text_input(
                    "비밀번호",
                    type="password",
                    key="_sfc_login_password",
                )
                submitted = st.form_submit_button(
                    "로그인",
                    use_container_width=True,
                )

            if submitted:
                if not email.strip() or not password:
                    st.error("이메일과 비밀번호를 입력해 주세요.")
                else:
                    try:
                        auth = cloud_request(
                            "POST",
                            "/auth/v1/token?grant_type=password",
                            authenticated=False,
                            json={
                                "email": email.strip(),
                                "password": password,
                            },
                        )

                        if (
                            not isinstance(auth, dict)
                            or not auth.get("access_token")
                            or not (auth.get("user") or {}).get("id")
                        ):
                            raise SaveConnectionError(
                                "로그인 결과를 확인할 수 없어요."
                            )

                        st.session_state["_sfc_auth"] = auth
                        st.session_state["_sfc_loaded"] = False
                        st.rerun()

                    except SaveConnectionError as error:
                        st.error(str(error))
                        st.caption(
                            "가입할 때 정한 비밀번호를 사용해 주세요. "
                            "이메일 인증이 필요한 계정은 "
                            "인증을 먼저 완료해 주세요."
                        )

        with signup_tab:
            with st.form("_sfc_signup_form"):
                signup_email = st.text_input(
                    "이메일", key="_sfc_signup_email"
                )
                signup_password = st.text_input(
                    "비밀번호",
                    type="password",
                    key="_sfc_signup_password",
                    help="6자 이상으로 입력해 주세요.",
                )
                signup_confirm = st.text_input(
                    "비밀번호 확인",
                    type="password",
                    key="_sfc_signup_confirm",
                )
                signup_submitted = st.form_submit_button(
                    "회원가입",
                    use_container_width=True,
                )

            if signup_submitted:
                clean_email = signup_email.strip()

                if (
                    not clean_email
                    or "@" not in clean_email
                    or not clean_email.rsplit("@", 1)[-1]
                ):
                    st.error("올바른 이메일을 입력해 주세요.")

                elif len(signup_password) < 6:
                    st.error("비밀번호는 6자 이상 입력해 주세요.")

                elif signup_password != signup_confirm:
                    st.error("비밀번호가 서로 달라요.")

                else:
                    try:
                        result = cloud_request(
                            "POST",
                            "/auth/v1/signup",
                            authenticated=False,
                            json={
                                "email": clean_email,
                                "password": signup_password,
                            },
                        )

                        if not isinstance(result, dict):
                            raise SaveConnectionError(
                                "회원가입 결과를 확인할 수 없어요."
                            )

                        if (
                            result.get("access_token")
                            and (result.get("user") or {}).get("id")
                        ):
                            st.session_state["_sfc_auth"] = result
                            st.session_state["_sfc_loaded"] = False
                            st.rerun()

                        else:
                            st.success(
                                "회원가입 요청을 처리했어요. "
                                "이메일로 인증 안내가 왔는지 확인하고, "
                                "인증 후 로그인 탭에서 로그인해 주세요."
                            )
                            st.caption(
                                "이미 가입한 이메일이라면 로그인해 주세요. "
                                "메일이 없으면 스팸함도 확인해 주세요."
                            )

                    except SaveConnectionError as error:
                        st.error(
                            "회원가입을 완료하지 못했어요. "
                            + str(error)
                        )

        st.stop()

    if st.session_state.get("_sfc_loaded"):
        return

    try:
        user_id = (
            st.session_state["_sfc_auth"]["user"]["id"]
        )

        rows = cloud_request(
            "GET",
            "/rest/v1/sleep_free_saves",
            params={
                "user_id": "eq." + user_id,
                "select": "save_data,updated_at",
            },
        )

        if rows:
            payload = rows[0]["save_data"]

            if (
                not isinstance(payload, dict)
                or not isinstance(
                    payload.get("profiles"), dict
                )
                or not payload["profiles"]
            ):
                raise SaveConnectionError(
                    "서버 자료 형식이 올바르지 않아 "
                    "덮어쓰지 않고 중단했어요."
                )

            if len(payload["profiles"]) > 20:
                raise SaveConnectionError(
                    "프로필 개수를 확인해 주세요."
                )

            restored = {}

            for name, source in payload["profiles"].items():
                if (
                    not isinstance(name, str)
                    or not isinstance(source, dict)
                ):
                    raise SaveConnectionError(
                        "프로필 형식을 확인해 주세요."
                    )

                for kind in (
                    "collection", "records", "cycles",
                    "naps", "day_checks",
                ):
                    if (
                        not isinstance(
                            source.get(kind, []), list
                        )
                        or len(source.get(kind, [])) > 5000
                    ):
                        raise SaveConnectionError(
                            "기록 형식을 확인해 주세요."
                        )

                restored[name] = migrate(source)

            st.session_state.sf_profiles = restored
            selected = payload.get("active_profile")

            st.session_state.sf_user = (
                selected
                if selected in restored
                else next(iter(restored))
            )

            st.session_state["_sfc_updated_at"] = (
                rows[0]["updated_at"]
            )
            st.session_state["_sfc_hash"] = (
                cloud_fingerprint(payload)
            )

        else:
            st.session_state.sf_profiles = {
                "내 기록": fresh_profile()
            }
            st.session_state.sf_user = "내 기록"
            st.session_state["_sfc_updated_at"] = None
            st.session_state["_sfc_hash"] = None

        st.session_state["_sfc_wallet"] = payload.get("wallet", {}) if rows else {}
        w = st.session_state["_sfc_wallet"]
        if not isinstance(w, dict):
            raise ValueError("코인 자료를 확인해 주세요.")
        w.setdefault("coins", 100)
        w.setdefault("balls", {})
        for ball_name in BALLS:
            w["balls"].setdefault(ball_name, 0)
        w.setdefault("codes", [])
        w.setdefault("sold_uids", [])
        w.setdefault("reward_days", {})
        st.session_state.sf_page = payload.get("page", "home") if rows else "home"
        st.session_state.sf_drawn = None
        st.session_state.sf_message = ""
        st.session_state["_sfc_loaded"] = True

    except (
        SaveConnectionError,
        KeyError,
        ValueError,
        TypeError,
    ) as error:
        st.error(
            "기록 불러오기에 실패했어요. " + str(error)
        )

        if st.button(
            "다시 불러오기",
            key="_sfc_reload",
        ):
            st.rerun()

        if st.button(
            "로그인 화면으로",
            key="_sfc_back_to_login",
        ):
            st.session_state.pop("_sfc_auth", None)
            st.rerun()

        st.stop()


def cloud_logout():
    cloud_save()

    try:
        cloud_request(
            "POST",
            "/auth/v1/logout?scope=local",
        )
    except SaveConnectionError:
        pass

    for key in list(st.session_state):
        if key.startswith(("sf_", "_sfc_")):
            del st.session_state[key]

    st.session_state["_sfc_clear_browser"] = True
    st.rerun()


cloud_login_gate()
if st.session_state.get("_sfc_pending_save"):
    cloud_save()

if (
    "sf_profiles" not in st.session_state
    or not isinstance(
        st.session_state.sf_profiles, dict
    )
    or not st.session_state.sf_profiles
):
    st.session_state.sf_profiles = {
        "트레이너": fresh_profile()
    }

for username in list(st.session_state.sf_profiles):
    st.session_state.sf_profiles[username] = migrate(
        st.session_state.sf_profiles[username]
    )

if (
    st.session_state.get("sf_user")
    not in st.session_state.sf_profiles
):
    st.session_state.sf_user = next(
        iter(st.session_state.sf_profiles)
    )

st.session_state.setdefault("sf_page", "home")
st.session_state.setdefault("sf_drawn", None)
st.session_state.setdefault("sf_message", "")


def current():
    return st.session_state.sf_profiles[
        st.session_state.sf_user
    ]


def select_partner(mon_uid):
    profile = current()
    if not any(mon["uid"] == mon_uid for mon in profile["collection"]):
        return False
    profile["partner_uid"] = mon_uid
    profile["home_selected_uid"] = mon_uid
    # Apply to the widget before it is created on the NEXT run. Mutating an
    # already-created Streamlit widget here would raise an API exception.
    st.session_state["_sfc_pending_home_choice"] = {
        "profile": st.session_state.sf_user, "uid": mon_uid,
    }
    return True


def partner():
    p = current()
    return next(
        (
            mon for mon in p["collection"]
            if mon["uid"] == p["partner_uid"]
        ),
        p["collection"][0],
    )


def goto(page):
    st.session_state.sf_page = page
    cloud_save()
    st.rerun()


def success(message):
    cloud_save()
    st.session_state.sf_message = message
    st.rerun()


# =====================================
# 이미지·뽑기
# =====================================

@st.cache_data(ttl=86400, show_spinner=False)
def sprite(number, shiny):
    base = (
        "https://raw.githubusercontent.com/"
        "PokeAPI/sprites/master/sprites/pokemon"
    )

    if shiny:
        urls = [
            f"{base}/other/official-artwork/shiny/{number}.png",
            f"{base}/shiny/{number}.png",
        ]
    else:
        urls = [
            f"{base}/other/official-artwork/{number}.png",
            f"{base}/{number}.png",
        ]

    for url in urls:
        try:
            response = requests.get(url, timeout=5)

            if (
                response.ok
                and response.headers.get(
                    "Content-Type", ""
                ).startswith("image/")
                and len(response.content) < 5_000_000
            ):
                return response.content

        except requests.RequestException:
            continue

    return None


def show_pokemon(mon, width=180):
    if mon["shiny"]:
        st.caption("✨ 이로치")

    image = sprite(
        mon.get("image_id", mon["number"]),
        mon["shiny"],
    )

    if image:
        st.image(image, width=width)
    else:
        st.write("🌙", mon["name"])
        st.caption("이미지를 불러오지 못했어요.")


def capture_scene_html(result):
    mon = result["mon"]
    art = sprite(mon.get("image_id", mon["number"]), mon.get("shiny", False))
    data = {
        "mode": result.get("mode", "capture"),
        "shiny": bool(mon.get("shiny", False)),
        "area": result.get("area", "meadow"),
        "name": mon["name"], "level": mon["level"],
        "rarity": mon["rarity"], "caught": bool(result["caught"]),
        "ball": result.get("ball", mon.get("ball", "몬스터볼")),
        "shakes": 3 if result["caught"] else max(1, min(3, int(result.get("shakes", 1)))),
        "image": "data:image/png;base64," + base64.b64encode(art).decode() if art else "",
    }
    # Escape HTML delimiters before embedding JSON into an inline script.
    encoded = json.dumps(data, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    template = '<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>\n*{box-sizing:border-box}body{margin:0;color:#f8faff;font-family:system-ui,-apple-system,sans-serif}.scene{position:relative;height:470px;overflow:hidden;border:1px solid #ffffff24;border-radius:28px;background:radial-gradient(ellipse at 50% 60%,#324970 0%,#10223d 50%,#071326 100%);isolation:isolate}.scene:before{content:\'\';position:absolute;inset:0;background:radial-gradient(circle at 12% 22%,#fff8 0 1px,transparent 2px),radial-gradient(circle at 85% 31%,#fff7 0 1px,transparent 2px),radial-gradient(circle at 72% 12%,#fff9 0 1px,transparent 2px),radial-gradient(circle at 28% 40%,#fff6 0 1px,transparent 2px)}.controls{position:absolute;right:16px;top:16px;display:flex;gap:8px;z-index:8}button{border:1px solid #fff4;background:#152740;color:white;border-radius:30px;padding:8px 14px;font-size:13px;cursor:pointer}button:hover{background:#2b4260}button:focus-visible{outline:3px solid #f9d973;outline-offset:3px}.hint{position:absolute;top:24px;left:24px;font-size:11px;letter-spacing:.22em;color:#b4c4df}.ring{position:absolute;width:240px;height:54px;border:1px solid #89afdb66;border-radius:50%;left:calc(50% - 120px);top:304px;background:#72a5dd0d;box-shadow:0 0 35px #7cafff14}.creature{position:absolute;top:56px;left:calc(50% - 100px);width:200px;height:200px;display:grid;place-items:center;filter:drop-shadow(0 10px 20px #0006);transform-origin:50% 85%;z-index:3}.creature img{width:100%;height:100%;object-fit:contain}.fallback{font-size:88px}.ball-wrap{position:absolute;top:229px;left:calc(50% - 42px);width:84px;height:84px;z-index:4;transform-origin:50% 90%}.ball{position:absolute;inset:0;border:5px solid #172033;border-radius:50%;background:linear-gradient(to bottom,var(--ball,#ed4453) 0 45%,#172033 45% 55%,#f5f7ff 55% 100%);box-shadow:inset 7px 8px 12px #ffffff5c,inset -8px -9px 14px #0003,0 12px 16px #0005}.ball:after{content:\'\';position:absolute;left:calc(50% - 14px);top:calc(50% - 14px);width:28px;height:28px;background:#edf2fa;border:5px solid #172033;border-radius:50%;box-shadow:inset 0 0 0 2px #c3ccda}.ball.bright:after{background:#ffdc76;box-shadow:0 0 24px #ffd86f}.ball.super:before,.ball.hyper:before,.ball.master:before{content:\'\';position:absolute;left:14px;right:14px;height:14px;top:7px;background:var(--stripe,#e74757);border-radius:15px 15px 4px 4px;transform:rotate(-7deg)}.ball.master:before{content:\'M\';color:white;background:transparent;text-align:center;font-size:17px;font-weight:900;top:0}.label{position:absolute;bottom:33px;text-align:center;left:15px;right:15px;z-index:6}.label h2{margin:0 0 9px;font-size:clamp(24px,4vw,38px);letter-spacing:-.05em}.label p{margin:0;color:#c6d5ed;font-size:14px}.dots{position:absolute;top:330px;left:0;right:0;display:flex;gap:8px;justify-content:center}.dots i{width:7px;height:7px;background:#d5e1f42b;border-radius:50%;transition:background .12s,box-shadow .12s}.dots i.on{background:#ffe6a4;box-shadow:0 0 12px #ffd15e}.flash{position:absolute;inset:0;background:#fff2c5;opacity:0;z-index:5;pointer-events:none}.halo{position:absolute;inset:20px;background:radial-gradient(circle at 50% 52%,#ffd97950,transparent 55%);opacity:0;pointer-events:none}.star{position:absolute;color:#ffe99e;font-size:42px;opacity:0;left:50%;top:264px;z-index:5;filter:drop-shadow(0 0 8px #ffdb69)}.s1{--x:-115px;--y:-105px;--r:-20deg}.s2{--x:85px;--y:-126px;--r:12deg}.s3{--x:-20px;--y:-165px;--r:5deg}.particle{position:absolute;left:50%;top:270px;width:6px;height:12px;border-radius:2px;opacity:0;background:var(--color);z-index:5}.anim-in{animation:absorb .62s ease-in forwards}.anim-shake{animation:shake .48s ease-in-out}.anim-drop{animation:drop .48s cubic-bezier(.3,.8,.6,1) forwards}.won .ball-wrap{animation:land .5s ease-out}.won .halo{opacity:1;transition:opacity .6s}.won .star{animation:star 1.4s ease-out forwards}.won .s2{animation-delay:.08s}.won .s3{animation-delay:.16s}.won .flash,.lost .flash{animation:flash .55s ease-out}.won .label h2{color:#ffe49a;animation:title .48s ease-out}.won .particle{animation:confetti 1.6s ease-out forwards;animation-delay:var(--delay)}.lost .ball-wrap{animation:open .35s forwards}.lost .creature{animation:escape .65s cubic-bezier(.2,.8,.4,1) forwards}.lost .label h2{color:#ffcfb5}.won .dots,.lost .dots{opacity:0}.replay{position:absolute;left:16px;bottom:16px;z-index:8;padding:6px 10px;font-size:11px;opacity:.7}\n@keyframes absorb{0%{transform:translateY(0) scale(1);filter:drop-shadow(0 0 10px #fff)}40%{opacity:1;filter:brightness(2) drop-shadow(0 0 20px #fff)}100%{transform:translateY(140px) scale(0);opacity:0;filter:brightness(3)}}@keyframes drop{0%{transform:translateY(-55px) scale(.65);opacity:0}65%{transform:translateY(6px) scale(1);opacity:1}100%{transform:translateY(0) scale(1);opacity:1}}@keyframes shake{0%,100%{transform:translateX(0) rotate(0)}25%{transform:translateX(-10px) rotate(-18deg)}65%{transform:translateX(9px) rotate(16deg)}}@keyframes land{0%{transform:scale(1.15)}45%{transform:scale(.94)}100%{transform:scale(1)}}@keyframes star{0%{opacity:0;transform:translate(-50%,0) scale(.1)}25%{opacity:1}65%,100%{opacity:1;transform:translate(var(--x),var(--y)) rotate(var(--r)) scale(1)}}@keyframes flash{0%{opacity:.8}100%{opacity:0}}@keyframes title{0%{transform:translateY(14px) scale(.9);opacity:0}100%{transform:translateY(0) scale(1);opacity:1}}@keyframes confetti{0%{opacity:1;transform:translate(0,0) rotate(0)}100%{opacity:0;transform:translate(var(--x),var(--y)) rotate(var(--r))}}@keyframes open{100%{transform:translateY(12px) scale(1.4);opacity:0}}@keyframes escape{0%{transform:translateY(125px) scale(0);opacity:0}65%{transform:translateY(-12px) scale(1.1);opacity:1}100%{transform:translateY(0) scale(1);opacity:1}}@media(prefers-reduced-motion:reduce){*{animation-duration:.01ms!important}.particle{display:none}.scene .star{animation-duration:.01ms!important}}@media(max-width:480px){.hint{top:65px;left:18px}.scene{border-radius:18px}.replay{bottom:8px;left:auto;right:12px}}\n.shiny-reveal .creature{animation:shinyFloat 2.5s ease-in-out infinite}.shiny-reveal .ball-wrap,.shiny-reveal .dots{display:none}.shiny-reveal .halo{opacity:1;background:radial-gradient(circle at 50% 45%,#e4c5ff80,transparent 60%)}.shiny-reveal .star{animation:star 1.4s ease-out forwards;color:#efdbff}.shiny-reveal .flash{animation:flash .7s ease-out}.shiny-reveal .label h2{color:#f1d8ff}.shiny-reveal .ring{border-color:#ebc7ff}.shiny-reveal .particle{animation:confetti 2s ease-out forwards;animation-delay:var(--delay)}@keyframes shinyFloat{0%,100%{transform:translateY(-8px);filter:drop-shadow(0 0 18px #b6a2ff)}50%{transform:translateY(2px);filter:drop-shadow(0 0 32px #e4c3ff)}}@media(prefers-reduced-motion:reduce){.shiny-reveal .creature{animation:none}}\n.arrival .ball-wrap,.arrival .dots{display:none}.arrival .creature{opacity:0;transform:translateY(35px) scale(.6);filter:brightness(0) blur(12px)}.arrival .ring{animation:searchRing 1.4s ease-in-out infinite}.appeared .creature{animation:appear 1.15s cubic-bezier(.1,.8,.3,1) forwards}.appeared .ring{animation:none}.appeared .halo{opacity:.7;background:radial-gradient(circle at 50% 45%,var(--area-glow,#83ddb3),transparent 55%)}@keyframes appear{0%{opacity:0;transform:translateY(38px) scale(.6);filter:brightness(0) blur(12px)}40%{opacity:1;filter:brightness(.2) blur(2px)}100%{opacity:1;transform:translateY(0) scale(1);filter:brightness(1) drop-shadow(0 0 16px #c7f7ff55)}}@keyframes searchRing{0%,100%{transform:scale(.8);opacity:.3}50%{transform:scale(1.15);opacity:1}}@media(prefers-reduced-motion:reduce){.arrival .ring{animation:none}}\n.controls{align-items:center;background:#0c1c31dd;border:1px solid #ffffff26;border-radius:22px;padding:5px;gap:10px}.controls button{padding:6px 11px}.volume-label{display:flex;align-items:center;gap:7px;padding-right:9px;color:#e1eaff;font-size:12px}.volume-label input{width:85px;accent-color:#ffe29a}.volume-label output{width:30px;font-variant-numeric:tabular-nums}@media(max-width:480px){.controls{right:10px;top:10px}.volume-label input{width:68px}.volume-label{font-size:11px;gap:5px}.hint{top:65px}}\n</style></head><body><section class="scene" id="scene" aria-label="포획 결과 연출"><div class="hint">SLEEP FREE · CAPTURE</div><div class="controls"><button id="audio" type="button" aria-label="무음 전환">🔊 유음</button><label class="volume-label" for="volume">음량 <input id="volume" type="range" min="0" max="100" step="1" value="35" aria-label="효과음 음량"><output id="volumeValue" for="volume">35%</output></label></div><div class="halo"></div><div class="ring"></div><div class="creature" id="creature"></div><div class="ball-wrap" id="ballWrap"><div class="ball" id="ball"></div></div><div class="flash"></div><div class="star s1">✦</div><div class="star s2">✦</div><div class="star s3">✦</div><div class="dots"><i></i><i></i><i></i></div><div class="label" aria-live="polite"><h2 id="title">들어갔다…!</h2><p id="subtitle">볼 안에서 움직이고 있어요.</p></div><button class="replay" id="replay" type="button">↻ 연출 다시 보기</button></section><script>\nconst data = __CAPTURE_DATA__;\nconst scene=document.getElementById(\'scene\'), creature=document.getElementById(\'creature\'), wrap=document.getElementById(\'ballWrap\'), ball=document.getElementById(\'ball\'), title=document.getElementById(\'title\'), subtitle=document.getElementById(\'subtitle\'), audioBtn=document.getElementById(\'audio\');\nif(data.image){const img=document.createElement(\'img\');img.src=data.image;img.alt=data.name;creature.append(img)}else{const fallback=document.createElement(\'span\');fallback.className=\'fallback\';fallback.textContent=\'🌟\';creature.append(fallback)}\nconst palette={\'몬스터볼\':[\'#ed4453\',\'normal\',\'#fff\'],\'슈퍼볼\':[\'#4285df\',\'super\',\'#ed4453\'],\'하이퍼볼\':[\'#293141\',\'hyper\',\'#ffce55\'],\'마스터볼\':[\'#8856bd\',\'master\',\'#f2b5e7\']};\nconst theme=palette[data.ball]||palette[\'몬스터볼\'];ball.style.setProperty(\'--ball\',theme[0]);ball.style.setProperty(\'--stripe\',theme[2]);ball.classList.add(theme[1]);\nfor(let i=0;i<24;i++){const p=document.createElement(\'b\');p.className=\'particle\';const a=Math.PI*2*i/24;const r=100+(i%5)*30;p.style.setProperty(\'--x\',`${Math.cos(a)*r}px`);p.style.setProperty(\'--y\',`${Math.sin(a)*r-40}px`);p.style.setProperty(\'--r\',`${i*63}deg`);p.style.setProperty(\'--delay\',`${(i%4)*.04}s`);p.style.setProperty(\'--color\',[\'#ffe29a\',\'#91e6d5\',\'#acd0ff\',\'#efb7fa\'][i%4]);scene.append(p)}\nlet ctx=null,master=null,sharedAudio=false,muted=false,volume=.35,timers=[],started=0,finished=false,hasStarted=false;\nconst volumeInput=document.getElementById(\'volume\'),volumeValue=document.getElementById(\'volumeValue\'),ownedOscillators=new Set();\ntry{muted=localStorage.getItem(\'sf-capture-muted\')===\'1\';const saved=localStorage.getItem(\'sf-capture-volume\');if(saved!==null&&Number.isFinite(Number(saved)))volume=Math.max(0,Math.min(1,Number(saved)))}catch(_){}\nfunction applyVolume(){if(master&&ctx){try{master.gain.setValueAtTime(muted?0:volume,ctx.currentTime)}catch(_){}}}\nfunction audioContext(){\n if(ctx&&ctx.state!==\'closed\')return ctx;\n // Reuse the audio context on the same-origin app page across scene iframes.\n // Never inspect the parent DOM or authentication data.\n let host=window;\n try{if(window.parent&&window.parent!==window){void window.parent.location.href;host=window.parent}}catch(_){}\n try{\n  let engine=host.__sleepFreeAudioV2;\n  if(!engine||engine.ctx.state===\'closed\'){\n   const C=host.AudioContext||host.webkitAudioContext||window.AudioContext||window.webkitAudioContext;\n   if(!C)return null;const ac=new C(),gain=ac.createGain();gain.connect(ac.destination);\n   engine={ctx:ac,master:gain};host.__sleepFreeAudioV2=engine;\n  }\n  ctx=engine.ctx;master=engine.master;sharedAudio=host!==window;applyVolume();return ctx;\n }catch(_){return null}\n}\nfunction soundButton(){\n const silent=muted||volume===0;audioBtn.textContent=silent?\'🔇 무음\':\'🔊 유음\';\n audioBtn.setAttribute(\'aria-pressed\',String(silent));\n audioBtn.title=silent?\'눌러서 소리 켜기\':\'눌러서 무음 전환\';\n volumeInput.value=String(Math.round(volume*100));volumeValue.textContent=Math.round(volume*100)+\'%\';\n}\nfunction tone(freq,delay,length=.12,volume=.07,type=\'sine\',end=null){try{if(muted||!ctx||ctx.state!==\'running\')return;const t=ctx.currentTime+delay,o=ctx.createOscillator(),g=ctx.createGain();o.type=type;o.frequency.setValueAtTime(freq,t);if(end)o.frequency.exponentialRampToValueAtTime(end,t+length);g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(volume,t+.012);g.gain.exponentialRampToValueAtTime(.001,t+length);o.connect(g);g.connect(master);ownedOscillators.add(o);o.start(t);o.onended=()=>{ownedOscillators.delete(o);try{o.disconnect();g.disconnect()}catch(_){}};o.stop(t+length+.02)}catch(_){soundButton()}}\nfunction jingle(){if(data.mode===\'encounter\'){if(data.shiny)[880,1174.66,1396.91,1760,2093].forEach((f,i)=>tone(f,i*.10,.30,.045,\'sine\'));else{tone(523,0,.2,.04);tone(659,.12,.25,.04)}return}if(data.caught){[523.25,659.25,783.99,1046.5].forEach((f,i)=>tone(f,i*.115,i===3?.48:.18,.065,\'triangle\'));tone(261.63,0,.5,.035)}else{tone(392,0,.25,.07,\'triangle\',196);tone(220,.2,.25,.035,\'sine\',165)}}\nfunction later(ms,fn){timers.push(setTimeout(fn,ms))}\nfunction launch(){timers.forEach(clearTimeout);timers=[];started=performance.now();finished=false;hasStarted=true;scene.classList.remove(\'won\',\'lost\',\'shiny-reveal\',\'arrival\',\'appeared\');creature.classList.remove(\'anim-in\');wrap.classList.remove(\'anim-shake\',\'anim-drop\');ball.classList.remove(\'bright\');document.querySelectorAll(\'.dots i\').forEach(x=>x.classList.remove(\'on\'));title.textContent=\'들어갔다…!\';subtitle.textContent=`${data.ball}이 포켓몬을 감쌌어요.`;if(data.mode===\'encounter\'){\n const areaNames={meadow:\'산들바람 초원\',forest:\'달빛 숲\',ruins:\'별빛 유적\',sanctuary:\'천상의 성역\'};\n const colors={meadow:\'#83ddb350\',forest:\'#b7aeff50\',ruins:\'#88d8ff50\',sanctuary:\'#ffd68b50\'};\n scene.style.setProperty(\'--area-glow\',colors[data.area]||colors.meadow);\n scene.classList.add(\'arrival\');title.textContent=\'무언가 다가온다…\';subtitle.textContent=areaNames[data.area]||areaNames.meadow;\n document.querySelector(\'.hint\').textContent=\'SLEEP FREE · EXPLORE\';\n tone(220,0,.5,.025,\'sine\',440);\n later(650,()=>{scene.classList.add(\'appeared\');title.textContent=\'풀숲이 흔들린다…\';tone(440,0,.4,.035,\'sine\',880)});\n later(1800,()=>{finished=true;title.textContent=data.shiny?\'✨ 이로치 발견!\':`야생 ${data.name} 등장!`;subtitle.textContent=`${data.name} · Lv.${data.level} · ${data.rarity}`;\n  if(data.shiny){scene.classList.remove(\'appeared\',\'arrival\');scene.classList.add(\'shiny-reveal\');jingle()}else{tone(523,0,.2,.04);tone(659,.12,.25,.04)}});return} wrap.style.opacity=\'0\';void scene.offsetWidth;creature.classList.add(\'anim-in\');tone(700,0,.45,.035,\'sine\',250);\n later(420,()=>{wrap.style.opacity=\'1\';wrap.classList.add(\'anim-drop\')});\n [1050,1950,2850].slice(0,data.shakes).forEach((ms,index)=>later(ms,()=>{wrap.classList.remove(\'anim-drop\',\'anim-shake\');void wrap.offsetWidth;wrap.classList.add(\'anim-shake\');document.querySelectorAll(\'.dots i\')[index].classList.add(\'on\');title.textContent=[\'한 번…\',\'두 번…\',\'세 번…!\'][index];subtitle.textContent=\'조금만 더…\';tone(170,0,.12,.065,\'sine\',100);tone(300,.11,.065,.025)}));\n later(1050 + (data.shakes - 1) * 900 + 970,()=>{finished=true;wrap.classList.remove(\'anim-shake\');scene.classList.add(data.caught?\'won\':\'lost\');if(data.caught){ball.classList.add(\'bright\');title.textContent=`잡았다! ${data.name}!`;subtitle.textContent=`Lv.${data.level} · ${data.rarity} · 보관함에 들어왔어요.`}else{title.textContent=\'앗! 볼에서 튀어나왔다!\';subtitle.textContent=`${data.name}에게 다른 볼로 다시 도전해 보세요.`}jingle()});}\nfunction saveSettings(){try{localStorage.setItem(\'sf-capture-muted\',muted?\'1\':\'0\');localStorage.setItem(\'sf-capture-volume\',String(volume))}catch(_){}applyVolume();soundButton()}\nfunction resumeAudio(){try{const ac=audioContext();if(ac&&ac.state!==\'running\'&&!muted&&volume>0){const promise=ac.resume();if(promise&&promise.catch)promise.catch(()=>{})}}catch(_){}}\naudioBtn.addEventListener(\'click\',()=>{\n muted=!(muted||volume===0);if(!muted&&volume===0)volume=.35;\n saveSettings();resumeAudio();\n});\nvolumeInput.addEventListener(\'input\',()=>{\n const value=Number(volumeInput.value);if(!Number.isFinite(value))return;\n volume=Math.max(0,Math.min(1,value/100));muted=volume===0;\n saveSettings();resumeAudio();\n});\ndocument.getElementById(\'replay\').addEventListener(\'click\',()=>{resumeAudio();launch()});\nsoundButton();try{audioContext();resumeAudio()}catch(_){}\n// Visuals always begin immediately; blocked audio never interrupts gameplay.\nlaunch();\nwindow.addEventListener(\'pagehide\',()=>{\n timers.forEach(clearTimeout);\n ownedOscillators.forEach(o=>{try{o.stop()}catch(_){}});ownedOscillators.clear();\n if(ctx&&!sharedAudio){try{ctx.close().catch(()=>{})}catch(_){}}\n});\n</script></body></html>\n'
    return template.replace("__CAPTURE_DATA__", encoded)


def capture_scene(result):
    components.html(capture_scene_html(result), height=490, scrolling=False)


EXPLORE_AREAS = {
    "meadow": {"name": "🌿 산들바람 초원", "cost": 10, "unlock": 1, "floor": 0,
               "shiny": .05, "weights": [75, 20, 4, .9, .1], "color": "#83ddb3"},
    "forest": {"name": "🌙 달빛 숲", "cost": 50, "unlock": 5, "floor": .5,
               "shiny": .08, "weights": [45, 40, 13, 1.8, .2], "color": "#b7aeff"},
    "ruins": {"name": "💎 별빛 유적", "cost": 150, "unlock": 15, "floor": .75,
              "shiny": .12, "weights": [20, 40, 30, 8, 2], "color": "#88d8ff"},
    "sanctuary": {"name": "🌌 천상의 성역", "cost": 500, "unlock": 35, "floor": .9,
                  "shiny": .20, "weights": [5, 25, 40, 22, 8], "color": "#ffd68b"},
}
RARITY_ORDER = ["일반", "희귀", "초희귀", "전설", "환상"]


def area_options(area_id):
    area = EXPLORE_AREAS[area_id]
    highest = max(mon["level"] for mon in current()["collection"])
    lower = max(1, math.ceil(highest * area["floor"]))
    pools = {r: [] for r in RARITY_ORDER}
    for entry in ENCOUNTER_CATALOG:
        if entry[3] <= highest:
            pools[entry[2]].append(entry)
    weights = {r: w for r, w in zip(RARITY_ORDER, area["weights"]) if pools[r] and w > 0}
    total = sum(weights.values())
    probabilities = {r: w / total for r, w in weights.items()} if total else {}
    return area, highest, lower, pools, probabilities


def pick_pokemon(area_id="meadow"):
    p = current()
    if p.get("encounter"):
        goto("draw")
        return
    if area_id not in EXPLORE_AREAS:
        st.warning("탐험 장소를 선택해 주세요.")
        return
    area, highest, lower, pools, probabilities = area_options(area_id)
    if highest < area["unlock"]:
        st.warning(f"보유 포켓몬 최고 레벨이 Lv.{area['unlock']} 이상이어야 해요.")
        return
    if wallet()["coins"] < area["cost"]:
        st.warning(f"이 장소의 탐험 비용은 {area['cost']:,}코인이에요.")
        return
    if not probabilities or not action_ready():
        return
    rarity = random.choices(list(probabilities), weights=list(probabilities.values()))[0]
    name, number, rarity, minimum = random.choice(pools[rarity])
    mon = pokemon(number, level=random.randint(max(minimum, lower), highest),
                  shiny=random.random() < area["shiny"],
                  info={"name": name, "rarity": rarity, "image_id": number})
    wallet()["coins"] -= area["cost"]
    p["encounter"] = mon
    p["battle"] = None
    p.pop("battle_result_scene", None)
    ensure_battle()
    p["encounter_area"] = area_id
    goto("draw")


def render_explore_areas():
    st.subheader("🧭 탐험할 장소를 선택하세요")
    st.caption("비용은 새로운 포켓몬을 만날 때 한 번 소모돼요. 포획에는 볼이 별도로 필요해요. 희귀도와 진화형의 기존 레벨 제한도 유지해요.")
    columns = st.columns(2)
    for index, (area_id, area) in enumerate(EXPLORE_AREAS.items()):
        _, highest, lower, _, probabilities = area_options(area_id)
        locked = highest < area["unlock"]
        with columns[index % 2]:
            with st.container(border=True):
                st.subheader(area["name"])
                st.write(f"**{area['cost']:,}코인 / 만남 1회**")
                st.write(f"이로치 확률 **{area['shiny']:.0%}**")
                if locked:
                    st.caption(f"🔒 보유 최고 Lv.{area['unlock']}부터 개방 · 현재 Lv.{highest}")
                else:
                    st.caption(f"등장 Lv.{lower}~{highest} · 진화형은 종별 최소 레벨 적용")
                    st.caption(" · ".join(f"{r} {chance:.1%}" for r, chance in probabilities.items()))
                if st.button(
                    f"{area['name']} 탐험 · {area['cost']:,}코인",
                    key=f"explore_{area_id}", use_container_width=True,
                    disabled=locked or wallet()["coins"] < area["cost"],
                ):
                    pick_pokemon(area_id)
    st.caption("표시된 희귀도 확률은 현재 보유 최고 레벨에서 등장 가능한 종을 기준으로 계산해요. 고급 장소도 희귀·이로치 만남을 보장하지는 않아요.")


# =====================================
# 기록 공통 기능
# =====================================

def header(title, description=""):
    st.title(title)
    if description:
        st.caption(description)


def form_times(start, end):
    left, right = st.columns(2)

    with left:
        start_date = st.date_input(
            "시작 날짜",
            value=start.date(),
        )
        start_time = st.time_input(
            "시작 시각",
            value=start.time().replace(tzinfo=None),
        )

    with right:
        end_date = st.date_input(
            "종료 날짜",
            value=end.date(),
        )
        end_time = st.time_input(
            "종료 시각",
            value=end.time().replace(tzinfo=None),
        )

    return (
        dt_join(start_date, start_time),
        dt_join(end_date, end_time),
    )


def choose(records, kind):
    options = ["new"] + [
        record["uid"] for record in records
    ]

    def display(record_uid):
        if record_uid == "new":
            return "＋ 새 기록"

        record = next(
            (
                item for item in records
                if item["uid"] == record_uid
            ),
            None,
        )

        if record is None:
            return "기록"

        try:
            return parse_dt(
                record.get("end", record.get("time"))
            ).strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            return "이전 기록"

    selected = st.selectbox(
        "새 기록 / 기존 기록 수정",
        options,
        format_func=display,
        key=f"{kind}_choice_{st.session_state.sf_user}",
    )

    return next(
        (
            record for record in records
            if record["uid"] == selected
        ),
        None,
    )


def save_record(records, old, value):
    value["uid"] = old["uid"] if old else new_id()

    if old:
        index = next(
            i for i, record in enumerate(records)
            if record["uid"] == old["uid"]
        )
        records[index] = value
    else:
        records.append(value)

    sync_growth(current())

    if records is current()["cycles"]:
        earned = reward_sleep(value)
        success(
            f"수면 기록 저장 완료 · 경험치 반영 · 코인 +{earned}"
        )
    else:
        success("기록을 저장했어요.")


def delete_control(records, old, kind):
    if old is None:
        return

    confirmed = st.checkbox(
        "선택한 기록 삭제 확인",
        key=f"{kind}_confirm_{old['uid']}",
    )

    if confirmed:
        if st.button(
            "🗑️ 기록 삭제",
            key=f"{kind}_delete_{old['uid']}",
        ):
            records[:] = [
                record for record in records
                if record["uid"] != old["uid"]
            ]
            sync_growth(current())
            success("기록을 삭제했어요.")


def validate_interval(start, end, max_minutes=4320):
    minutes = (end - start).total_seconds() / 60

    if minutes <= 0:
        raise ValueError(
            "종료 시각은 시작 시각보다 늦어야 해요. "
            "자정을 넘겼다면 종료 날짜도 확인해 주세요."
        )

    if minutes > max_minutes:
        raise ValueError(
            f"전체 기록 시간은 {max_minutes}분 이하여야 해요."
        )

    if end > now() + timedelta(minutes=1):
        raise ValueError(
            "종료 시각이 현재보다 미래예요."
        )

    return minutes


# =====================================
# 디자인
# =====================================

st.markdown("""
<style>
.stApp {
    background: linear-gradient(145deg, #07152c, #15365e);
    color: #f8fbff;
}

.stApp h1,
.stApp h2,
.stApp h3,
.stApp h4 {
    color: #ffffff !important;
}

.stApp [data-testid="stWidgetLabel"] p {
    color: #ffffff !important;
    font-weight: 650;
}

.stApp [data-testid="stCaptionContainer"] p {
    color: #d8e8fc !important;
}

.stApp [data-testid="stMetricLabel"] p,
.stApp [data-testid="stMetricValue"] {
    color: white !important;
}

.stApp [data-testid="stAlert"] {
    background: #f3f8ff !important;
    border: 1px solid #9ab6d2 !important;
    color: #111111 !important;
}

.stApp [data-testid="stAlert"] * {
    color: #111111 !important;
    -webkit-text-fill-color: #111111 !important;
}

.stApp [data-baseweb="input"] input,
.stApp [data-baseweb="textarea"] textarea {
    background: #ffffff !important;
    color: #111111 !important;
    -webkit-text-fill-color: #111111 !important;
}

.stApp [data-baseweb="select"] > div {
    background: #ffffff !important;
    color: #111111 !important;
}

.stApp [data-baseweb="select"] span,
.stApp [data-baseweb="select"] input {
    color: #111111 !important;
    -webkit-text-fill-color: #111111 !important;
}

[data-baseweb="popover"],
[role="listbox"] {
    background: #ffffff !important;
}

[data-baseweb="popover"] *,
[role="option"] {
    color: #111111 !important;
}

.stApp div.stButton > button,
.stApp div.stDownloadButton > button,
.stApp div.stFormSubmitButton > button,
.stApp [data-testid="stFormSubmitButton"] button {
    background: #a9e0ff !important;
    border: 1px solid #d5efff !important;
    border-radius: 12px;
    color: #0b223d !important;
    min-height: 44px;
}

.stApp div.stButton > button *,
.stApp div.stDownloadButton > button *,
.stApp div.stFormSubmitButton > button *,
.stApp [data-testid="stFormSubmitButton"] button * {
    color: #0b223d !important;
}

.stApp [data-testid="stExpander"] summary {
    background: #173655;
    color: #ffffff;
}

.stApp [data-testid="stExpander"] summary * {
    color: #ffffff !important;
}

/* High-contrast navigation */
.stApp [data-testid="stSidebar"] {
    background: #10243d !important;
    border-right: 1px solid #466480 !important;
}
.stApp [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
.stApp [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
.stApp [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
.stApp [data-testid="stSidebar"] label,
.stApp [data-testid="stSidebar"] summary {
    color: #f1f6ff !important;
    -webkit-text-fill-color: #f1f6ff !important;
}
.stApp [data-testid="stSidebar"] div.stButton > button,
.stApp [data-testid="stSidebar"] div.stDownloadButton > button {
    background: #e5f1ff !important;
    border-color: #96b8da !important;
}
.stApp [data-testid="stSidebar"] div.stButton > button *,
.stApp [data-testid="stSidebar"] div.stDownloadButton > button * {
    color: #10243d !important;
    -webkit-text-fill-color: #10243d !important;
}
.stApp [data-testid="stSidebar"] [data-baseweb="input"] input,
.stApp [data-testid="stSidebar"] [data-baseweb="select"] span {
    color: #10243d !important;
    -webkit-text-fill-color: #10243d !important;
}
.st-key-top_shop_area [data-testid="stPopover"] > button {
    background: #ffdb85 !important;
    color: #18243a !important;
    border: 1px solid #ffe9b8 !important;
    border-radius: 14px !important;
    min-height: 48px;
    font-weight: 750;
}
.st-key-top_shop_area [data-testid="stPopover"] > button * {
    color: #18243a !important;
    -webkit-text-fill-color: #18243a !important;
}
/* Popovers can be rendered outside the main app DOM. */
[data-testid="stPopoverBody"] {
    background: #f7faff !important;
    color: #142a43 !important;
    border: 1px solid #b6cbe2 !important;
    border-radius: 16px !important;
    max-height: 75vh;
    overflow-y: auto;
}
[data-testid="stPopoverBody"] [data-testid="stMarkdownContainer"] p,
[data-testid="stPopoverBody"] [data-testid="stCaptionContainer"] p,
[data-testid="stPopoverBody"] [data-testid="stWidgetLabel"] p,
[data-testid="stPopoverBody"] [data-testid="stMetricLabel"] p,
[data-testid="stPopoverBody"] [data-testid="stMetricValue"],
[data-testid="stPopoverBody"] h3 {
    color: #142a43 !important;
    -webkit-text-fill-color: #142a43 !important;
}
.stApp div.stButton > button:disabled,
[data-testid="stPopoverBody"] button:disabled {
    background: #dde4ed !important;
    border-color: #bdc9d8 !important;
    color: #526277 !important;
    opacity: 1 !important;
}
[data-testid="stPopoverBody"] button:disabled * {
    color: #526277 !important;
    -webkit-text-fill-color: #526277 !important;
}

/* A dedicated shop avoids inheriting the dark main page's white text. */
.stApp .st-key-shop_panel {
    background: #f5f8ff !important;
    border: 1px solid #b5c9df !important;
    border-radius: 18px !important;
    padding: 22px !important;
    color: #142a43 !important;
}
.stApp .st-key-shop_panel.st-key-shop_panel * {
    color: #142a43 !important;
    -webkit-text-fill-color: #142a43 !important;
}
.stApp .st-key-shop_panel.st-key-shop_panel input,
.stApp .st-key-shop_panel.st-key-shop_panel [data-baseweb="input"],
.stApp .st-key-shop_panel.st-key-shop_panel [data-baseweb="select"] > div {
    background: #ffffff !important;
    border-color: #92aac5 !important;
    color: #142a43 !important;
}
.stApp .st-key-shop_panel.st-key-shop_panel button {
    background: #d1eaff !important;
    border: 1px solid #75a2c7 !important;
}
.stApp .st-key-shop_panel.st-key-shop_panel button:hover:not(:disabled) {
    background: #b4dcff !important;
}
.stApp .st-key-shop_panel.st-key-shop_panel button:disabled {
    background: #e1e7ef !important;
    border-color: #c1cbd8 !important;
    opacity: 1 !important;
}
.stApp .st-key-shop_panel.st-key-shop_panel button:disabled * {
    color: #596a7e !important;
    -webkit-text-fill-color: #596a7e !important;
}
.stApp .st-key-top_shop_area div.stButton > button {
    background: #ffdb85 !important;
    border-color: #ffe9b8 !important;
    min-height: 48px;
}
.stApp .st-key-top_shop_area div.stButton > button * {
    color: #18243a !important;
    -webkit-text-fill-color: #18243a !important;
}
</style>
""", unsafe_allow_html=True)

# ===== 1번 코드 끝. 바로 아래에 2번 코드를 붙여 넣으세요. =====
# =====================================
# 메뉴·백업
# =====================================

with st.sidebar:
    st.title("🌙 Sleep Free")
    st.caption("🔐 로그인된 내 계정 · 자동 저장")

    if st.button("로그아웃", key="_sfc_logout"):
        cloud_logout()

    users = list(st.session_state.sf_profiles)

    selected = st.selectbox(
        "프로필",
        users,
        index=users.index(st.session_state.sf_user),
    )

    if selected != st.session_state.sf_user:
        st.session_state.sf_user = selected
        goto("home")

    with st.expander("＋ 사용자 추가"):
        username = st.text_input(
            "새 사용자 이름",
            max_chars=30,
        )

        if st.button("프로필 만들기"):
            username = username.strip()

            if (
                not username
                or username in st.session_state.sf_profiles
            ):
                st.error("다른 이름을 입력해 주세요.")

            elif len(users) >= 20:
                st.error("최대 20명까지 만들 수 있어요.")

            else:
                st.session_state.sf_profiles[
                    username
                ] = fresh_profile()

                st.session_state.sf_user = username
                goto("home")

    st.write(
        f"📦 포켓몬 {len(current()['collection'])}마리"
    )
    st.write(
        f"🌙 파트너: {partner()['name']}"
    )

    pages = [
        ("🏠 홈", "home"),
        ("🔎 포켓몬 만나기 · 10코인", "draw"),
        ("📦 보관함", "collection"),
        ("🌙 수면 추적", "sleep"),
        ("📝 Sleep Cycle 입력", "cycle"),
        ("☀️ 졸림 기록", "day"),
        ("💤 낮잠 기록", "nap"),
        ("📊 데이터 분석", "analysis"),
        ("📚 수면 기록", "history"),
        ("⚙️ 설정", "settings"),
    ]

    for label, destination in pages:
        if st.button(
            label,
            key=f"nav_{destination}",
            use_container_width=True,
        ):
            goto(destination)

    st.divider()

    backup = json.dumps(
        {
            "version": "sleep-free-pokemon-3",
            "profiles": st.session_state.sf_profiles,
        },
        ensure_ascii=False,
        indent=2,
    )

    st.download_button(
        "💾 전체 데이터 백업",
        backup,
        file_name="sleep_free_save.json",
        mime="application/json",
        use_container_width=True,
    )

    with st.expander("📂 백업 불러오기"):
        uploaded = st.file_uploader(
            "JSON 파일",
            type=["json"],
        )

        st.caption(
            "복원하면 현재 데이터가 파일 내용으로 교체돼요."
        )

        if st.button("백업 복원"):
            try:
                if uploaded is None:
                    raise ValueError(
                        "먼저 파일을 선택해 주세요."
                    )

                if uploaded.size > 5 * 1024 * 1024:
                    raise ValueError(
                        "파일은 5MB 이하여야 해요."
                    )

                data = json.loads(uploaded.getvalue())
                profiles = data.get("profiles")

                if (
                    data.get("version") not in (
                        "sleep-free-pokemon-1",
                        "sleep-free-pokemon-2",
                        "sleep-free-pokemon-3",
                    )
                    or not isinstance(profiles, dict)
                    or not 1 <= len(profiles) <= 20
                ):
                    raise ValueError(
                        "지원하지 않는 백업 형식이에요."
                    )

                rebuilt = {}

                for username, source in profiles.items():
                    if (
                        not isinstance(username, str)
                        or not 1 <= len(username) <= 30
                        or not isinstance(source, dict)
                    ):
                        raise ValueError(
                            "프로필 정보가 올바르지 않아요."
                        )

                    for field in (
                        "collection",
                        "records",
                        "cycles",
                        "naps",
                        "day_checks",
                    ):
                        records = source.get(field, [])

                        if (
                            not isinstance(records, list)
                            or len(records) > 5000
                        ):
                            raise ValueError(
                                f"{field} 기록을 확인해 주세요."
                            )

                    rebuilt[username] = migrate(source)

                st.session_state.sf_profiles = rebuilt
                st.session_state.sf_user = next(
                    iter(rebuilt)
                )
                st.session_state.sf_drawn = None

                goto("home")

            except (
                ValueError,
                TypeError,
                KeyError,
                AttributeError,
                OverflowError,
            ) as error:
                st.error(f"복원 실패: {error}")

    st.caption(
        "로그인한 계정에 자동 저장됩니다. "
        "이 브라우저에서는 새로고침 후에도 로그인을 유지해요. "
        "프로필은 내 계정 안의 기록 묶음이며, "
        "친구는 별도 로그인 계정을 사용해 주세요."
    )


# =====================================
# 메인 화면
# =====================================

def render_shop():
    st.subheader("🛒 몬스터볼 상점")
    st.metric("보유 코인", f"{wallet()['coins']:,}")
    st.subheader("🍬 경험치 사탕 구매")
    st.caption("구매한 사탕은 가방에 보관돼요. 홈에서 원하는 포켓몬을 골라 사용하세요.")
    inventory = candy_inventory()
    for kind, details in CANDIES.items():
        st.write(f"**{details['name']} · {details['xp']} XP**")
        st.caption(f"보유 {inventory[kind]:,}개 · 개당 {details['price']:,}코인")
        quantity = int(st.number_input(
            f"{details['name']} 구매 수량", min_value=1, max_value=10000,
            value=1, step=1, key=f"candy_buy_amount_{kind}",
        ))
        cost = details["price"] * quantity
        if st.button(
            f"{details['name']} {quantity:,}개 구매 · {cost:,}코인",
            key=f"buy_candy_{kind}", disabled=wallet()["coins"] < cost,
        ):
            if buy_candies(kind, quantity):
                success(f"🍬 {details['name']} {quantity}개를 가방에 넣었어요. 홈에서 사용해 주세요.")
    st.divider()
    st.subheader("🔴 몬스터볼 구매")
    for ball, details in BALLS.items():
        st.caption(f"{ball} · 보유 {wallet()['balls'][ball]}개 · 성능 {details['power'] if ball != '마스터볼' else '확정 포획'}")
        quantity = int(st.number_input(
            f"{ball} 구매 수량",
            min_value=1, max_value=10000, value=1, step=1,
            key=f"buy_quantity_{ball}",
        ))
        total_price = details["price"] * quantity
        affordable = wallet()["coins"] // details["price"]
        st.caption(
            f"개당 {details['price']:,}코인 · 총 {total_price:,}코인 "
            f"· 현재 최대 {affordable:,}개 구매 가능"
        )
        if st.button(
            f"{ball} {quantity:,}개 구매 · {total_price:,}코인",
            key=f"buy_{ball}",
            disabled=wallet()["coins"] < total_price,
        ):
            if action_ready() and wallet()["coins"] >= total_price:
                wallet()["coins"] -= total_price
                wallet()["balls"][ball] += quantity
                success(f"{ball} {quantity:,}개를 {total_price:,}코인에 구매했어요.")
    st.caption("수면 보상: 40점 미만 25 / 40~60점 미만 50 / 60~80점 미만 100 / 80~90점 미만 175 / 90~100점 250코인. 계정당 기상 날짜별 1회.")


with st.container(key="top_shop_area"):
    wallet_column, shop_column = st.columns([4, 2])
    with wallet_column:
        st.markdown(f"### 🪙 {wallet()['coins']:,} 코인")
        total_balls = sum(wallet()["balls"].values())
        total_candies = sum(candy_inventory().values())
        st.caption(f"🔴 볼 {total_balls:,}개 · 🍬 사탕 {total_candies:,}개")
    with shop_column:
        if st.button("🛒 상점 열기", key="open_shop_page", use_container_width=True):
            if st.session_state.sf_page != "shop":
                st.session_state.sf_shop_return = st.session_state.sf_page
                goto("shop")


p = current()
page = st.session_state.sf_page

if st.session_state.sf_message:
    message_kind = st.session_state.pop("sf_message_kind", "success")
    if message_kind == "warning":
        st.warning(st.session_state.sf_message)
    else:
        st.success(st.session_state.sf_message)
    st.session_state.sf_message = ""


# 홈
if page == "home":
    header(
        "☁️ 🌙 Sleep Free",
        "함께 자고 성장하는 포켓몬 수면 기록실",
    )

    collection = p["collection"]
    ids = [mon["uid"] for mon in collection]
    selected_uid = p.get("home_selected_uid", p["partner_uid"])
    if selected_uid not in ids:
        selected_uid = p["partner_uid"]
    labels = {mon["uid"]: f"{mon['name']}{' ✨' if mon['shiny'] else ''} · Lv.{mon['level']} · {mon['uid'][:4]}" for mon in collection}
    pending_choice = st.session_state.pop("_sfc_pending_home_choice", None)
    profile_changed = st.session_state.get("_sfc_home_choice_profile") != st.session_state.sf_user
    if pending_choice and pending_choice["profile"] == st.session_state.sf_user and pending_choice["uid"] in ids:
        selected_uid = pending_choice["uid"]
        st.session_state["home_pokemon_choice"] = selected_uid
    elif profile_changed or st.session_state.get("home_pokemon_choice") not in ids:
        st.session_state["home_pokemon_choice"] = selected_uid
    st.session_state["_sfc_home_choice_profile"] = st.session_state.sf_user
    selected_uid = st.selectbox(
        "홈 포켓몬 · 사탕과 다음 전투의 대상", ids,
        index=ids.index(selected_uid), format_func=lambda uid: labels[uid],
        key="home_pokemon_choice",
    )
    p["home_selected_uid"] = selected_uid
    selected_mon = next(mon for mon in collection if mon["uid"] == selected_uid)
    left, center, right = st.columns([1, 2, 1])
    with center:
        show_pokemon(selected_mon, 250)
        st.subheader(f"{selected_mon['name']} · Lv.{selected_mon['level']}")
        growth_status(selected_mon)
        home_moves_panel(selected_mon)
        evolution_panel(selected_mon)
        if selected_uid == p["partner_uid"]:
            st.caption("🌙 현재 수면 파트너예요.")
        elif st.button("🌙 이 포켓몬을 수면 파트너로", key="home_make_partner"):
            if select_partner(selected_uid):
                success(f"{selected_mon['name']}을 파트너로 선택했어요. 홈 표시와 다음 전투 대상도 함께 바뀌었어요.")
    ongoing_battle = p.get("battle")
    if ongoing_battle and p.get("encounter") and ongoing_battle["ally"]["uid"] != selected_uid:
        st.info(f"진행 중인 전투는 {ongoing_battle['ally']['name']}이(가) 이어가요. 홈에서 선택한 {selected_mon['name']}은(는) 다음 만남부터 출전해요.")
    with st.container(border=True):
        home_candy_panel(selected_mon)

    today = now().date().isoformat()
    today_reward = wallet()["reward_days"].get(today)
    if today_reward is None:
        st.info("🌙 수면 점수를 저장하면 경험치와 25~250코인을 받아요. 기상 날짜별 1회 지급돼요.")
    else:
        st.success(f"🌙 오늘 기상 날짜의 수면 보상 +{today_reward:,}코인 수령 완료")
    with st.expander("수면 점수별 보상 확인"):
        st.write("40점 미만 **25코인** · 40~60점 미만 **50코인** · 60~80점 미만 **100코인** · 80~90점 미만 **175코인** · 90~100점 **250코인**")
        st.caption("기록한 날이 아니라 기상 날짜를 기준으로 지급해요. 이미 보상받은 날짜는 수정·삭제·재입력해도 중복 지급되지 않아요. 업데이트 이전 지급분은 유지해요.")

    if p.get("encounter"):
        st.caption("🔎 아직 만나고 있는 포켓몬이 있어요. ‘탐험 장소 선택’을 누르면 추가 비용 없이 이어서 볼 수 있어요.")
    a, b = st.columns(2)

    with a:
        if st.button(
            "🌙 수면 시작 / 종료",
            use_container_width=True,
        ):
            goto("sleep")

        if st.button(
            "📝 Sleep Cycle 기록",
            use_container_width=True,
        ):
            goto("cycle")

    with b:
        if st.button(
            "🧭 탐험 장소 선택",
            use_container_width=True,
        ):
            goto("draw")

        if st.button(
            "☀️ 낮 시간 점검",
            use_container_width=True,
        ):
            goto("day")


# Dedicated shop has one explicit color theme and avoids portal styling conflicts.
elif page == "shop":
    header("🛒 상점", "사탕과 몬스터볼을 구매하세요. 보유 코인과 총가격을 확인한 뒤 구매할 수 있어요.")
    if st.button("← 이전 화면으로", key="shop_back"):
        destination = st.session_state.get("sf_shop_return", "home")
        goto(destination if destination in ("home", "draw", "collection", "sleep", "cycle", "day", "nap", "analysis", "history", "settings") else "home")
    with st.container(border=True, key="shop_panel"):
        render_shop()


# 포켓몬 만나기 · 포획
elif page == "draw":
    header("🔎 포켓몬 만나기")
    st.info("장소별 탐험 비용이 달라요. 포획에는 볼 1개를 사용하고, 실패하면 같은 포켓몬에게 재도전할 수 있어요.")
    st.caption("희귀 Lv.5 · 초희귀 Lv.15 · 전설 Lv.35 · 환상 Lv.45부터 등장. 진화형은 종별 요구 레벨 이상에서 등장해요. 돌·교환·친밀도 등 특수 진화형은 최소 Lv.20을 적용해요.")
    result = st.session_state.pop("sf_capture_result", None)
    if result:
        capture_scene(result)
    last = p.get("encounter")
    if last:
        area_id = p.get("encounter_area", "meadow")
        area = EXPLORE_AREAS.get(area_id, EXPLORE_AREAS["meadow"])
        st.caption(f"📍 {area['name']}")
        fresh_reveal = st.session_state.get("_sfc_encounter_seen") != last["uid"]
        if fresh_reveal:
            st.session_state["_sfc_encounter_seen"] = last["uid"]
            capture_scene({"mode": "encounter", "mon": dict(last), "caught": False, "shakes": 1, "area": area_id})
        elif not result:
            show_pokemon(last, 240)
            st.subheader(f"{last['name']} · Lv.{last['level']} · {last['rarity']}")
            if last.get("shiny"):
                st.success("✨ 이로치 포켓몬! 특별한 색의 포켓몬이에요.")
        capture_delay = 1050 + (result.get("shakes", 3) - 1) * 900 + 1470 if result and not result["caught"] else 0
        battle = render_battle_panel(capture_delay)
        st.subheader("🔴 포획 시도")
        for ball, details in BALLS.items():
            count = wallet()["balls"][ball]
            chance = catch_probability(last, ball)
            label = f"{ball} 사용 · {count}개 · 포획 확률 {chance:.0%}"
            # Encounter UID in key makes queued clicks on an old encounter harmless.
            if st.button(label, key=f"catch_{last['uid']}_{ball}", disabled=count <= 0 or chance <= 0):
                if chance > 0 and action_ready() and p.get("encounter", {}).get("uid") == last["uid"] and wallet()["balls"][ball] > 0:
                    wallet()["balls"][ball] -= 1
                    caught = secrets.randbelow(1000000) / 1000000 < chance
                    st.session_state["sf_capture_result"] = {"caught": caught, "mon": dict(last), "ball": ball, "shakes": 3 if caught else secrets.randbelow(3) + 1}
                    if caught:
                        last["ball"] = ball
                        last["move_layout"] = [slot["id"] for slot in battle["wild"]["moves"]]
                        p["collection"].append(last)
                        p["encounter"] = None
                        p["battle"] = None
                        cloud_save()
                        st.session_state.sf_message = ""
                        st.rerun()
                    else:
                        st.session_state.sf_message = ""
                        wild_counter_after_ball()
                        cloud_save()
                        st.rerun()
        if st.button("이 포켓몬 보내주기", key=f"release_{last['uid']}"):
            if action_ready():
                p["encounter"] = None
                p["battle"] = None
                success("포켓몬을 보내줬어요.")
    else:
        if p.get("battle_result_scene"):
            render_battle_scene(p["battle_result_scene"])
        if p.get("battle_last_log"):
            with st.expander("지난 전투의 마지막 기록"):
                for text in p["battle_last_log"][-8:]:
                    st.write(text)
        render_explore_areas()


# 보관함
elif page == "collection":
    header("📦 포켓몬 보관함")

    st.write(
        f"총 {len(p['collection'])}마리 · "
        f"{len({mon['number'] for mon in p['collection']})}종"
    )

    search = st.text_input("포켓몬 이름 검색")
    shiny_only = st.checkbox("이로치만 보기")

    order = st.selectbox(
        "정렬",
        ["최근 획득순", "레벨 높은 순", "도감 번호순"],
    )

    items = [
        mon for mon in p["collection"]
        if search in mon["name"]
        and (not shiny_only or mon["shiny"])
    ]

    if order == "최근 획득순":
        items.reverse()

    elif order == "레벨 높은 순":
        items.sort(
            key=lambda mon: mon["level"],
            reverse=True,
        )

    else:
        items.sort(key=lambda mon: mon["number"])

    if items:
        total_pages = max(1, (len(items) + 8) // 9)

        selected_page = st.selectbox(
            "페이지",
            list(range(1, total_pages + 1)),
        )

        visible = items[
            (selected_page - 1) * 9:selected_page * 9
        ]

        columns = st.columns(3)

        for index, mon in enumerate(visible):
            with columns[index % 3]:
                with st.container(border=True):
                    show_pokemon(mon, 140)
                    st.write(f"**{mon['name']}**")
                    st.caption(
                        f"No.{mon['number']:04d} · "
                        f"{mon['rarity']}"
                    )

                    growth_status(mon)
                    evolution_panel(mon)
                    price = sale_price(mon)
                    active_fighter = ((p.get("battle") or {}).get("ally") or {}).get("uid")
                    can_sell = len(p["collection"]) > 1 and mon["uid"] != p["partner_uid"] and mon["uid"] != active_fighter and mon["uid"] not in wallet()["sold_uids"]
                    if st.button(f"판매 · {price}코인", key=f"sell_{mon['uid']}", disabled=not can_sell):
                        if can_sell and action_ready() and mon["uid"] not in wallet()["sold_uids"] and any(x["uid"] == mon["uid"] for x in p["collection"]):
                            wallet()["sold_uids"].append(mon["uid"])
                            p["collection"] = [x for x in p["collection"] if x["uid"] != mon["uid"]]
                            wallet()["coins"] += price
                            success(f"{mon['name']}을 판매해 {price}코인을 받았어요.")
                    if not can_sell:
                        st.caption("현재 파트너·전투 중인 포켓몬·마지막 한 마리·이미 판매한 개체는 판매할 수 없어요.")


                    if mon["uid"] == p["partner_uid"]:
                        st.success("현재 수면 파트너")

                    elif st.button(
                        "파트너 선택",
                        key=f"choose_{mon['uid']}",
                    ):
                        if select_partner(mon["uid"]):
                            st.session_state.sf_message = f"{mon['name']}을 파트너로 선택했어요."
                            goto("home")

    else:
        st.info("검색 결과가 없어요.")


# 수면 추적
elif page == "sleep":
    header("🌙 수면 추적")

    if p["sleep_start"]:
        sleep_mon = next(
            (
                mon for mon in p["collection"]
                if mon["uid"] == p.get("sleep_partner_uid")
            ),
            partner(),
        )
    else:
        sleep_mon = partner()

    show_pokemon(sleep_mon, 200)

    st.write(
        f"이번 수면 파트너: **{sleep_mon['name']}**"
    )

    if not p["sleep_start"]:
        st.info(
            "시작할 때 선택한 파트너가 "
            "이번 수면의 파트너로 기록돼요."
        )

        if st.button(
            "🌙 수면 시작",
            use_container_width=True,
        ):
            p["sleep_start"] = now().isoformat()
            p["sleep_partner_uid"] = p["partner_uid"]
            goto("sleep")

    else:
        try:
            start = parse_dt(p["sleep_start"])

            st.write(
                f"시작 시각: **{start:%Y-%m-%d %H:%M}**"
            )

            if st.button(
                "☀️ 수면 종료",
                use_container_width=True,
            ):
                end = now()
                validate_interval(start, end)

                p["records"].append({
                    "uid": new_id(),
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "goal": p["goal_hours"],
                    "awake_minutes": 0,
                    "feeling": "미입력",
                    "memo": "",
                    "partner_uid": p.get(
                        "sleep_partner_uid",
                        p["partner_uid"],
                    ),
                })

                p["sleep_start"] = None
                goto("cycle")

        except (ValueError, TypeError) as error:
            st.error(f"수면 기록 오류: {error}")

            if st.button("잘못된 수면 시작 기록 초기화"):
                p["sleep_start"] = None
                goto("sleep")

    st.caption(
        "버튼으로 기록한 시간만으로 경험치를 주지 않아요. "
        "종료 후 Sleep Cycle의 수면 점수를 입력해 주세요."
    )


# Sleep Cycle 기록
elif page == "cycle":
    header(
        "📝 Sleep Cycle 지표 입력",
        "앱에 표시된 값만 입력하세요. 없는 항목은 빈칸으로 두세요.",
    )

    records = p["cycles"]
    old = choose(records, "cycle")

    end = (
        parse_dt(old["end"])
        if old
        else now().replace(second=0, microsecond=0)
    )

    start = (
        parse_dt(old["start"])
        if old
        else end - timedelta(hours=7)
    )

    ids = [
        mon["uid"] for mon in p["collection"]
    ]

    names = {
        mon["uid"]: (
            f"{mon['name']} · Lv.{mon['level']}"
            + (" · ✨ 이로치" if mon["shiny"] else "")
            + f" · {index + 1}번"
        )
        for index, mon in enumerate(p["collection"])
    }

    if old:
        default_uid = old.get("partner_uid")
    else:
        default_uid = next(
            (
                record.get("partner_uid")
                for record in reversed(p["records"])
                if parse_dt(record["end"]).date() == end.date()
                and record.get("partner_uid") in ids
            ),
            p["partner_uid"],
        )

    if default_uid not in ids:
        default_uid = p["partner_uid"]

    st.info(
        "수면 점수 1점 = 1 XP예요. "
        "경험치는 기상 날짜당 한 번만 반영해요.\n\n"
        "그날 함께 잔 파트너와 날짜를 확인해 주세요. "
        "6시간 20분은 380분으로 입력하면 돼요."
    )

    form_id = (
        f"cycle_growth_{st.session_state.sf_user}_"
        f"{old['uid'] if old else 'new'}"
    )

    with st.form(form_id):
        slept_uid = st.selectbox(
            "이날 함께 잔 파트너",
            ids,
            index=ids.index(default_uid),
            format_func=lambda value: names[value],
        )

        start_dt, end_dt = form_times(start, end)
        st.subheader("Sleep Cycle 측정 지표")

        values = {}
        columns = st.columns(2)

        for index, (field, label, maximum) in enumerate(METRICS):
            previous = old.get(field) if old else None

            with columns[index % 2]:
                values[field] = st.text_input(
                    label,
                    value=(
                        ""
                        if previous is None
                        else str(previous)
                    ),
                    placeholder="선택 입력 · 예: 75",
                    key=f"{form_id}_{field}",
                )

        memo = st.text_area(
            "메모 (선택)",
            value=old.get("memo", "") if old else "",
            max_chars=500,
        )

        submitted = st.form_submit_button(
            "💾 Sleep Cycle 데이터 저장",
            use_container_width=True,
        )

        if submitted:
            try:
                validate_interval(start_dt, end_dt)

                record = {
                    "start": start_dt.isoformat(),
                    "end": end_dt.isoformat(),
                    "memo": memo,
                    "partner_uid": slept_uid,
                }

                for field, label, maximum in METRICS:
                    raw = values[field].strip().replace(",", ".")

                    if not raw:
                        record[field] = None
                        continue

                    try:
                        value = float(raw)
                    except ValueError:
                        raise ValueError(
                            f"「{label}」에는 숫자만 입력해 주세요."
                        )

                    if (
                        not math.isfinite(value)
                        or not 0 <= value <= maximum
                    ):
                        raise ValueError(
                            f"「{label}」은 "
                            f"0~{maximum} 범위로 입력해 주세요."
                        )

                    record[field] = value

                duplicate = any(
                    item is not old
                    and parse_dt(item["end"]).date()
                    == end_dt.date()
                    for item in records
                )

                if duplicate:
                    raise ValueError(
                        "같은 기상 날짜의 기록이 이미 있어요. "
                        "기존 기록을 선택해서 수정해 주세요."
                    )

                save_record(records, old, record)

            except (ValueError, TypeError) as error:
                st.error(f"저장되지 않았어요: {error}")

    delete_control(records, old, "cycle")

    st.caption(
        "수면의 질 점수가 없으면 경험치를 지급하지 않아요. "
        "점수는 Sleep Cycle의 추정값이며 "
        "게임 보상에 사용하는 앱 자체 규칙이에요."
    )


# 낮잠 기록
elif page == "nap":
    header("💤 낮잠 기록")

    records = p["naps"]
    old = choose(records, "nap")

    end = (
        parse_dt(old["end"])
        if old
        else now().replace(second=0, microsecond=0)
    )

    start = (
        parse_dt(old["start"])
        if old
        else end - timedelta(minutes=30)
    )

    with st.form(
        f"nap_form_{old['uid'] if old else 'new'}"
    ):
        start_dt, end_dt = form_times(start, end)

        memo = st.text_area(
            "메모",
            value=old.get("memo", "") if old else "",
            max_chars=500,
        )

        if st.form_submit_button(
            "💾 낮잠 저장",
            use_container_width=True,
        ):
            try:
                validate_interval(
                    start_dt, end_dt, 1440
                )

                overlapping = any(
                    item is not old
                    and parse_dt(item["start"]) < end_dt
                    and parse_dt(item["end"]) > start_dt
                    for item in records
                )

                if overlapping:
                    raise ValueError(
                        "다른 낮잠 기록과 시간이 겹쳐요."
                    )

                save_record(
                    records,
                    old,
                    {
                        "start": start_dt.isoformat(),
                        "end": end_dt.isoformat(),
                        "memo": memo,
                    },
                )

            except (ValueError, TypeError, KeyError) as error:
                st.error(f"저장되지 않았어요: {error}")

    delete_control(records, old, "nap")

    for record in sorted(
        records,
        key=lambda item: item.get("start", ""),
        reverse=True,
    )[:20]:
        try:
            start = parse_dt(record["start"])
            end = parse_dt(record["end"])
            minutes = (end - start).total_seconds() / 60

            st.write(
                f"💤 {start:%m/%d %H:%M} ~ "
                f"{end:%m/%d %H:%M} · {minutes:.0f}분"
            )

        except (ValueError, TypeError, KeyError):
            st.warning(
                "날짜 형식이 잘못된 이전 기록이 있어요."
            )


# 졸림 기록
elif page == "day":
    header(
        "☀️ 낮 시간 졸림 기록",
        "언제 얼마나 졸렸는지 하루 여러 번 기록할 수 있어요.",
    )

    records = p["day_checks"]
    old = choose(records, "day")
    moment = parse_dt(old["time"]) if old else now()

    with st.form(
        f"day_form_{old['uid'] if old else 'new'}"
    ):
        date = st.date_input(
            "기록 날짜",
            moment.date(),
        )

        time = st.time_input(
            "기록 시각",
            moment.time().replace(tzinfo=None),
        )

        level = st.select_slider(
            "졸림 정도",
            options=[1, 2, 3, 4, 5],
            value=int(old["sleepiness"]) if old else 2,
            format_func=lambda value: {
                1: "1 · 또렷함",
                2: "2 · 조금 나른함",
                3: "3 · 졸림",
                4: "4 · 매우 졸림",
                5: "5 · 깨어 있기 어려움",
            }[value],
        )

        if st.form_submit_button(
            "💾 졸림 저장",
            use_container_width=True,
        ):
            when = dt_join(date, time)

            if when > now() + timedelta(minutes=1):
                st.error(
                    "저장되지 않았어요: 미래 시각이에요."
                )
            else:
                save_record(
                    records,
                    old,
                    {
                        "time": when.isoformat(),
                        "sleepiness": level,
                    },
                )

    delete_control(records, old, "day")

    for record in sorted(
        records,
        key=lambda item: item.get("time", ""),
        reverse=True,
    )[:20]:
        try:
            st.write(
                f"{parse_dt(record['time']):%m/%d %H:%M} "
                f"· 졸림 {record['sleepiness']}/5"
            )

        except (ValueError, TypeError, KeyError):
            st.warning(
                "형식이 잘못된 이전 기록이 있어요."
            )

    if st.button("💤 낮잠 기록으로 이동"):
        goto("nap")

    st.caption(
        "졸림 정도는 직접 입력한 주관적 평가예요."
    )


# 분석
elif page == "analysis":
    header("📊 수면 데이터 분석")

    cycle_rows = []

    for record in p["cycles"]:
        try:
            row = {
                "날짜": parse_dt(
                    record["end"]
                ).date().isoformat()
            }

            for field, label, _ in METRICS:
                row[label] = record.get(field)

            cycle_rows.append(row)

        except (ValueError, TypeError, KeyError):
            continue

    if cycle_rows:
        frame = pd.DataFrame(cycle_rows)

        st.subheader("Sleep Cycle 기록")
        st.dataframe(
            frame,
            use_container_width=True,
            hide_index=True,
        )

        for field, title in [
            ("quality", "수면의 질 점수"),
            ("asleep", "수면 시간(분)"),
        ]:
            label = next(
                item[1]
                for item in METRICS
                if item[0] == field
            )

            chart = frame[["날짜", label]].copy()

            chart[label] = pd.to_numeric(
                chart[label],
                errors="coerce",
            )

            chart = (
                chart.groupby("날짜")[label]
                .mean()
                .dropna()
            )

            if not chart.empty:
                st.subheader(f"{title} 변화")
                st.line_chart(chart)

    else:
        st.info(
            "Sleep Cycle 지표를 입력하면 그래프가 나타나요."
        )

    day_rows = []

    for record in p["day_checks"]:
        try:
            day_rows.append({
                "시각": parse_dt(record["time"]),
                "졸림 정도": int(record["sleepiness"]),
            })
        except (ValueError, TypeError, KeyError):
            continue

    if day_rows:
        st.subheader("시간대별 졸림")

        day_frame = (
            pd.DataFrame(day_rows)
            .sort_values("시각")
            .set_index("시각")
        )
        st.line_chart(day_frame)

    nap_rows = []

    for record in p["naps"]:
        try:
            start = parse_dt(record["start"])
            end = parse_dt(record["end"])

            nap_rows.append({
                "날짜": start.date().isoformat(),
                "낮잠 시간(분)": (
                    end - start
                ).total_seconds() / 60,
            })

        except (ValueError, TypeError, KeyError):
            continue

    if nap_rows:
        st.subheader("날짜별 낮잠 시간")

        nap_frame = (
            pd.DataFrame(nap_rows)
            .groupby("날짜")["낮잠 시간(분)"]
            .sum()
        )
        st.bar_chart(nap_frame)

    st.subheader("CSV 다운로드")

    for label, key in [
        ("Sleep Cycle", "cycles"),
        ("낮잠", "naps"),
        ("졸림", "day_checks"),
    ]:
        records = p[key]

        if not records:
            continue

        output = io.StringIO()

        fields = list(dict.fromkeys(
            field
            for record in records
            for field in record
        ))

        writer = csv.DictWriter(
            output,
            fieldnames=fields,
        )
        writer.writeheader()

        for record in records:
            cleaned = {}

            for field, value in record.items():
                if (
                    isinstance(value, str)
                    and value.startswith(("=", "+", "-", "@"))
                ):
                    cleaned[field] = "'" + value
                else:
                    cleaned[field] = value

            writer.writerow(cleaned)

        st.download_button(
            f"📥 {label} CSV",
            output.getvalue().encode("utf-8-sig"),
            file_name=f"sleep_free_{key}.csv",
            mime="text/csv",
            key=f"csv_{key}",
        )


# 기록 보기
elif page == "history":
    header("📚 수면 기록")
    st.subheader("수면 시작·종료 기록")

    for record in reversed(p["records"][-100:]):
        try:
            start = parse_dt(record["start"])
            end = parse_dt(record["end"])
            hours = (end - start).total_seconds() / 3600

            with st.expander(
                f"{end:%Y-%m-%d} · {hours:.1f}시간"
            ):
                st.write(
                    f"시작: {start:%m/%d %H:%M} / "
                    f"종료: {end:%m/%d %H:%M}"
                )
                st.write(record.get("memo", ""))

        except (ValueError, TypeError, KeyError):
            st.warning(
                "일부 이전 기록의 날짜를 읽을 수 없어요."
            )

    st.subheader("Sleep Cycle 기록")

    names = {
        mon["uid"]: mon["name"]
        for mon in p["collection"]
    }

    for record in reversed(p["cycles"][-100:]):
        try:
            with st.expander(
                f"{parse_dt(record['end']):%Y-%m-%d} "
                "· Sleep Cycle"
            ):
                st.write(
                    "함께 잔 파트너: "
                    + names.get(
                        record.get("partner_uid"),
                        "미지정",
                    )
                )

                for field, label, _ in METRICS:
                    value = record.get(field)

                    st.write(
                        f"{label}: "
                        f"{value if value is not None else '미입력'}"
                    )

        except (ValueError, TypeError, KeyError):
            st.warning(
                "일부 이전 기록을 읽을 수 없어요."
            )


# 설정
elif page == "settings":
    header("⚙️ 설정")

    with st.form("settings_form"):
        goal = st.number_input(
            "목표 수면 시간",
            min_value=1.0,
            max_value=14.0,
            value=float(p["goal_hours"]),
            step=0.5,
        )

        if st.form_submit_button("저장"):
            p["goal_hours"] = goal
            st.success("목표 시간을 저장했어요.")

    st.info(
        "Sleep Cycle은 수동 입력 방식이에요. "
        "자동 연동이나 의료 진단 기능은 없어요."
    )


with st.expander("📖 경험치·진화 규칙"):
    st.write(
        "수면 점수 80점은 함께 잔 파트너에게 80 XP로 반영됩니다. "
        "사탕·전투 경험치와 기존 코인 레벨업 경험치는 수면 경험치와 별도로 보존합니다. "
        "Lv.1→2에는 1 XP, Lv.2→3에는 2 XP가 필요하며 "
        "Lv.99→100에는 99 XP가 필요합니다. 최대 레벨은 100입니다. "
        "남은 경험치는 다음 레벨로 이월됩니다. "
        "같은 기상 날짜의 수면 기록은 한 번만 보상에 반영합니다. "
        "재저장으로 중복 지급되지 않으며, 기록 수정·삭제 시 "
        "경험치와 레벨을 다시 계산합니다. "
        "이전 기록 중 파트너가 지정되지 않은 기록은 "
        "수정 화면에서 함께 잔 파트너를 지정하면 반영됩니다. "
        "기존 포켓몬 레벨은 처음 얻은 레벨로 보존합니다. "
        "진화는 조건 충족 후 직접 선택합니다. "
        "진화해도 이로치 여부와 경험치는 유지되며, "
        "기록 수정으로 레벨이 내려가도 진화 모습은 유지합니다. "
        "수면 점수는 외부 앱의 추정값을 게임 보상에 사용하는 것이며 "
        "의학적 수면의 질을 판정하는 기능이 아닙니다."
    )


with st.expander("🎁 보상 코드 입력"):
    with st.form("reward_code_form"):
        reward_code = st.text_input("코드", type="password")
        redeem = st.form_submit_button("코드 사용")
    if redeem:
        if reward_code.strip() != "10313":
            st.error("코드를 확인해 주세요.")
        elif "10313" in wallet()["codes"]:
            st.info("이 계정에서 이미 사용한 코드예요.")
        elif action_ready():
            wallet()["codes"].append("10313")
            wallet()["coins"] += 100000
            success("🎉 100,000코인을 받았어요!")

# 정상 실행이 끝날 때 설정 변경도 저장합니다.
cloud_save()

if st.session_state.get("_sfc_saved"):
    st.caption(
        "☁️ 내 계정에 저장 완료 · "
        + st.session_state["_sfc_saved"]
        + " (한국 시간)"
    )

# ===== 2번 코드 끝. 여기까지 붙인 뒤 Commit changes를 누르세요. =====
