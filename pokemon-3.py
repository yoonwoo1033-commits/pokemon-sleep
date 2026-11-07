import time
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
        mon["total_xp"] = totals[mon["uid"]] + mon.get("coin_xp", 0)
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
            "coin_xp": item.get("coin_xp", 0) if type(item.get("coin_xp", 0)) is int and 0 <= item.get("coin_xp", 0) <= 5000 else 0,
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
            if remote and cloud_fingerprint(remote[0]["save_data"]) == fingerprint:
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


def level_upgrade_cost(mon):
    return mon["level"] * 20


def buy_level_upgrade(mon_uid):
    profile = current()
    sync_growth(profile)
    mon = next((m for m in profile["collection"] if m["uid"] == mon_uid), None)
    if not mon or mon["level"] >= 100:
        return False
    cost = level_upgrade_cost(mon)
    if wallet()["coins"] < cost or not action_ready():
        return False
    wallet()["coins"] -= cost
    # XP equal to the current level advances exactly one level and retains
    # the existing fractional progress. Store separately from sleep rewards.
    mon["coin_xp"] = mon.get("coin_xp", 0) + mon["level"]
    sync_growth(profile)
    return True


def catch_probability(mon, ball):
    if ball == "마스터볼":
        return 1.0
    base = {"일반": .78, "희귀": .52, "초희귀": .30, "전설": .10, "환상": .06}.get(mon["rarity"], .5)
    return min(.95, max(.01, base * BALLS[ball]["power"] / (1 + (mon["level"] - 1) * .025)))


def sale_price(mon):
    return int(SALE_BASE.get(mon["rarity"], 10) * (1 + (mon["level"] - 1) * .10) * (2 if mon.get("shiny") else 1))


def reward_sleep(value):
    score = value.get("quality")
    if score is None:
        return 0
    day = parse_dt(value["end"]).date().isoformat()
    if day > now().date().isoformat() or day in wallet()["reward_days"]:
        return 0
    score = float(score)
    if not math.isfinite(score) or not 0 <= score <= 100:
        return 0
    coins = 5 if score < 40 else 10 if score < 60 else 20 if score < 80 else 35 if score < 90 else 50
    wallet()["reward_days"][day] = coins
    wallet()["coins"] += coins
    return coins


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
    template = '<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>\n*{box-sizing:border-box}body{margin:0;color:#f8faff;font-family:system-ui,-apple-system,sans-serif}.scene{position:relative;height:470px;overflow:hidden;border:1px solid #ffffff24;border-radius:28px;background:radial-gradient(ellipse at 50% 60%,#324970 0%,#10223d 50%,#071326 100%);isolation:isolate}.scene:before{content:\'\';position:absolute;inset:0;background:radial-gradient(circle at 12% 22%,#fff8 0 1px,transparent 2px),radial-gradient(circle at 85% 31%,#fff7 0 1px,transparent 2px),radial-gradient(circle at 72% 12%,#fff9 0 1px,transparent 2px),radial-gradient(circle at 28% 40%,#fff6 0 1px,transparent 2px)}.controls{position:absolute;right:16px;top:16px;display:flex;gap:8px;z-index:8}button{border:1px solid #fff4;background:#152740;color:white;border-radius:30px;padding:8px 14px;font-size:13px;cursor:pointer}button:hover{background:#2b4260}button:focus-visible{outline:3px solid #f9d973;outline-offset:3px}.hint{position:absolute;top:24px;left:24px;font-size:11px;letter-spacing:.22em;color:#b4c4df}.ring{position:absolute;width:240px;height:54px;border:1px solid #89afdb66;border-radius:50%;left:calc(50% - 120px);top:304px;background:#72a5dd0d;box-shadow:0 0 35px #7cafff14}.creature{position:absolute;top:56px;left:calc(50% - 100px);width:200px;height:200px;display:grid;place-items:center;filter:drop-shadow(0 10px 20px #0006);transform-origin:50% 85%;z-index:3}.creature img{width:100%;height:100%;object-fit:contain}.fallback{font-size:88px}.ball-wrap{position:absolute;top:229px;left:calc(50% - 42px);width:84px;height:84px;z-index:4;transform-origin:50% 90%}.ball{position:absolute;inset:0;border:5px solid #172033;border-radius:50%;background:linear-gradient(to bottom,var(--ball,#ed4453) 0 45%,#172033 45% 55%,#f5f7ff 55% 100%);box-shadow:inset 7px 8px 12px #ffffff5c,inset -8px -9px 14px #0003,0 12px 16px #0005}.ball:after{content:\'\';position:absolute;left:calc(50% - 14px);top:calc(50% - 14px);width:28px;height:28px;background:#edf2fa;border:5px solid #172033;border-radius:50%;box-shadow:inset 0 0 0 2px #c3ccda}.ball.bright:after{background:#ffdc76;box-shadow:0 0 24px #ffd86f}.ball.super:before,.ball.hyper:before,.ball.master:before{content:\'\';position:absolute;left:14px;right:14px;height:14px;top:7px;background:var(--stripe,#e74757);border-radius:15px 15px 4px 4px;transform:rotate(-7deg)}.ball.master:before{content:\'M\';color:white;background:transparent;text-align:center;font-size:17px;font-weight:900;top:0}.label{position:absolute;bottom:33px;text-align:center;left:15px;right:15px;z-index:6}.label h2{margin:0 0 9px;font-size:clamp(24px,4vw,38px);letter-spacing:-.05em}.label p{margin:0;color:#c6d5ed;font-size:14px}.dots{position:absolute;top:330px;left:0;right:0;display:flex;gap:8px;justify-content:center}.dots i{width:7px;height:7px;background:#d5e1f42b;border-radius:50%;transition:background .12s,box-shadow .12s}.dots i.on{background:#ffe6a4;box-shadow:0 0 12px #ffd15e}.flash{position:absolute;inset:0;background:#fff2c5;opacity:0;z-index:5;pointer-events:none}.halo{position:absolute;inset:20px;background:radial-gradient(circle at 50% 52%,#ffd97950,transparent 55%);opacity:0;pointer-events:none}.star{position:absolute;color:#ffe99e;font-size:42px;opacity:0;left:50%;top:264px;z-index:5;filter:drop-shadow(0 0 8px #ffdb69)}.s1{--x:-115px;--y:-105px;--r:-20deg}.s2{--x:85px;--y:-126px;--r:12deg}.s3{--x:-20px;--y:-165px;--r:5deg}.particle{position:absolute;left:50%;top:270px;width:6px;height:12px;border-radius:2px;opacity:0;background:var(--color);z-index:5}.anim-in{animation:absorb .62s ease-in forwards}.anim-shake{animation:shake .48s ease-in-out}.anim-drop{animation:drop .48s cubic-bezier(.3,.8,.6,1) forwards}.won .ball-wrap{animation:land .5s ease-out}.won .halo{opacity:1;transition:opacity .6s}.won .star{animation:star 1.4s ease-out forwards}.won .s2{animation-delay:.08s}.won .s3{animation-delay:.16s}.won .flash,.lost .flash{animation:flash .55s ease-out}.won .label h2{color:#ffe49a;animation:title .48s ease-out}.won .particle{animation:confetti 1.6s ease-out forwards;animation-delay:var(--delay)}.lost .ball-wrap{animation:open .35s forwards}.lost .creature{animation:escape .65s cubic-bezier(.2,.8,.4,1) forwards}.lost .label h2{color:#ffcfb5}.won .dots,.lost .dots{opacity:0}.replay{position:absolute;left:16px;bottom:16px;z-index:8;padding:6px 10px;font-size:11px;opacity:.7}\n@keyframes absorb{0%{transform:translateY(0) scale(1);filter:drop-shadow(0 0 10px #fff)}40%{opacity:1;filter:brightness(2) drop-shadow(0 0 20px #fff)}100%{transform:translateY(140px) scale(0);opacity:0;filter:brightness(3)}}@keyframes drop{0%{transform:translateY(-55px) scale(.65);opacity:0}65%{transform:translateY(6px) scale(1);opacity:1}100%{transform:translateY(0) scale(1);opacity:1}}@keyframes shake{0%,100%{transform:translateX(0) rotate(0)}25%{transform:translateX(-10px) rotate(-18deg)}65%{transform:translateX(9px) rotate(16deg)}}@keyframes land{0%{transform:scale(1.15)}45%{transform:scale(.94)}100%{transform:scale(1)}}@keyframes star{0%{opacity:0;transform:translate(-50%,0) scale(.1)}25%{opacity:1}65%,100%{opacity:1;transform:translate(var(--x),var(--y)) rotate(var(--r)) scale(1)}}@keyframes flash{0%{opacity:.8}100%{opacity:0}}@keyframes title{0%{transform:translateY(14px) scale(.9);opacity:0}100%{transform:translateY(0) scale(1);opacity:1}}@keyframes confetti{0%{opacity:1;transform:translate(0,0) rotate(0)}100%{opacity:0;transform:translate(var(--x),var(--y)) rotate(var(--r))}}@keyframes open{100%{transform:translateY(12px) scale(1.4);opacity:0}}@keyframes escape{0%{transform:translateY(125px) scale(0);opacity:0}65%{transform:translateY(-12px) scale(1.1);opacity:1}100%{transform:translateY(0) scale(1);opacity:1}}@media(prefers-reduced-motion:reduce){*{animation-duration:.01ms!important}.particle{display:none}.scene .star{animation-duration:.01ms!important}}@media(max-width:480px){.hint{top:65px;left:18px}.scene{border-radius:18px}.replay{bottom:8px;left:auto;right:12px}}\n.start-panel{position:absolute;inset:0;background:#071326c9;backdrop-filter:blur(6px);z-index:20;display:grid;place-content:center;gap:14px;text-align:center;padding:20px}.start-panel[hidden]{display:none}.start-panel strong{font-size:24px}.start-panel p{color:#d4e3fa;margin:0 0 6px;font-size:14px}.start-panel button{min-height:48px;background:#ffe1a0;color:#152740;border:0;font-weight:700}.start-panel button.silent{background:#243c5b;color:#fff}.shiny-reveal .creature{animation:shinyFloat 2.5s ease-in-out infinite}.shiny-reveal .ball-wrap,.shiny-reveal .dots{display:none}.shiny-reveal .halo{opacity:1;background:radial-gradient(circle at 50% 45%,#e4c5ff80,transparent 60%)}.shiny-reveal .star{animation:star 1.4s ease-out forwards;color:#efdbff}.shiny-reveal .flash{animation:flash .7s ease-out}.shiny-reveal .label h2{color:#f1d8ff}.shiny-reveal .ring{border-color:#ebc7ff}.shiny-reveal .particle{animation:confetti 2s ease-out forwards;animation-delay:var(--delay)}@keyframes shinyFloat{0%,100%{transform:translateY(-8px);filter:drop-shadow(0 0 18px #b6a2ff)}50%{transform:translateY(2px);filter:drop-shadow(0 0 32px #e4c3ff)}}@media(prefers-reduced-motion:reduce){.shiny-reveal .creature{animation:none}}\n.arrival .ball-wrap,.arrival .dots{display:none}.arrival .creature{opacity:0;transform:translateY(35px) scale(.6);filter:brightness(0) blur(12px)}.arrival .ring{animation:searchRing 1.4s ease-in-out infinite}.appeared .creature{animation:appear 1.15s cubic-bezier(.1,.8,.3,1) forwards}.appeared .ring{animation:none}.appeared .halo{opacity:.7;background:radial-gradient(circle at 50% 45%,var(--area-glow,#83ddb3),transparent 55%)}@keyframes appear{0%{opacity:0;transform:translateY(38px) scale(.6);filter:brightness(0) blur(12px)}40%{opacity:1;filter:brightness(.2) blur(2px)}100%{opacity:1;transform:translateY(0) scale(1);filter:brightness(1) drop-shadow(0 0 16px #c7f7ff55)}}@keyframes searchRing{0%,100%{transform:scale(.8);opacity:.3}50%{transform:scale(1.15);opacity:1}}@media(prefers-reduced-motion:reduce){.arrival .ring{animation:none}}\n</style></head><body><section class="scene" id="scene" aria-label="포획 결과 연출"><div class="start-panel" id="startPanel" hidden><strong>소리와 함께 볼까요?</strong><p id="audioHint">브라우저에서 효과음 재생을 허용해 주세요.</p><button id="startSound" type="button">🔊 소리와 함께 시작</button><button id="startSilent" class="silent" type="button">무음으로 시작</button></div><div class="hint">SLEEP FREE · CAPTURE</div><div class="controls"><button id="audio" type="button">🔊 소리 켜기</button></div><div class="halo"></div><div class="ring"></div><div class="creature" id="creature"></div><div class="ball-wrap" id="ballWrap"><div class="ball" id="ball"></div></div><div class="flash"></div><div class="star s1">✦</div><div class="star s2">✦</div><div class="star s3">✦</div><div class="dots"><i></i><i></i><i></i></div><div class="label" aria-live="polite"><h2 id="title">들어갔다…!</h2><p id="subtitle">볼 안에서 움직이고 있어요.</p></div><button class="replay" id="replay" type="button">↻ 연출 다시 보기</button></section><script>\nconst data = __CAPTURE_DATA__;\nconst scene=document.getElementById(\'scene\'), creature=document.getElementById(\'creature\'), wrap=document.getElementById(\'ballWrap\'), ball=document.getElementById(\'ball\'), title=document.getElementById(\'title\'), subtitle=document.getElementById(\'subtitle\'), audioBtn=document.getElementById(\'audio\');\nif(data.image){const img=document.createElement(\'img\');img.src=data.image;img.alt=data.name;creature.append(img)}else{const fallback=document.createElement(\'span\');fallback.className=\'fallback\';fallback.textContent=\'🌟\';creature.append(fallback)}\nconst palette={\'몬스터볼\':[\'#ed4453\',\'normal\',\'#fff\'],\'슈퍼볼\':[\'#4285df\',\'super\',\'#ed4453\'],\'하이퍼볼\':[\'#293141\',\'hyper\',\'#ffce55\'],\'마스터볼\':[\'#8856bd\',\'master\',\'#f2b5e7\']};\nconst theme=palette[data.ball]||palette[\'몬스터볼\'];ball.style.setProperty(\'--ball\',theme[0]);ball.style.setProperty(\'--stripe\',theme[2]);ball.classList.add(theme[1]);\nfor(let i=0;i<24;i++){const p=document.createElement(\'b\');p.className=\'particle\';const a=Math.PI*2*i/24;const r=100+(i%5)*30;p.style.setProperty(\'--x\',`${Math.cos(a)*r}px`);p.style.setProperty(\'--y\',`${Math.sin(a)*r-40}px`);p.style.setProperty(\'--r\',`${i*63}deg`);p.style.setProperty(\'--delay\',`${(i%4)*.04}s`);p.style.setProperty(\'--color\',[\'#ffe29a\',\'#91e6d5\',\'#acd0ff\',\'#efb7fa\'][i%4]);scene.append(p)}\nlet ctx=null,muted=false,timers=[],started=0,finished=false,hasStarted=false;\nconst startPanel=document.getElementById("startPanel"),audioHint=document.getElementById("audioHint");\ntry{muted=localStorage.getItem(\'sf-capture-muted\')===\'1\'}catch(_){}\nfunction audioContext(){if(!ctx){const C=window.AudioContext||window.webkitAudioContext;if(C)ctx=new C()}return ctx}\nfunction soundButton(){const running=ctx&&ctx.state===\'running\';audioBtn.textContent=muted?\'🔇 소리 켜기\':running?\'🔊 소리 끄기\':\'🔊 소리 켜기\'}\nfunction tone(freq,delay,length=.12,volume=.07,type=\'sine\',end=null){try{if(muted||!ctx||ctx.state!==\'running\')return;const t=ctx.currentTime+delay,o=ctx.createOscillator(),g=ctx.createGain();o.type=type;o.frequency.setValueAtTime(freq,t);if(end)o.frequency.exponentialRampToValueAtTime(end,t+length);g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(volume,t+.012);g.gain.exponentialRampToValueAtTime(.001,t+length);o.connect(g);g.connect(ctx.destination);o.start(t);o.onended=()=>{try{o.disconnect();g.disconnect()}catch(_){}};o.stop(t+length+.02)}catch(_){soundButton()}}\nfunction jingle(){if(data.mode===\'encounter\'){if(data.shiny)[880,1174.66,1396.91,1760,2093].forEach((f,i)=>tone(f,i*.10,.30,.045,\'sine\'));else{tone(523,0,.2,.04);tone(659,.12,.25,.04)}return}if(data.caught){[523.25,659.25,783.99,1046.5].forEach((f,i)=>tone(f,i*.115,i===3?.48:.18,.065,\'triangle\'));tone(261.63,0,.5,.035)}else{tone(392,0,.25,.07,\'triangle\',196);tone(220,.2,.25,.035,\'sine\',165)}}\nfunction later(ms,fn){timers.push(setTimeout(fn,ms))}\nfunction launch(){timers.forEach(clearTimeout);timers=[];started=performance.now();finished=false;hasStarted=true;startPanel.hidden=true;scene.classList.remove(\'won\',\'lost\',\'shiny-reveal\',\'arrival\',\'appeared\');creature.classList.remove(\'anim-in\');wrap.classList.remove(\'anim-shake\',\'anim-drop\');ball.classList.remove(\'bright\');document.querySelectorAll(\'.dots i\').forEach(x=>x.classList.remove(\'on\'));title.textContent=\'들어갔다…!\';subtitle.textContent=`${data.ball}이 포켓몬을 감쌌어요.`;if(data.mode===\'encounter\'){\n const areaNames={meadow:\'산들바람 초원\',forest:\'달빛 숲\',ruins:\'별빛 유적\',sanctuary:\'천상의 성역\'};\n const colors={meadow:\'#83ddb350\',forest:\'#b7aeff50\',ruins:\'#88d8ff50\',sanctuary:\'#ffd68b50\'};\n scene.style.setProperty(\'--area-glow\',colors[data.area]||colors.meadow);\n scene.classList.add(\'arrival\');title.textContent=\'무언가 다가온다…\';subtitle.textContent=areaNames[data.area]||areaNames.meadow;\n document.querySelector(\'.hint\').textContent=\'SLEEP FREE · EXPLORE\';\n tone(220,0,.5,.025,\'sine\',440);\n later(650,()=>{scene.classList.add(\'appeared\');title.textContent=\'풀숲이 흔들린다…\';tone(440,0,.4,.035,\'sine\',880)});\n later(1800,()=>{finished=true;title.textContent=data.shiny?\'✨ 이로치 발견!\':`야생 ${data.name} 등장!`;subtitle.textContent=`${data.name} · Lv.${data.level} · ${data.rarity}`;\n  if(data.shiny){scene.classList.remove(\'appeared\',\'arrival\');scene.classList.add(\'shiny-reveal\');jingle()}else{tone(523,0,.2,.04);tone(659,.12,.25,.04)}});return} wrap.style.opacity=\'0\';void scene.offsetWidth;creature.classList.add(\'anim-in\');tone(700,0,.45,.035,\'sine\',250);\n later(420,()=>{wrap.style.opacity=\'1\';wrap.classList.add(\'anim-drop\')});\n [1050,1950,2850].slice(0,data.shakes).forEach((ms,index)=>later(ms,()=>{wrap.classList.remove(\'anim-drop\',\'anim-shake\');void wrap.offsetWidth;wrap.classList.add(\'anim-shake\');document.querySelectorAll(\'.dots i\')[index].classList.add(\'on\');title.textContent=[\'한 번…\',\'두 번…\',\'세 번…!\'][index];subtitle.textContent=\'조금만 더…\';tone(170,0,.12,.065,\'sine\',100);tone(300,.11,.065,.025)}));\n later(1050 + (data.shakes - 1) * 900 + 970,()=>{finished=true;wrap.classList.remove(\'anim-shake\');scene.classList.add(data.caught?\'won\':\'lost\');if(data.caught){ball.classList.add(\'bright\');title.textContent=`잡았다! ${data.name}!`;subtitle.textContent=`Lv.${data.level} · ${data.rarity} · 보관함에 들어왔어요.`}else{title.textContent=\'앗! 볼에서 튀어나왔다!\';subtitle.textContent=`${data.name}에게 다른 볼로 다시 도전해 보세요.`}jingle()});}\nfunction saveMute(){try{localStorage.setItem(\'sf-capture-muted\',muted?\'1\':\'0\')}catch(_){}}\nasync function enableSound(){\n try{\n  const ac=audioContext();if(!ac)return false;\n  // A resume promise may remain pending when Safari blocks playback.\n  await Promise.race([ac.resume(),new Promise(resolve=>setTimeout(resolve,1200))]);\n  if(ac.state!==\'running\')return false;\n  muted=false;saveMute();soundButton();return true;\n }catch(_){return false}\n}\ndocument.getElementById(\'startSound\').addEventListener(\'click\',async()=>{\n if(await enableSound())launch();\n else audioHint.textContent=\'소리를 재생할 수 없어요. 무음으로 시작할 수 있어요.\';\n});\ndocument.getElementById(\'startSilent\').addEventListener(\'click\',()=>{muted=true;saveMute();soundButton();launch()});\naudioBtn.addEventListener(\'click\',async()=>{\n if(ctx&&ctx.state===\'running\'&&!muted){muted=true;saveMute();soundButton();return}\n if(await enableSound()){if(!hasStarted)launch();else if(finished)jingle();else tone(660,0,.08,.025)}\n else{audioBtn.textContent=\'🔇 소리 재생 제한\';if(!hasStarted)startPanel.hidden=false}\n});\ndocument.getElementById(\'replay\').addEventListener(\'click\',async()=>{\n if(!muted&&!(await enableSound())){startPanel.hidden=false;return}launch();\n});\nsoundButton();\ntry{const ac=audioContext();if(muted||(ac&&ac.state===\'running\'))launch();else startPanel.hidden=false}catch(_){startPanel.hidden=false}\nwindow.addEventListener(\'pagehide\',()=>{timers.forEach(clearTimeout);if(ctx)ctx.close().catch(()=>{})});\n</script></body></html>\n'
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
    st.subheader("⬆️ 포켓몬 레벨업")
    collection = current()["collection"]
    names = {m["uid"]: f"{m['name']} · Lv.{m['level']}" for m in collection}
    chosen = st.selectbox(
        "레벨업할 포켓몬", list(names),
        format_func=lambda uid: names[uid],
        key="coin_levelup_choice",
    )
    mon = next(m for m in collection if m["uid"] == chosen)
    st.caption("한 번에 1레벨 상승 · 비용은 현재 레벨 × 20코인 · 최대 Lv.100. 수면 경험치와 코인 경험치를 함께 저장해요.")
    if mon["level"] >= 100:
        st.success("최고 레벨 Lv.100이에요!")
    else:
        cost = level_upgrade_cost(mon)
        if st.button(
            f"Lv.{mon['level']} → {mon['level'] + 1} · {cost:,}코인",
            key=f"coin_levelup_{mon['uid']}_{mon['level']}",
            disabled=wallet()["coins"] < cost,
        ):
            name = mon["name"]
            if buy_level_upgrade(chosen):
                success(f"⬆️ {name}이 Lv.{mon['level']}로 성장했어요!")
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
    st.caption("수면 보상: 0~39점 5 / 40~59점 10 / 60~79점 20 / 80~89점 35 / 90~100점 50코인. 계정당 기상 날짜별 1회.")


with st.container(key="top_shop_area"):
    wallet_column, shop_column = st.columns([4, 2])
    with wallet_column:
        st.markdown(f"### 🪙 {wallet()['coins']:,} 코인")
    with shop_column:
        with st.popover("🛒 상점 열기", use_container_width=True):
            render_shop()


p = current()
page = st.session_state.sf_page

if st.session_state.sf_message:
    st.success(st.session_state.sf_message)
    st.session_state.sf_message = ""


# 홈
if page == "home":
    header(
        "☁️ 🌙 Sleep Free",
        "함께 자고 성장하는 포켓몬 수면 기록실",
    )

    left, center, right = st.columns([1, 2, 1])

    with center:
        show_pokemon(partner(), 250)
        st.subheader(
            f"오늘의 파트너 · {partner()['name']}"
        )
        growth_status(partner())
        evolution_panel(partner())

    st.info(
        "Sleep Cycle의 수면 점수를 기록하면 "
        "그날 함께 잔 파트너가 경험치를 얻어요."
    )

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
        else:
            show_pokemon(last, 240)
            st.subheader(f"{last['name']} · Lv.{last['level']} · {last['rarity']}")
            if last.get("shiny"):
                st.success("✨ 이로치 포켓몬! 특별한 색의 포켓몬이에요.")
        for ball, details in BALLS.items():
            count = wallet()["balls"][ball]
            chance = catch_probability(last, ball)
            label = f"{ball} 사용 · {count}개 · 포획 확률 {chance:.0%}"
            # Encounter UID in key makes queued clicks on an old encounter harmless.
            if st.button(label, key=f"catch_{last['uid']}_{ball}", disabled=count <= 0):
                if action_ready() and p.get("encounter", {}).get("uid") == last["uid"] and wallet()["balls"][ball] > 0:
                    wallet()["balls"][ball] -= 1
                    caught = secrets.randbelow(1000000) / 1000000 < chance
                    st.session_state["sf_capture_result"] = {"caught": caught, "mon": dict(last), "ball": ball, "shakes": 3 if caught else secrets.randbelow(3) + 1}
                    if caught:
                        last["ball"] = ball
                        p["collection"].append(last)
                        p["encounter"] = None
                        cloud_save()
                        st.session_state.sf_message = ""
                        st.rerun()
                    else:
                        cloud_save()
                        st.session_state.sf_message = ""
                        st.rerun()
        if st.button("이 포켓몬 보내주기", key=f"release_{last['uid']}"):
            if action_ready():
                p["encounter"] = None
                success("포켓몬을 보내줬어요.")
    else:
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
                    can_sell = len(p["collection"]) > 1 and mon["uid"] != p["partner_uid"] and mon["uid"] not in wallet()["sold_uids"]
                    if st.button(f"판매 · {price}코인", key=f"sell_{mon['uid']}", disabled=not can_sell):
                        if action_ready() and mon["uid"] not in wallet()["sold_uids"] and any(x["uid"] == mon["uid"] for x in p["collection"]):
                            wallet()["sold_uids"].append(mon["uid"])
                            p["collection"] = [x for x in p["collection"] if x["uid"] != mon["uid"]]
                            wallet()["coins"] += price
                            success(f"{mon['name']}을 판매해 {price}코인을 받았어요.")
                    if not can_sell:
                        st.caption("파트너와 마지막 한 마리는 판매할 수 없어요.")


                    if mon["uid"] == p["partner_uid"]:
                        st.success("현재 수면 파트너")

                    elif st.button(
                        "파트너 선택",
                        key=f"choose_{mon['uid']}",
                    ):
                        p["partner_uid"] = mon["uid"]
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
        "코인으로 구매한 레벨업 경험치는 수면 경험치와 별도로 보존합니다. "
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
