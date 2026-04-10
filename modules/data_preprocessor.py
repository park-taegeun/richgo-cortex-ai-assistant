import numpy as np

def filter_pir_outliers(base_series: np.ndarray, current_pir: float) -> np.ndarray:
    """
    PIR 데이터의 급격한 변동(튀는 현상)을 제어하기 위한 전처리기.
    직전 시점의 데이터(n-1) 대비 현재 값이 ±40% 이상의 상식 밖 변동을 보일 경우,
    변동폭을 최대 ±30%로 캡(Cap)을 씌워 시각적 안정성과 무결성을 확보합니다.

    Args:
        base_series (np.ndarray): n개의 시뮬레이션/시계열 데이터 배열
        current_pir (float): 배열의 마지막을 덮어쓸 현재 실제 PIR 값

    Returns:
        np.ndarray: 아웃라이어가 제거된 안정화된 시계열 배열
    """
    if len(base_series) < 2:
        return base_series

    series = base_series.copy()
    prev_value = series[-2]
    
    # 0 분모 방어
    if prev_value <= 0:
        series[-1] = current_pir
        return series

    # 변동폭 계산
    change_ratio = (current_pir - prev_value) / prev_value

    max_allowed_change = 0.30  # 최대 허용 변동폭 30%
    threshold = 0.40           # 40% 이상 시 이상치로 간주

    if change_ratio > threshold:
        # 급작스러운 폭등 -> +30%로 캡
        series[-1] = prev_value * (1 + max_allowed_change)
    elif change_ratio < -threshold:
        # 급작스러운 폭락 -> -30%로 캡
        series[-1] = prev_value * (1 - max_allowed_change)
    else:
        # 정상 범위
        series[-1] = current_pir
        
    return series
