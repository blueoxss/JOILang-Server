import pandas as pd
import matplotlib.pyplot as plt
import platform
if platform.system() == 'Linux':
    plt.rc('font', family='NanumGothic')  # 리눅스에서 나눔고딕 사용 (설치 필요)
elif platform.system() == 'Darwin':
    plt.rc('font', family='AppleGothic')  # 맥OS
else:
    plt.rc('font', family='Malgun Gothic')  # 윈도우

plt.rcParams['axes.unicode_minus'] = False  # 마이너스 깨짐 방지

def analyze_similarity(csv_path, cols):
    df = pd.read_csv(csv_path)

    # 모든 cols를 한 번에 float으로 변환 (문자/에러값은 NaN 처리)
    df[cols] = df[cols].apply(pd.to_numeric, errors='coerce')

    # 1. 전체 유사성 점수 분포 시각화 (모든 cols를 한 그래프에)
    plt.figure(figsize=(10, 5))
    total = len(df)
    for idx, col in enumerate(cols):
        data = df[col].dropna()
        if len(data) == 0:
            print(f"컬럼 {col}은(는) 모두 숫자가 아니어서 히스토그램을 건너뜁니다.")
            continue
        counts, bins, patches = plt.hist(data, bins=20, alpha=0.7, label=col)
        for count, patch, left, right in zip(counts, patches, bins[:-1], bins[1:]):
            if count > 0:
                percent = 100 * count / total
                y_offset = max(counts) * 0.05 * (idx + 2)
                plt.text((left + right) / 2, count+y_offset, f'{percent:.1f}%', ha='center', va='bottom', fontsize=8, rotation=90)
    plt.xlabel('Similarity Score')
    plt.ylabel('Counts')
    plt.title('Similarity Score Distribution (total)')
    plt.legend()
    plt.tight_layout()
    plt.savefig('similarity_score_distribution_all.png')
    plt.close()

    # 2. 카테고리별 각 cols의 similarity 평균, max, min 그래프 (각 col별로 따로)
    if 'category_analysis' in df.columns:
        cat_col = 'category_analysis'
        # 카테고리 값을 정수로 변환 및 정렬
        categories = sorted(df[cat_col].dropna().unique(), key=lambda x: int(x))
        for col in cols:
            if not pd.api.types.is_numeric_dtype(df[col]):
                print(f"컬럼 {col}은(는) 숫자형이 아니어서 박스플롯을 건너뜁니다.")
                continue
            plt.figure(figsize=(12, 6))
            data = [df[df[cat_col] == cat][col].dropna() for cat in categories]
            plt.boxplot(data, labels=[int(cat) for cat in categories], showmeans=True)
            plt.title(f'{col} - Each Category Similarity Box Plot')
            plt.ylabel('Similarity')
            plt.xlabel('Category')
            plt.ylim(0, 1 + 0.01)  # y축 최소/최대값을 0~1로 고정
            plt.xticks(rotation=0)
            plt.tight_layout()
            plt.savefig(f'{col}_category_similarity_boxplot.png')
            plt.close()

    # 3. 전체 통계 요약 및 4. 결측값 분석 (텍스트 파일로 저장)
    stats_lines = []
    for col in cols:
        if not pd.api.types.is_numeric_dtype(df[col]):
            stats_lines.append(f'[{col}]')
            stats_lines.append('  (숫자형 데이터가 아님)')
            print(f'[{col}]')
            print('  (숫자형 데이터가 아님)')
            print()
            continue
        mean = df[col].mean()
        median = df[col].median()
        std = df[col].std()
        missing = df[col].isna().sum()
        total = len(df)
        stats_lines.append(f'[{col}]')
        stats_lines.append(f'  평균: {mean:.3f}')
        stats_lines.append(f'  중앙값: {median:.3f}')
        stats_lines.append(f'  표준편차: {std:.3f}')
        stats_lines.append(f'  결측값: {missing}개 ({missing/total*100:.1f}%)\n')
        print(f'[{col}]')
        print(f'  평균: {mean:.3f}')
        print(f'  중앙값: {median:.3f}')
        print(f'  표준편차: {std:.3f}')
        print(f'  결측값: {missing}개 ({missing/total*100:.1f}%)')
        # 결측값이 있는 경우 command 컬럼 출력
        if missing > 0 and 'command' in df.columns:
            na_commands = df[df[col].isna()]['command']
            print('  결측값 command 목록:')
            for cmd in na_commands:
                print(f'    - {cmd}')
            stats_lines.append('  결측값 command 목록:')
            for cmd in na_commands:
                stats_lines.append(f'    - {cmd}')
        print()
    with open('similarity_stats.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(stats_lines))

if __name__ == "__main__":
    csv_path = './output_merged_250630.csv'
    cols = ['cloud_similarity_gpt4o', 'cloud_similarity_gpt-4.1-mini', 'cloud_similarity_gpt-4.1_cap', 'cloud_similarity_Qwen2.5-Coder:7B', 'script_similarity_llama4:scout.dense']
    analyze_similarity(csv_path, cols)