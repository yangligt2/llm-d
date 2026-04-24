import json
import os

import numpy as np
import matplotlib.pyplot as plt
import yaml

STATS = ['mean', 'min', 'max', 'p0.1', 'p1', 'p5', 'p10', 'p25', 'median', 'p75', 'p90', 'p95', 'p99', 'p99.9']

def bar_plot(ax, xvals, yvals, xtick_labels, ylabel):
    ax.bar(xvals, yvals)
    ax.set_ylabel(ylabel)
    ax.set_xticks(xvals)
    ax.set_xticklabels(xtick_labels)
    ax.set_ylim(0, )


def cdf(data):
    length = len(data)
    x = np.sort(data)
    # Get the CDF values of y
    y = (np.arange(length) + 1) / float(length)
    return x, y


def parse_qps(config_file):
    # load inference_perf config
    with open(config_file, 'r') as f:
        config = yaml.full_load(f)
    return config.get('load').get('stages')[0].get('rate')


def plot_inference_perf_report(config_file, report_file, output_dir):
    with open(report_file, 'r') as f:
        metrics = json.load(f)

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

    qps = parse_qps(config_file)
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

    plt.savefig(os.path.join(output_dir, 'benchmark_results.png'), bbox_inches='tight')


def plot_kv_transfer(kv_transfer_log, output_dir):
    prepare_time, pull_time, size = [], [], []
    with open(kv_transfer_log, 'r') as f:
        for line in f:
            _, _, _, prepare_time_str, pull_time_str, size_str = line.strip().split("|")
            prepare_time.append(float(prepare_time_str.strip().split('=')[1][:-2]))
            pull_time.append(float(pull_time_str.strip().split('=')[1][:-2]))
            size.append(float(size_str.strip().split('=')[1][:-2]))

    fig, axes = plt.subplots(2, 3, figsize=(18, 8))
    ax = axes[0, 0]
    ax.plot(*cdf(prepare_time))
    ax.set_xlabel("Prepare time (ms)")
    ax.set_ylim(0, 1)
    ax.set_ylabel("CDF")

    ax = axes[0, 1]
    ax.plot(*cdf(pull_time))
    ax.set_xlabel("Pull time (ms)")
    ax.set_ylim(0, 1)
    ax.set_ylabel("CDF")

    ax = axes[0, 2]
    ax.plot(*cdf(size))
    ax.set_xlabel("KV transfer size (MiB)")
    ax.set_ylim(0, 1)
    ax.set_ylabel("CDF")

    ax = axes[1, 0]
    ax.scatter(size, prepare_time)
    ax.set_xlabel("KV transfer size (MiB)")
    ax.set_ylabel("Prepare time (ms)")

    ax = axes[1, 1]
    ax.scatter(size, pull_time)
    ax.set_xlabel("KV transfer size (MiB)")
    ax.set_ylabel("Pull time (ms)")

    ax = axes[1, 2]

    plt.savefig(os.path.join(output_dir, 'kv_transfer.png'), bbox_inches='tight')


def main():
    report_dir = './v7x-perf-report'
    report_file = os.path.join(report_dir, 'summary_lifecycle_metrics.json')
    config_file = os.path.join(report_dir, 'config.yaml')
    kv_transfer_log = os.path.join(report_dir, 'kv_transfer.log')
    plot_inference_perf_report(config_file, report_file, report_dir)
    plot_kv_transfer(kv_transfer_log, report_dir)


if __name__ == '__main__':
    main()
