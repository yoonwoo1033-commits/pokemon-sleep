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
        mon["total_xp"] = totals[mon["uid"]]
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
            timeout=20,
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
    }


def cloud_save():
    if not st.session_state.get("_sfc_loaded"):
        return

    payload = cloud_payload()

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
        st.error(
            "자동 저장에 실패했어요. " + str(error)
        )

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

        st.session_state.sf_page = "home"
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

    st.rerun()


cloud_login_gate()

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


def pick_pokemon():
    p = current()
    maximum_level = max(
        mon["level"] for mon in p["collection"]
    )
    fallback = False

    try:
        with st.spinner("새로운 포켓몬을 찾는 중..."):
            number = random.choice(species_ids())
            info = species_info(number)

            mon = pokemon(
                number,
                level=random.randint(1, maximum_level),
                shiny=random.random() < 0.05,
                info=info,
            )

    except (
        requests.RequestException,
        ValueError,
        KeyError,
        TypeError,
    ):
        fallback = True
        number = random.choice(POKEMON)[1]

        mon = pokemon(
            number,
            level=random.randint(1, maximum_level),
            shiny=random.random() < 0.05,
        )

    p["collection"].append(mon)
    st.session_state.sf_drawn = mon["uid"]

    if fallback:
        st.session_state.sf_message = (
            "전체 도감 연결에 실패해 "
            "기본 목록에서 포켓몬을 뽑았어요."
        )

    goto("draw")


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
        success(
            "수면 기록을 저장하고 경험치를 반영했어요."
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
        ("🎲 포켓몬 뽑기", "draw"),
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
        "새로고침 후 다시 로그인하면 기록을 불러올 수 있어요. "
        "프로필은 내 계정 안의 기록 묶음이며, "
        "친구는 별도 로그인 계정을 사용해 주세요."
    )


# =====================================
# 메인 화면
# =====================================

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
            "🎲 포켓몬 뽑기",
            use_container_width=True,
        ):
            pick_pokemon()

        if st.button(
            "☀️ 낮 시간 점검",
            use_container_width=True,
        ):
            goto("day")


# 포켓몬 뽑기
elif page == "draw":
    header("🎲 포켓몬 뽑기")

    highest = max(
        mon["level"] for mon in p["collection"]
    )

    st.info(
        f"등장 레벨: 1~{highest} 동일 확률 · "
        "이로치 확률: 5%\n\n"
        "전체 도감의 종별 기본 모습을 뽑아요."
    )

    last = next(
        (
            mon for mon in p["collection"]
            if mon["uid"] == st.session_state.sf_drawn
        ),
        None,
    )

    if last:
        show_pokemon(last, 240)
        st.subheader(
            f"{last['name']} · {last['rarity']}"
        )

        growth_status(last)
        evolution_panel(last)

        if st.button("🌙 이 포켓몬을 파트너로"):
            p["partner_uid"] = last["uid"]
            goto("home")

    else:
        show_pokemon(partner(), 180)

    if st.button(
        "🔴 몬스터볼 던지기",
        use_container_width=True,
    ):
        pick_pokemon()


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


# 정상 실행이 끝날 때 설정 변경도 저장합니다.
cloud_save()

if st.session_state.get("_sfc_saved"):
    st.caption(
        "☁️ 내 계정에 저장 완료 · "
        + st.session_state["_sfc_saved"]
        + " (한국 시간)"
    )

# ===== 2번 코드 끝. 여기까지 붙인 뒤 Commit changes를 누르세요. =====
