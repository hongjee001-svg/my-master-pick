# 3. 분석 대상 종목 가져오기 (안전하게 시가총액 상위 300개 우량주만 집중 스캔)
print("📊 시장 종목 데이터를 불러옵니다...")
df_krx = fdr.StockListing('KRX')
df_krx = df_krx[df_krx['Code'].str.match(r'^\d{6}$')]
df_krx = df_krx.head(300).copy() # 2500개 -> 300개로 축소하여 에러 원천 차단 및 속도 극대화

total_count = len(df_krx)
print(f"🚀 총 {total_count}개 우량주 재무 및 모멘텀 분석 시작...")
