import pandas as pd
import numpy as np

# 보조지표 생성 메소드 모음

'''
이동평균
    df : 계산할 가격 데이터
    window : 이동평균일수
'''
def moving_average(df, window=5):
    return df.rolling(window=window).mean()


'''
볼린저밴드
    df : 계산할 가격 데이터
    window : 이동평균일수
    return 볼린저밴드 상단선, 볼린저 밴드 하단선
'''
def bollinger_band(df, window=20):
    ma = moving_average(df, window)
    upper_line = ma + 2 * df.rolling(window).std()
    lower_line = ma - 2 * df.rolling(window).std()
    return upper_line, lower_line

'''
RSI
    df : 계산할 가격 데이터
    period : 기간
    return rsi
'''
def rsi(df, period=14):
    # 전일 대비 변동 평균
    change = df.diff()

    # 상승한 가격과 하락한 가격
    up = change.apply(lambda x: x if x > 0 else 0)
    down = change.apply(lambda x: -x if x < 0 else 0)

    # 상승 평균과 하락 평균
    avg_up = up.ewm(alpha=1/period).mean()
    avg_down = down.ewm(alpha=1/period).mean()

    # 상대강도지수(RSI) 계산
    rs = avg_up / avg_down
    rsi = 100 - (100 / (1 + rs))
    return rsi