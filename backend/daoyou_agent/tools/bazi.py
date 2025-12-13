"""八字排盘工具 - 从 daoyou 项目迁移，移除 Pydantic 依赖"""
from datetime import datetime, timedelta
from calendar import monthrange
from typing import Dict, List, Tuple, Any
import ephem
from lunarcalendar import Converter, Solar, Lunar
from loguru import logger

TIANGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
ZODIAC = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]

SOLAR_TERMS = {"立春": 315, "惊蛰": 345, "清明": 15, "立夏": 45, 
               "芒种": 75, "小暑": 105, "立秋": 135, "白露": 165,
               "寒露": 195, "立冬": 225, "大雪": 255, "小寒": 285}

NA_YIN = [["海中金", "炉中火", "大林木", "路旁土", "剑锋金"],
          ["山头火", "涧下水", "城头土", "白蜡金", "杨柳木"],
          ["泉中水", "屋上土", "霹雳火", "松柏木", "长流水"],
          ["砂石金", "山下火", "平地木", "壁上土", "金箔金"],
          ["佛灯火", "天河水", "大驿土", "钗钏金", "桑柘木"],
          ["大溪水", "沙中土", "天上火", "石榴木", "大海水"]]

SHI_SHEN_TABLE = {
    "甲": ["比肩", "劫财", "食神", "伤官", "偏财", "正财", "七杀", "正官", "偏印", "正印"],
    "乙": ["劫财", "比肩", "伤官", "食神", "正财", "偏财", "正官", "七杀", "正印", "偏印"],
    "丙": ["偏印", "正印", "比肩", "劫财", "食神", "伤官", "偏财", "正财", "七杀", "正官"],
    "丁": ["正印", "偏印", "劫财", "比肩", "伤官", "食神", "正财", "偏财", "正官", "七杀"],
    "戊": ["七杀", "正官", "偏印", "正印", "比肩", "劫财", "食神", "伤官", "偏财", "正财"],
    "己": ["正官", "七杀", "正印", "偏印", "劫财", "比肩", "伤官", "食神", "正财", "偏财"],
    "庚": ["偏财", "正财", "七杀", "正官", "偏印", "正印", "比肩", "劫财", "食神", "伤官"],
    "辛": ["正财", "偏财", "正官", "七杀", "正印", "偏印", "劫财", "比肩", "伤官", "食神"],
    "壬": ["食神", "伤官", "偏财", "正财", "七杀", "正官", "偏印", "正印", "比肩", "劫财"],
    "癸": ["伤官", "食神", "正财", "偏财", "正官", "七杀", "正印", "偏印", "劫财", "比肩"]}

CANG_GAN = {"子": ["癸"], "丑": ["己", "癸", "辛"], "寅": ["甲", "丙", "戊"], "卯": ["乙"],
            "辰": ["戊", "乙", "癸"], "巳": ["丙", "戊", "庚"], "午": ["丁", "己"], "未": ["己", "丁", "乙"],
            "申": ["庚", "壬", "戊"], "酉": ["辛"], "戌": ["戊", "辛", "丁"], "亥": ["壬", "甲"]}

CHANG_SHENG_MAP = {
    "甲": ["亥", "子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌"],
    "乙": ["午", "巳", "辰", "卯", "寅", "丑", "子", "亥", "戌", "酉", "申", "未"],
    "丙": ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"],
    "丁": ["酉", "申", "未", "午", "巳", "辰", "卯", "寅", "丑", "子", "亥", "戌"],
    "戊": ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"],
    "己": ["酉", "申", "未", "午", "巳", "辰", "卯", "寅", "丑", "子", "亥", "戌"],
    "庚": ["巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑", "寅", "卯", "辰"],
    "辛": ["子", "亥", "戌", "酉", "申", "未", "午", "巳", "辰", "卯", "寅", "丑"],
    "壬": ["申", "酉", "戌", "亥", "子", "丑", "寅", "卯", "辰", "巳", "午", "未"],
    "癸": ["卯", "寅", "丑", "子", "亥", "戌", "酉", "申", "未", "午", "巳", "辰"]}
CHANG_SHENG_POSITIONS = ["长生", "沐浴", "冠带", "临官", "帝旺", "衰", "病", "死", "墓", "绝", "胎", "养"]


def calculate_bazi(year: int, month: int, day: int, hour: str, gender: str, birth_place: str,
                   minute: str = "00", calendarType: str = "solar", isLeapMonth: bool = False) -> Dict[str, Any]:
    """八字排盘（MCP 工具接口）"""
    try:
        hour_int, minute_int = int(hour), int(minute)
        if calendarType == "lunar":
            lunar_date = _create_lunar_date(year, month, day, isLeapMonth)
            solar_conv = Converter.Lunar2Solar(lunar_date).to_date()
            solar_year, solar_month, solar_day = solar_conv.year, solar_conv.month, solar_conv.day
        else:
            solar_year, solar_month, solar_day = year, month, day
            lunar_date = Converter.Solar2Lunar(Solar(year, month, day))
        
        solar_date = datetime(solar_year, solar_month, solar_day, hour_int, minute_int)
        prev_term, next_term = _calculate_prev_next_solar_terms(solar_date)
        
        pillars = {
            "year": _get_pillar_detail(_calculate_year_pillar(lunar_date.year)),
            "month": _get_pillar_detail(_calculate_month_pillar(lunar_date.year, lunar_date.month, lunar_date.isleap, prev_term)),
            "day": _get_pillar_detail(_calculate_day_pillar(solar_year, solar_month, solar_day, hour_int)),
            "hour": _get_pillar_detail(_calculate_hour_pillar(solar_year, solar_month, solar_day, hour_int)),
        }
        
        day_master = pillars["day"]["gan"]
        for key, pillar in pillars.items():
            pillar["shi_shen"] = "日主" if key == "day" else SHI_SHEN_TABLE[day_master][TIANGAN.index(pillar["gan"])]
            zhi_cang = {}
            for cg in pillar["cang_gan"]:
                zhi_cang[cg] = SHI_SHEN_TABLE[day_master][TIANGAN.index(cg)]
            pillar["cang_gan"] = zhi_cang
        
        da_yun = _calculate_da_yun(solar_date, gender, pillars, prev_term, next_term)
        qiyun_age = da_yun[0]["start_age"] if da_yun else 0
        
        result = {
            "success": True, "solar_date": solar_date.strftime("%Y-%m-%d %H:%M"),
            "gender": gender, "birth_place": birth_place,
            "lunar_date": {"year": lunar_date.year, "month": lunar_date.month, "day": lunar_date.day,
                          "is_leap": lunar_date.isleap, "chinese_month": _get_lunar_month_name(lunar_date.month),
                          "chinese_day": _get_lunar_day_name(lunar_date.day)},
            "previous_term": {"name": prev_term["name"], "datetime": prev_term["datetime"].strftime("%Y-%m-%d %H:%M")},
            "next_term": {"name": next_term["name"], "datetime": next_term["datetime"].strftime("%Y-%m-%d %H:%M")},
            "pillars": pillars, "zodiac": ZODIAC[(lunar_date.year - 4) % 12],
            "day_master": day_master, "qiyun_age": int(qiyun_age), "da_yun": da_yun,
            "wu_xing_balance": _calculate_wuxing_balance(pillars),
        }
        result["summary"] = _generate_summary(result, birth_place)
        return result
    except Exception as e:
        logger.error(f"八字排盘失败: {e}")
        return {"success": False, "error": str(e), "summary": f"排盘失败: {str(e)}"}


def _calculate_year_pillar(year: int) -> str:
    return TIANGAN[(year - 4) % 10] + DIZHI[(year - 4) % 12]


def _calculate_month_pillar(year: int, month: int, is_leap: bool, prev_term: Dict) -> str:
    TERM_TO_ZHI = {"立春": 2, "雨水": 2, "惊蛰": 3, "春分": 3, "清明": 4, "谷雨": 4,
                  "立夏": 5, "小满": 5, "芒种": 6, "夏至": 6, "小暑": 7, "大暑": 7,
                  "立秋": 8, "处暑": 8, "白露": 9, "秋分": 9, "寒露": 10, "霜降": 10,
                  "立冬": 11, "小雪": 11, "大雪": 0, "冬至": 0, "小寒": 1, "大寒": 1}
    month_zhi = TERM_TO_ZHI.get(prev_term["name"])
    if month_zhi is None:
        raise ValueError(f"未知节气: {prev_term['name']}")
    year_gan_index = (year - 4) % 10
    start_gan = [2, 4, 6, 8, 0, 2, 4, 6, 8, 0][year_gan_index]
    month_offset = (month_zhi - 2 + 12) % 12
    return TIANGAN[(start_gan + month_offset) % 10] + DIZHI[month_zhi]


def _calculate_day_pillar(year: int, month: int, day: int, hour: int) -> str:
    base = datetime(1901, 2, 15)
    if hour == 23:
        day += 1
        if day > monthrange(year, month)[1]:
            day, month = 1, month + 1
            if month > 12:
                month, year = 1, year + 1
    delta = (datetime(year, month, day) - base).days
    return TIANGAN[delta % 10] + DIZHI[delta % 12]


def _calculate_hour_pillar(year: int, month: int, day: int, hour: int) -> str:
    day_gan = _calculate_day_pillar(year, month, day, hour)[0]
    hour_idx = 0 if hour == 23 else (hour + 1) // 2 % 12
    return TIANGAN[(TIANGAN.index(day_gan) % 5 * 2 + hour_idx) % 10] + DIZHI[hour_idx]


def _calculate_prev_next_solar_terms(target_date: datetime) -> Tuple[Dict, Dict]:
    terms = []
    for year_offset in range(0, 3):
        start_date = ephem.Date(datetime(target_date.year + year_offset, 1, 1, 0, 1, 1))
        for term_name, angle in SOLAR_TERMS.items():
            observer = ephem.Observer()
            observer.lat, observer.lon = "39.9", "116.4"
            observer.date = start_date
            term_date = _find_term_by_angle(observer, angle)
            terms.append({"name": term_name, "datetime": term_date.datetime() + timedelta(hours=8)})
    terms.sort(key=lambda x: x["datetime"])
    for i, term in enumerate(terms):
        if term["datetime"] > target_date:
            return terms[i - 1] if i > 0 else terms[-1], term
    raise ValueError("节气计算错误！")


def _find_term_by_angle(observer, target_angle: float):
    sun = ephem.Sun()
    step, max_iter, it = 1.0, 1080, 0
    while it < max_iter:
        sun.compute(observer)
        if sun.hlon is None:
            observer.date += step; it += 1; continue
        current_angle = (sun.hlon * 180 / ephem.pi) % 360
        angle_diff = (current_angle - target_angle + 180) % 360
        if abs(angle_diff) < 0.01:
            return observer.date
        if abs(angle_diff) > 10: step = 1.0 * (1 if angle_diff < 0 else -1)
        elif abs(angle_diff) > 1: step = 0.1 * (1 if angle_diff < 0 else -1)
        elif abs(angle_diff) > 0.033: step = 0.01 * (1 if angle_diff < 0 else -1)
        else: step = 0.001 * (1 if angle_diff < 0 else -1)
        observer.date += step; it += 1
    raise ValueError(f"未能找到节气日期（目标角度:{target_angle}°）")


def _calculate_da_yun(birth_date: datetime, gender: str, pillars: Dict, prev_term: Dict, next_term: Dict) -> List[Dict]:
    year_gan = pillars["year"]["gan"]
    is_yang_year = year_gan in ["甲", "丙", "戊", "庚", "壬"]
    reverse = (gender == "male" and is_yang_year) or (gender == "female" and not is_yang_year)
    
    if reverse:
        term_interval = (next_term["datetime"] - birth_date).total_seconds() / (24 * 3600)
    else:
        term_interval = (birth_date - prev_term["datetime"]).total_seconds() / (24 * 3600)
    
    qiyun_age = term_interval // 3 + (term_interval % 3) * 4 / 12
    day_master = pillars["day"]["gan"]
    da_yun = []
    
    for i in range(8):
        start_age = qiyun_age + i * 10
        end_age = start_age + 10 - 0.1
        month_gan_idx = TIANGAN.index(pillars["month"]["gan"])
        month_zhi_idx = DIZHI.index(pillars["month"]["zhi"])
        step = 1 if reverse else -1
        gan_zhi = TIANGAN[(month_gan_idx + step * (i + 1)) % 10] + DIZHI[(month_zhi_idx + step * (i + 1)) % 12]
        gan, zhi = gan_zhi[0], gan_zhi[1]
        
        events = [{"age": int(start_age + j), "year": birth_date.year + int(start_age + j), 
                   "gan_zhi": _calculate_year_pillar(birth_date.year + int(start_age + j))} for j in range(10)]
        
        positions = CHANG_SHENG_MAP.get(day_master, [])
        chang_sheng = CHANG_SHENG_POSITIONS[positions.index(zhi)] if zhi in positions else "未知"
        
        da_yun.append({
            "start_year": int(birth_date.year + start_age - 1), "start_age": int(start_age),
            "end_age": int(round(end_age)), "end_year": int(birth_date.year + end_age - 1),
            "gan_zhi": gan_zhi, "events": events,
            "analysis": {"position": chang_sheng, "stem": {"gan": gan, "shi_shen": SHI_SHEN_TABLE[day_master][TIANGAN.index(gan)]},
                        "branch": {"zhi": zhi, "hidden_stems": [{"gan": cg, "shi_shen": SHI_SHEN_TABLE[day_master][TIANGAN.index(cg)]} for cg in CANG_GAN[zhi]]}}
        })
    return da_yun


def _create_lunar_date(year: int, month: int, day: int, is_leap: bool):
    for d in [day] + [d for d in (30, 29) if d != day] + list(range(min(day - 1, 28), 0, -1)):
        try: return Lunar(year, month, d, is_leap)
        except: continue
    raise ValueError("Invalid lunar date")


def _get_pillar_detail(pillar: str) -> Dict:
    gan, zhi = pillar[0], pillar[1]
    return {"gan": gan, "zhi": zhi, "cang_gan": CANG_GAN[zhi].copy(),
            "na_yin": NA_YIN[TIANGAN.index(gan) % 5][DIZHI.index(zhi) % 5],
            "shi_shen": "", "wu_xing": _get_wu_xing(gan, zhi)}


def _get_wu_xing(gan: str, zhi: str) -> str:
    m = {"甲": "木", "乙": "木", "寅": "木", "卯": "木", "丙": "火", "丁": "火", "巳": "火", "午": "火",
         "戊": "土", "己": "土", "辰": "土", "戌": "土", "丑": "土", "未": "土",
         "庚": "金", "辛": "金", "申": "金", "酉": "金", "壬": "水", "癸": "水", "亥": "水", "子": "水"}
    return m.get(gan, "") + m.get(zhi, "")


def _calculate_wuxing_balance(pillars: Dict) -> Dict[str, int]:
    count = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    for p in pillars.values():
        for wx in p["wu_xing"]:
            if wx in count: count[wx] += 1
    return count


def _get_lunar_month_name(month: int) -> str:
    names = ["正月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "冬月", "腊月"]
    return names[month - 1] if 1 <= month <= 12 else ""


def _get_lunar_day_name(day: int) -> str:
    names = ["初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
             "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
             "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十"]
    return names[day - 1] if 1 <= day <= 30 else "三十"


def _generate_summary(result: Dict, birth_place: str) -> str:
    p, l, d = result["pillars"], result["lunar_date"], result["da_yun"]
    s = f"性别：{'男' if result['gender'] == 'male' else '女'}\n"
    s += f"出生地点：{birth_place}\n公历出生时间：{result['solar_date']}\n"
    s += f"农历出生时间：{p['year']['gan']}{p['year']['zhi']}年{'闰' if l['is_leap'] else ''}{l['chinese_month']}月{l['chinese_day']}日{p['hour']['zhi']}时\n"
    s += f"八字：{p['year']['gan']}{p['year']['zhi']} {p['month']['gan']}{p['month']['zhi']} {p['day']['gan']}{p['day']['zhi']} {p['hour']['gan']}{p['hour']['zhi']}\n"
    s += f"日主：{result['day_master']}\n"
    s += f"起运年龄：{result['qiyun_age']}岁\n"
    
    if d:
        # 完整大运列表
        s += "\n【大运排列】（请严格使用以下数据，不要自行推算）\n"
        cy = datetime.now().year
        current_dayun = None
        for i, dy in enumerate(d):
            marker = ""
            if dy["start_year"] <= cy < dy.get("end_year", dy["start_year"] + 10):
                current_dayun = dy
                marker = " ← 当前大运"
            s += f"  {i+1}. {dy['gan_zhi']}运（{dy['start_age']}-{dy['end_age']}岁，{dy['start_year']}-{dy.get('end_year', dy['start_year']+10)}年）{marker}\n"
        
        if current_dayun:
            s += f"\n当前所行大运：{current_dayun['gan_zhi']}运（{current_dayun['start_age']}-{current_dayun['end_age']}岁）\n"
    
    return s


__all__ = ["calculate_bazi"]
