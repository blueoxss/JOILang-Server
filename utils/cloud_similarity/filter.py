import pandas as pd

df = pd.read_csv("./final_output_250616.csv", encoding="utf-8-sig")
df = df[df["selected"] == 1]
df.to_csv("./final_output_250616_filtered.csv", index=False, encoding="utf-8-sig")