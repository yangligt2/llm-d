import json
import numpy as np
import matplotlib.pyplot as plt

STATS = ['mean', 'min', 'max', 'p0.1', 'p1', 'p5', 'p10', 'p25', 'median', 'p75', 'p90', 'p95', 'p99', 'p99.9']

def bar_plot(ax, xvals, yvals, xtick_labels, ylabel):
    ax.bar(xvals, yvals)
    ax.set_ylabel(ylabel)
    ax.set_xticks(xvals)
    ax.set_xticklabels(xtick_labels)
    ax.set_ylim(0, )

def main():
    with open('./v7x-perf-report/summary_lifecycle_metrics.json') as f:
        metrics = json.load(f)
    # print(metrics['time_to_first_token'])
    print(metrics.keys())
    print(metrics['successes'].keys())
    # print(metrics['successes']['latency'].keys())
    # print(metrics['successes']['latency']['time_to_first_token'].keys())
    # print(metrics['successes']['latency']['request_latency'].keys())
    print(metrics['successes']['throughput'].keys())
    print(metrics['successes']['throughput']['requests_per_sec'])
    print(metrics['successes']['throughput']['input_tokens_per_sec'])
    print(metrics['successes']['throughput']['output_tokens_per_sec'])
    print(metrics['successes']['throughput']['total_tokens_per_sec'])

    req_lat = [metrics['successes']['latency']['request_latency'][stats] for stats in STATS]
    ttft = [metrics['successes']['latency']['time_to_first_token'][stats] for stats in STATS]
    tpot = [metrics['successes']['latency']['time_per_output_token'][stats] for stats in STATS]
    itl = [metrics['successes']['latency']['inter_token_latency'][stats] for stats in STATS]

    requests_per_sec = metrics['successes']['throughput']['requests_per_sec']
    input_tokens_per_sec = metrics['successes']['throughput']['input_tokens_per_sec']
    output_tokens_per_sec = metrics['successes']['throughput']['output_tokens_per_sec']
    total_tokens_per_sec = metrics['successes']['throughput']['total_tokens_per_sec']

    prompt_len = [metrics['successes']['prompt_len'][stats] for stats in STATS]
    output_len = [metrics['successes']['output_len'][stats] for stats in STATS]

    fig, axes = plt.subplots(4, 2, figsize=(15, 10))

    xtick_labels = ['p50' if stats == 'median' else stats for stats in STATS]
    xticks = np.arange(len(xtick_labels)) * 2
    bar_plot(axes[0, 0], xticks, req_lat, xtick_labels, "Request latency (s)")
    bar_plot(axes[1, 0], xticks, ttft, xtick_labels, "Time to first token (s)")
    bar_plot(axes[2, 0], xticks, tpot, xtick_labels, "Time per output token (s)")
    bar_plot(axes[3, 0], xticks, itl, xtick_labels, "Inter token latency (s)")

    qps = 1 # TODO: remove hardcode
    xtick_labels = ["Request", "Response"]
    xticks = np.arange(len(xtick_labels))
    request_tputs = [qps, requests_per_sec]
    bar_plot(axes[0, 1], xticks, request_tputs, xtick_labels, "QPS")

    xtick_labels = ["Input tokens", "Output tokens", "Total tokens"]
    xticks = np.arange(len(xtick_labels))
    token_tputs = [input_tokens_per_sec, output_tokens_per_sec, total_tokens_per_sec]
    bar_plot(axes[1, 1], xticks, token_tputs, xtick_labels, "Tokens per sec")

    xtick_labels = ['p50' if stats == 'median' else stats for stats in STATS]
    xticks = np.arange(len(xtick_labels))
    bar_plot(axes[2, 1], xticks, prompt_len, xtick_labels, "Prompt length (tokens)")
    bar_plot(axes[3, 1], xticks, output_len, xtick_labels, "Output length (tokens)")

    plt.savefig('./v7x-perf-report/benchmark_results.png')


if __name__ == '__main__':
    main()
