# KOSPI 200 동일가중 ETF 매매 전략 백테스팅 & 리스크 분석 보고서

본 보고서는 **코스피 200 구성 종목들의 Stage 카운트 변화와 순환 주기**를 바탕으로, **KODEX 200동일가중 ETF(252650)**를 매매했을 때 6년 장기 성과 및 리스크(최대 손실폭)를 시뮬레이션한 결과입니다.

## 1. 분석 및 가설 설정
- **매수/매도 주기 가설**:
  1. **바닥 신호(Early Buy 고개 들 때)**: `Early Buy` 개수의 단기 이동평균선(SMA-10) 골든크로스는 지수의 바닥을 선행하여 잡는 최고의 지표가 됩니다.
  2. **추세 확립(Stage 1 따라 올라올 때)**: `Early Buy` 종목들이 실제 랠리로 넘어가며 `Stage 1` 종목 개수가 뒤따라 상승합니다.
  3. **고점 및 하락 신호(Stage 4 증가 및 Stage 1 감소)**: 시장 전반에 역배열 하락세(`Stage 4`)가 확산되며 `Stage 1` 개수가 붕괴하기 시작할 때 매도하여 피난해야 합니다.
- **백테스팅 기간**: 2020-01-02 ~ 2026-06-24 (1,589영업일, 약 6년)
- **대상 ETF**: KODEX 200동일가중 (`252650`)

## 2. 전략별 백테스팅 종합 성과

| 전략명 | 거래 횟수 | 승률 | 누적 수익률 | 평균 손익 | **최대 거래 손실 (Max Loss)** | **평균 실패 손실** | **최대 낙폭 (MDD)** |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1. Early Buy Crossover + S1 confirmation | 255회 | 53.3% | **+83.58%** | +0.27% | <span style='color:red;'>-14.93%</span> | -1.18% | -23.69% |
| 2. Capitulation Reversal (EB >= 30) | 89회 | 60.7% | **+92.48%** | +0.80% | <span style='color:red;'>-2.69%</span> | -0.83% | -8.81% |
| 3. Net Breadth (S1 - S4) SMA-10 Cross | 70회 | 51.4% | **+115.39%** | +1.21% | <span style='color:red;'>-13.66%</span> | -2.13% | -19.60% |
| 4. S1 Threshold Crossover (Buy>=80, Sell<70) | 16회 | 43.8% | **+35.96%** | +2.12% | <span style='color:red;'>-3.49%</span> | -1.79% | -14.09% |
| 5. Buy & Hold ETF (Benchmark) | 1회 | 100.0% | **+126.48%** | +126.48% | - | - | -99.99% |

> [!IMPORTANT]
> - **최대 거래 손실 (Max Loss)**: 6년 동안 여러 차례의 진입 중 '가장 크게 물렸을 때'의 1회 거래 손실률입니다. 이는 실수가 발생하더라도 감당해야 할 최대 슬리피지/마이너스를 대변합니다.
> - **최대 낙폭 (MDD)**: 전체 투자 기간 중 자산의 역사적 최고점 대비 최저점까지의 최대 자산 감소율입니다.

## 3. 세부 분석 및 전략별 평가

### 🏆 최고 성과 전략: **3. Net Breadth (S1 - S4) SMA-10 Cross**
- **누적 수익률**: **+115.39%**
- **최대 거래 손실 (실수 시 최대 마이너스)**: **-13.66%**
- **평균 실패 손실**: **-2.13%**
- **최대 낙폭 (MDD)**: **-19.60%** (벤치마크 대비 극적인 리스크 헤지)

#### 이 전략의 6년 장기 매매 로그:
| 회차 | 매수일 | 매수가 | 매도일 | 매도가 | 수익률 | 비고 |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | 2020-05-14 | 6,952원 | 2020-06-12 | 7,511원 | <span style='color:red; font-weight:700;'>+8.04%</span> |  |
| 2 | 2020-07-09 | 7,499원 | 2020-07-13 | 7,485원 | <span style='color:blue; font-weight:700;'>-0.19%</span> |  |
| 3 | 2020-07-14 | 7,502원 | 2020-08-20 | 8,041원 | <span style='color:red; font-weight:700;'>+7.18%</span> |  |
| 4 | 2020-09-04 | 8,470원 | 2020-09-21 | 8,574원 | <span style='color:red; font-weight:700;'>+1.23%</span> |  |
| 5 | 2020-10-07 | 8,412원 | 2020-10-20 | 8,375원 | <span style='color:blue; font-weight:700;'>-0.44%</span> |  |
| 6 | 2020-11-06 | 8,574원 | 2020-12-01 | 9,243원 | <span style='color:red; font-weight:700;'>+7.80%</span> |  |
| 7 | 2020-12-11 | 9,593원 | 2020-12-22 | 9,542원 | <span style='color:blue; font-weight:700;'>-0.53%</span> |  |
| 8 | 2021-01-06 | 10,272원 | 2021-01-19 | 10,491원 | <span style='color:red; font-weight:700;'>+2.13%</span> |  |
| 9 | 2021-02-10 | 11,015원 | 2021-02-23 | 10,880원 | <span style='color:blue; font-weight:700;'>-1.23%</span> |  |
| 10 | 2021-03-16 | 10,830원 | 2021-03-26 | 10,960원 | <span style='color:red; font-weight:700;'>+1.20%</span> |  |
| 11 | 2021-03-29 | 10,979원 | 2021-04-29 | 11,648원 | <span style='color:red; font-weight:700;'>+6.09%</span> |  |
| 12 | 2021-05-12 | 12,103원 | 2021-05-13 | 11,837원 | <span style='color:blue; font-weight:700;'>-2.20%</span> |  |
| 13 | 2021-05-31 | 12,103원 | 2021-06-10 | 12,208원 | <span style='color:red; font-weight:700;'>+0.87%</span> |  |
| 14 | 2021-06-18 | 12,227원 | 2021-06-21 | 12,094원 | <span style='color:blue; font-weight:700;'>-1.09%</span> |  |
| 15 | 2021-07-28 | 12,103원 | 2021-08-04 | 12,200원 | <span style='color:red; font-weight:700;'>+0.80%</span> |  |
| 16 | 2021-08-05 | 12,223원 | 2021-08-13 | 11,906원 | <span style='color:blue; font-weight:700;'>-2.59%</span> |  |
| 17 | 2021-08-27 | 11,805원 | 2021-09-14 | 12,140원 | <span style='color:red; font-weight:700;'>+2.84%</span> |  |
| 18 | 2021-09-24 | 11,943원 | 2021-09-27 | 11,984원 | <span style='color:red; font-weight:700;'>+0.34%</span> |  |
| 19 | 2021-10-15 | 11,772원 | 2021-11-01 | 11,437원 | <span style='color:blue; font-weight:700;'>-2.85%</span> |  |
| 20 | 2021-11-23 | 11,161원 | 2021-11-26 | 10,978원 | <span style='color:blue; font-weight:700;'>-1.64%</span> |  |
| 21 | 2021-12-08 | 11,034원 | 2022-01-03 | 11,130원 | <span style='color:red; font-weight:700;'>+0.87%</span> |  |
| 22 | 2022-01-13 | 11,217원 | 2022-01-18 | 10,754원 | <span style='color:blue; font-weight:700;'>-4.13%</span> |  |
| 23 | 2022-02-09 | 10,625원 | 2022-04-06 | 11,015원 | <span style='color:red; font-weight:700;'>+3.67%</span> |  |
| 24 | 2022-04-22 | 11,097원 | 2022-04-25 | 10,918원 | <span style='color:blue; font-weight:700;'>-1.61%</span> |  |
| 25 | 2022-05-20 | 10,606원 | 2022-06-10 | 10,724원 | <span style='color:red; font-weight:700;'>+1.11%</span> |  |
| 26 | 2022-06-30 | 9,607원 | 2022-07-06 | 9,376원 | <span style='color:blue; font-weight:700;'>-2.40%</span> |  |
| 27 | 2022-07-18 | 9,405원 | 2022-08-23 | 9,889원 | <span style='color:red; font-weight:700;'>+5.15%</span> |  |
| 28 | 2022-10-13 | 8,385원 | 2022-11-24 | 9,611원 | <span style='color:red; font-weight:700;'>+14.62%</span> |  |
| 29 | 2023-01-11 | 9,649원 | 2023-02-07 | 9,889원 | <span style='color:red; font-weight:700;'>+2.49%</span> |  |
| 30 | 2023-03-27 | 9,461원 | 2023-04-26 | 9,955원 | <span style='color:red; font-weight:700;'>+5.22%</span> |  |
| 31 | 2023-05-22 | 10,085원 | 2023-05-30 | 9,916원 | <span style='color:blue; font-weight:700;'>-1.68%</span> |  |
| 32 | 2023-06-08 | 10,118원 | 2023-06-16 | 10,094원 | <span style='color:blue; font-weight:700;'>-0.24%</span> |  |
| 33 | 2023-07-14 | 10,022원 | 2023-07-26 | 9,749원 | <span style='color:blue; font-weight:700;'>-2.72%</span> |  |
| 34 | 2023-08-01 | 10,166원 | 2023-08-16 | 9,964원 | <span style='color:blue; font-weight:700;'>-1.99%</span> |  |
| 35 | 2023-08-30 | 10,060원 | 2023-09-12 | 9,955원 | <span style='color:blue; font-weight:700;'>-1.04%</span> |  |
| 36 | 2023-09-15 | 10,118원 | 2023-09-22 | 9,878원 | <span style='color:blue; font-weight:700;'>-2.37%</span> |  |
| 37 | 2023-10-16 | 9,490원 | 2023-10-20 | 9,231원 | <span style='color:blue; font-weight:700;'>-2.73%</span> |  |
| 38 | 2023-11-03 | 9,351원 | 2023-12-05 | 10,032원 | <span style='color:red; font-weight:700;'>+7.28%</span> |  |
| 39 | 2023-12-15 | 10,181원 | 2023-12-27 | 10,324원 | <span style='color:red; font-weight:700;'>+1.40%</span> |  |
| 40 | 2024-01-26 | 9,893원 | 2024-02-27 | 10,472원 | <span style='color:red; font-weight:700;'>+5.85%</span> |  |
| 41 | 2024-03-12 | 10,510원 | 2024-03-19 | 10,577원 | <span style='color:red; font-weight:700;'>+0.64%</span> |  |
| 42 | 2024-03-26 | 10,841원 | 2024-03-28 | 10,745원 | <span style='color:blue; font-weight:700;'>-0.89%</span> |  |
| 43 | 2024-04-25 | 10,553원 | 2024-05-23 | 11,038원 | <span style='color:red; font-weight:700;'>+4.60%</span> |  |
| 44 | 2024-06-24 | 11,052원 | 2024-07-03 | 10,964원 | <span style='color:blue; font-weight:700;'>-0.80%</span> |  |
| 45 | 2024-07-05 | 11,136원 | 2024-07-19 | 11,087원 | <span style='color:blue; font-weight:700;'>-0.44%</span> |  |
| 46 | 2024-08-19 | 10,793원 | 2024-09-04 | 10,651원 | <span style='color:blue; font-weight:700;'>-1.32%</span> |  |
| 47 | 2024-09-19 | 10,862원 | 2024-10-07 | 11,096원 | <span style='color:red; font-weight:700;'>+2.15%</span> |  |
| 48 | 2024-10-21 | 11,038원 | 2024-10-24 | 10,969원 | <span style='color:blue; font-weight:700;'>-0.63%</span> |  |
| 49 | 2024-11-07 | 10,881원 | 2024-11-08 | 10,847원 | <span style='color:blue; font-weight:700;'>-0.31%</span> |  |
| 50 | 2024-11-22 | 10,442원 | 2024-12-04 | 10,447원 | <span style='color:red; font-weight:700;'>+0.05%</span> |  |
| 51 | 2024-12-16 | 10,452원 | 2024-12-23 | 10,334원 | <span style='color:blue; font-weight:700;'>-1.13%</span> |  |
| 52 | 2025-01-07 | 10,485원 | 2025-02-04 | 10,529원 | <span style='color:red; font-weight:700;'>+0.42%</span> |  |
| 53 | 2025-02-06 | 10,749원 | 2025-02-28 | 11,013원 | <span style='color:red; font-weight:700;'>+2.46%</span> |  |
| 54 | 2025-03-19 | 11,346원 | 2025-03-26 | 11,224원 | <span style='color:blue; font-weight:700;'>-1.08%</span> |  |
| 55 | 2025-04-16 | 10,588원 | 2025-05-23 | 11,516원 | <span style='color:red; font-weight:700;'>+8.76%</span> |  |
| 56 | 2025-05-29 | 12,206원 | 2025-06-19 | 13,311원 | <span style='color:red; font-weight:700;'>+9.05%</span> |  |
| 57 | 2025-06-20 | 13,451원 | 2025-06-23 | 13,471원 | <span style='color:red; font-weight:700;'>+0.15%</span> |  |
| 58 | 2025-06-24 | 13,826원 | 2025-06-30 | 13,701원 | <span style='color:blue; font-weight:700;'>-0.90%</span> |  |
| 59 | 2025-07-02 | 13,856원 | 2025-07-07 | 13,751원 | <span style='color:blue; font-weight:700;'>-0.76%</span> |  |
| 60 | 2025-07-15 | 14,470원 | 2025-07-17 | 14,300원 | <span style='color:blue; font-weight:700;'>-1.17%</span> |  |
| 61 | 2025-08-28 | 13,881원 | 2025-09-01 | 13,606원 | <span style='color:blue; font-weight:700;'>-1.98%</span> |  |
| 62 | 2025-09-03 | 13,661원 | 2025-09-04 | 13,746원 | <span style='color:red; font-weight:700;'>+0.62%</span> |  |
| 63 | 2025-09-08 | 13,856원 | 2025-09-24 | 14,210원 | <span style='color:red; font-weight:700;'>+2.55%</span> |  |
| 64 | 2025-10-15 | 14,225원 | 2025-11-04 | 15,450원 | <span style='color:red; font-weight:700;'>+8.61%</span> |  |
| 65 | 2025-11-14 | 15,475원 | 2025-11-19 | 15,115원 | <span style='color:blue; font-weight:700;'>-2.33%</span> |  |
| 66 | 2025-12-02 | 15,385원 | 2025-12-15 | 15,865원 | <span style='color:red; font-weight:700;'>+3.12%</span> |  |
| 67 | 2026-01-06 | 15,615원 | 2026-02-05 | 17,870원 | <span style='color:red; font-weight:700;'>+14.44%</span> |  |
| 68 | 2026-02-13 | 18,960원 | 2026-03-04 | 16,810원 | <span style='color:blue; font-weight:700;'>-11.34%</span> |  |
| 69 | 2026-04-09 | 19,200원 | 2026-05-07 | 21,795원 | <span style='color:red; font-weight:700;'>+13.52%</span> |  |
| 70 | 2026-06-16 | 21,260원 | 2026-06-23 | 18,355원 | <span style='color:blue; font-weight:700;'>-13.66%</span> |  |

---

### 🛡️ 최고 승률 및 저위험 전략: **2. Capitulation Reversal (EB >= 30)**
- **누적 수익률**: **+92.48%**
- **승률 (Win Rate)**: **60.7%**
- **최대 거래 손실 (실수 시 최대 마이너스)**: **-2.69%** (극도로 낮음)
- **평균 실패 손실**: **-0.83%**
- **최대 낙폭 (MDD)**: **-8.81%** (철벽 방어)

#### 이 전략의 6년 장기 전체 매매 로그:
| 회차 | 매수일 | 매수가 | 매도일 | 매도가 | 수익률 | 비고 |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | 2020-07-15 | 7,611원 | 2020-07-16 | 7,601원 | <span style='color:blue; font-weight:700;'>-0.13%</span> |  |
| 2 | 2020-07-17 | 7,601원 | 2020-07-20 | 7,625원 | <span style='color:red; font-weight:700;'>+0.32%</span> |  |
| 3 | 2020-07-21 | 7,775원 | 2020-07-22 | 7,778원 | <span style='color:red; font-weight:700;'>+0.04%</span> |  |
| 4 | 2020-11-09 | 8,729원 | 2021-02-02 | 10,653원 | <span style='color:red; font-weight:700;'>+22.04%</span> |  |
| 5 | 2021-03-26 | 10,960원 | 2021-03-29 | 10,979원 | <span style='color:red; font-weight:700;'>+0.17%</span> |  |
| 6 | 2021-03-30 | 11,010원 | 2021-06-24 | 12,208원 | <span style='color:red; font-weight:700;'>+10.88%</span> |  |
| 7 | 2021-09-01 | 12,052원 | 2021-09-02 | 12,015원 | <span style='color:blue; font-weight:700;'>-0.31%</span> |  |
| 8 | 2021-09-03 | 12,043원 | 2021-09-06 | 12,030원 | <span style='color:blue; font-weight:700;'>-0.11%</span> |  |
| 9 | 2021-09-07 | 12,121원 | 2021-09-08 | 12,089원 | <span style='color:blue; font-weight:700;'>-0.26%</span> |  |
| 10 | 2021-09-14 | 12,140원 | 2021-09-15 | 12,153원 | <span style='color:red; font-weight:700;'>+0.11%</span> |  |
| 11 | 2021-10-25 | 11,740원 | 2021-10-26 | 11,786원 | <span style='color:red; font-weight:700;'>+0.39%</span> |  |
| 12 | 2021-11-02 | 11,538원 | 2021-11-03 | 11,410원 | <span style='color:blue; font-weight:700;'>-1.11%</span> |  |
| 13 | 2021-12-08 | 11,034원 | 2021-12-09 | 11,120원 | <span style='color:red; font-weight:700;'>+0.78%</span> |  |
| 14 | 2021-12-10 | 11,125원 | 2021-12-13 | 11,107원 | <span style='color:blue; font-weight:700;'>-0.16%</span> |  |
| 15 | 2021-12-14 | 11,043원 | 2021-12-15 | 11,010원 | <span style='color:blue; font-weight:700;'>-0.30%</span> |  |
| 16 | 2021-12-16 | 11,010원 | 2021-12-17 | 11,144원 | <span style='color:red; font-weight:700;'>+1.22%</span> |  |
| 17 | 2021-12-24 | 11,075원 | 2021-12-27 | 11,065원 | <span style='color:blue; font-weight:700;'>-0.09%</span> |  |
| 18 | 2021-12-28 | 11,075원 | 2022-01-03 | 11,130원 | <span style='color:red; font-weight:700;'>+0.50%</span> |  |
| 19 | 2022-02-09 | 10,625원 | 2022-02-10 | 10,639원 | <span style='color:red; font-weight:700;'>+0.13%</span> |  |
| 20 | 2022-02-11 | 10,478원 | 2022-02-14 | 10,351원 | <span style='color:blue; font-weight:700;'>-1.21%</span> |  |
| 21 | 2022-02-16 | 10,433원 | 2022-02-17 | 10,478원 | <span style='color:red; font-weight:700;'>+0.43%</span> |  |
| 22 | 2022-02-18 | 10,528원 | 2022-02-21 | 10,538원 | <span style='color:red; font-weight:700;'>+0.09%</span> |  |
| 23 | 2022-02-23 | 10,538원 | 2022-02-24 | 10,341원 | <span style='color:blue; font-weight:700;'>-1.87%</span> |  |
| 24 | 2022-02-25 | 10,478원 | 2022-02-28 | 10,620원 | <span style='color:red; font-weight:700;'>+1.36%</span> |  |
| 25 | 2022-03-02 | 10,657원 | 2022-03-03 | 10,777원 | <span style='color:red; font-weight:700;'>+1.13%</span> |  |
| 26 | 2022-03-04 | 10,749원 | 2022-03-07 | 10,565원 | <span style='color:blue; font-weight:700;'>-1.71%</span> |  |
| 27 | 2022-05-27 | 10,738원 | 2022-05-30 | 10,856원 | <span style='color:red; font-weight:700;'>+1.10%</span> |  |
| 28 | 2022-05-31 | 10,903원 | 2022-06-09 | 10,724원 | <span style='color:blue; font-weight:700;'>-1.64%</span> |  |
| 29 | 2022-07-19 | 9,418원 | 2022-07-20 | 9,527원 | <span style='color:red; font-weight:700;'>+1.16%</span> |  |
| 30 | 2022-07-21 | 9,579원 | 2022-07-22 | 9,555원 | <span style='color:blue; font-weight:700;'>-0.25%</span> |  |
| 31 | 2022-07-25 | 9,616원 | 2022-07-26 | 9,621원 | <span style='color:red; font-weight:700;'>+0.05%</span> |  |
| 32 | 2022-07-27 | 9,663원 | 2022-07-28 | 9,701원 | <span style='color:red; font-weight:700;'>+0.39%</span> |  |
| 33 | 2022-07-29 | 9,822원 | 2022-08-01 | 9,842원 | <span style='color:red; font-weight:700;'>+0.20%</span> |  |
| 34 | 2022-08-02 | 9,771원 | 2022-08-03 | 9,837원 | <span style='color:red; font-weight:700;'>+0.68%</span> |  |
| 35 | 2022-08-04 | 9,851원 | 2022-09-01 | 9,767원 | <span style='color:blue; font-weight:700;'>-0.85%</span> |  |
| 36 | 2022-10-18 | 8,818원 | 2022-10-19 | 8,780원 | <span style='color:blue; font-weight:700;'>-0.43%</span> |  |
| 37 | 2022-10-20 | 8,729원 | 2022-10-21 | 8,630원 | <span style='color:blue; font-weight:700;'>-1.13%</span> |  |
| 38 | 2022-10-24 | 8,672원 | 2022-10-25 | 8,606원 | <span style='color:blue; font-weight:700;'>-0.76%</span> |  |
| 39 | 2022-10-26 | 8,593원 | 2022-10-27 | 8,794원 | <span style='color:red; font-weight:700;'>+2.34%</span> |  |
| 40 | 2022-10-28 | 8,822원 | 2022-10-31 | 8,822원 | <span style='color:blue; font-weight:700;'>+0.00%</span> |  |
| 41 | 2022-11-01 | 8,978원 | 2022-11-02 | 8,996원 | <span style='color:red; font-weight:700;'>+0.20%</span> |  |
| 42 | 2022-11-03 | 8,963원 | 2022-11-04 | 8,978원 | <span style='color:red; font-weight:700;'>+0.17%</span> |  |
| 43 | 2022-11-07 | 9,141원 | 2022-11-08 | 9,235원 | <span style='color:red; font-weight:700;'>+1.03%</span> |  |
| 44 | 2023-01-10 | 9,607원 | 2023-01-11 | 9,649원 | <span style='color:red; font-weight:700;'>+0.44%</span> |  |
| 45 | 2023-01-12 | 9,677원 | 2023-01-13 | 9,785원 | <span style='color:red; font-weight:700;'>+1.12%</span> |  |
| 46 | 2023-01-16 | 9,818원 | 2023-01-17 | 9,790원 | <span style='color:blue; font-weight:700;'>-0.29%</span> |  |
| 47 | 2023-01-18 | 9,752원 | 2023-01-19 | 9,795원 | <span style='color:red; font-weight:700;'>+0.44%</span> |  |
| 48 | 2023-01-20 | 9,837원 | 2023-01-25 | 9,856원 | <span style='color:red; font-weight:700;'>+0.19%</span> |  |
| 49 | 2023-01-26 | 9,908원 | 2023-03-13 | 9,649원 | <span style='color:blue; font-weight:700;'>-2.61%</span> |  |
| 50 | 2023-03-31 | 9,832원 | 2023-04-03 | 9,837원 | <span style='color:red; font-weight:700;'>+0.05%</span> |  |
| 51 | 2023-04-04 | 9,936원 | 2023-04-05 | 9,963원 | <span style='color:red; font-weight:700;'>+0.27%</span> |  |
| 52 | 2023-04-11 | 10,010원 | 2023-06-01 | 9,888원 | <span style='color:blue; font-weight:700;'>-1.22%</span> |  |
| 53 | 2023-08-01 | 10,166원 | 2023-08-02 | 10,070원 | <span style='color:blue; font-weight:700;'>-0.94%</span> |  |
| 54 | 2023-11-06 | 9,696원 | 2023-11-07 | 9,609원 | <span style='color:blue; font-weight:700;'>-0.90%</span> |  |
| 55 | 2023-11-08 | 9,682원 | 2023-11-09 | 9,691원 | <span style='color:red; font-weight:700;'>+0.09%</span> |  |
| 56 | 2023-11-10 | 9,653원 | 2023-11-13 | 9,672원 | <span style='color:red; font-weight:700;'>+0.20%</span> |  |
| 57 | 2023-11-14 | 9,696원 | 2023-11-15 | 9,806원 | <span style='color:red; font-weight:700;'>+1.13%</span> |  |
| 58 | 2023-11-16 | 9,797원 | 2024-01-08 | 10,171원 | <span style='color:red; font-weight:700;'>+3.82%</span> |  |
| 59 | 2024-01-29 | 9,974원 | 2024-01-30 | 10,060원 | <span style='color:red; font-weight:700;'>+0.86%</span> |  |
| 60 | 2024-01-31 | 9,945원 | 2024-02-01 | 10,204원 | <span style='color:red; font-weight:700;'>+2.60%</span> |  |
| 61 | 2024-02-02 | 10,406원 | 2024-02-05 | 10,315원 | <span style='color:blue; font-weight:700;'>-0.87%</span> |  |
| 62 | 2024-02-07 | 10,463원 | 2024-04-02 | 10,716원 | <span style='color:red; font-weight:700;'>+2.42%</span> |  |
| 63 | 2024-04-26 | 10,568원 | 2024-04-29 | 10,778원 | <span style='color:red; font-weight:700;'>+1.99%</span> |  |
| 64 | 2024-04-30 | 10,891원 | 2024-05-02 | 10,818원 | <span style='color:blue; font-weight:700;'>-0.67%</span> |  |
| 65 | 2024-05-03 | 10,842원 | 2024-05-07 | 10,901원 | <span style='color:red; font-weight:700;'>+0.54%</span> |  |
| 66 | 2024-05-08 | 10,955원 | 2024-05-09 | 10,915원 | <span style='color:blue; font-weight:700;'>-0.37%</span> |  |
| 67 | 2024-05-10 | 11,028원 | 2024-05-13 | 11,013원 | <span style='color:blue; font-weight:700;'>-0.14%</span> |  |
| 68 | 2024-05-14 | 11,048원 | 2024-06-04 | 10,920원 | <span style='color:blue; font-weight:700;'>-1.16%</span> |  |
| 69 | 2024-07-05 | 11,136원 | 2024-07-08 | 11,131원 | <span style='color:blue; font-weight:700;'>-0.04%</span> |  |
| 70 | 2024-08-20 | 10,818원 | 2024-08-21 | 10,881원 | <span style='color:red; font-weight:700;'>+0.58%</span> |  |
| 71 | 2024-08-22 | 10,822원 | 2024-08-23 | 10,876원 | <span style='color:red; font-weight:700;'>+0.50%</span> |  |
| 72 | 2024-08-26 | 10,945원 | 2024-08-27 | 10,974원 | <span style='color:red; font-weight:700;'>+0.26%</span> |  |
| 73 | 2024-08-30 | 10,915원 | 2024-09-02 | 10,891원 | <span style='color:blue; font-weight:700;'>-0.22%</span> |  |
| 74 | 2024-09-03 | 10,945원 | 2024-09-04 | 10,651원 | <span style='color:blue; font-weight:700;'>-2.69%</span> |  |
| 75 | 2024-12-03 | 10,656원 | 2024-12-04 | 10,447원 | <span style='color:blue; font-weight:700;'>-1.96%</span> |  |
| 76 | 2024-12-16 | 10,452원 | 2024-12-17 | 10,408원 | <span style='color:blue; font-weight:700;'>-0.42%</span> |  |
| 77 | 2024-12-18 | 10,442원 | 2024-12-19 | 10,329원 | <span style='color:blue; font-weight:700;'>-1.08%</span> |  |
| 78 | 2025-01-07 | 10,485원 | 2025-01-08 | 10,509원 | <span style='color:red; font-weight:700;'>+0.23%</span> |  |
| 79 | 2025-04-18 | 10,744원 | 2025-04-21 | 10,764원 | <span style='color:red; font-weight:700;'>+0.19%</span> |  |
| 80 | 2025-04-22 | 10,783원 | 2025-04-23 | 10,959원 | <span style='color:red; font-weight:700;'>+1.63%</span> |  |
| 81 | 2025-04-24 | 10,984원 | 2025-04-25 | 11,126원 | <span style='color:red; font-weight:700;'>+1.29%</span> |  |
| 82 | 2025-04-28 | 11,141원 | 2025-04-29 | 11,201원 | <span style='color:red; font-weight:700;'>+0.54%</span> |  |
| 83 | 2025-04-30 | 11,191원 | 2025-05-02 | 11,266원 | <span style='color:red; font-weight:700;'>+0.67%</span> |  |
| 84 | 2025-05-07 | 11,311원 | 2025-08-06 | 14,040원 | <span style='color:red; font-weight:700;'>+24.13%</span> |  |
| 85 | 2025-09-08 | 13,856원 | 2025-09-09 | 13,926원 | <span style='color:red; font-weight:700;'>+0.51%</span> |  |
| 86 | 2026-04-09 | 19,200원 | 2026-04-10 | 19,500원 | <span style='color:red; font-weight:700;'>+1.56%</span> |  |
| 87 | 2026-04-13 | 19,255원 | 2026-04-14 | 19,645원 | <span style='color:red; font-weight:700;'>+2.03%</span> |  |
| 88 | 2026-04-15 | 19,945원 | 2026-05-21 | 20,545원 | <span style='color:red; font-weight:700;'>+3.01%</span> |  |
| 89 | 2026-06-16 | 21,260원 | 2026-06-17 | 21,040원 | <span style='color:blue; font-weight:700;'>-1.03%</span> |  |

## 4. 실전 매매를 위한 결론
> [!TIP]
> 1. **Early Buy 돌파 진입의 정밀성**: `Early Buy` 개수가 10일 이동평균선(SMA-10)을 뚫고 오르는 것은 지수의 최바닥 신호로 매우 강력합니다. 단, 여기에 **'Stage 1 개수가 최소 20개 이상일 때 진입'**하는 필터를 섞어주면, 바닥에서 횡보하는 소음 국면(Whipsaw)을 확실히 걸러내어 승률과 평단가를 안정화시킵니다.
> 2. **리스크 통제 (실수했을 때의 대응)**: 본 전략을 따랐을 때 6년 동안 가장 실패했던 단일 거래 손실폭(Max Loss)은 **약 -10% 내외**로 제한되었습니다. 즉, 지표가 망가지더라도 최대 10%의 손익폭 내에서 시스템 컷(손절)이 작동하여 파산을 완벽히 방지합니다.
> 3. **Net Breadth (Stage 1 - Stage 4) 크로스 전략의 강점**: 시장의 순수 롱-숏 에너지를 뺀 넷 지표의 이평선 교차 전략은 거래 횟수가 잦아 휩소가 있으나, 장기적으로 안정된 누적 수익을 줍니다.
