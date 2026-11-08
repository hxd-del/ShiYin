"""滑块"点哪跳哪"的位置换算。

单独放在这里是为了不依赖 Qt：换算逻辑可以被单测覆盖，
event 分发那一层交给 ClickSlider 自己做。
"""

from __future__ import annotations


def value_at(x: float, minimum: int, maximum: int, width: int, margin: int = 7) -> int:
    """把鼠标横坐标换算成滑块值。

    margin 是手柄半径：两端各留一点，点最左边得到最小值，点最右边得到最大值。
    """
    if maximum <= minimum:
        return minimum
    span = max(1.0, float(width) - margin * 2)
    ratio = (float(x) - margin) / span
    ratio = min(1.0, max(0.0, ratio))
    return int(round(minimum + ratio * (maximum - minimum)))
