import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("congestion.csv")

# eixo x = número da amostra
x = range(len(df))

plt.figure(figsize=(12, 6))

plt.plot(x, df["cwnd"], label="CWND")
plt.plot(x, df["ssthresh"], label="SSTHRESH")

timeout = df[df["evento"] == "timeout"]
fast = df[df["evento"] == "fast_recovery"]

plt.scatter(timeout.index, timeout["cwnd"], marker="x", s=100, label="Timeout")
plt.scatter(fast.index, fast["cwnd"], marker="o", s=80, label="Fast Recovery")

plt.xlabel("Amostra")
plt.ylabel("Janela (MSS)")
plt.title("TCP Congestion Control")

plt.grid(True)
plt.legend()

plt.show()