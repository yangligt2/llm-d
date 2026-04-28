import datetime
import json
import os
import re

import numpy as np
import matplotlib.pyplot as plt
import yaml

STATS = ['mean', 'min', 'p0.1', 'p1', 'p5', 'p10', 'p25', 'median', 'p75', 'p90', 'p95', 'p99', 'p99.9', 'max']

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
    # Regex to find the date and time pattern (MM-DD HH:MM:SS)
    regex = r"(\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
    ts, prepare_time, pull_time, size = [], [], [], []
    with open(kv_transfer_log, 'r') as f:
        for line in f:
            print(line)
            prefix, _, _, prepare_time_str, pull_time_str, size_str = line.strip().split("|")
            prepare_time.append(float(prepare_time_str.strip().split('=')[1][:-2]))
            pull_time.append(float(pull_time_str.strip().split('=')[1][:-2]))
            size.append(float(size_str.strip().split('=')[1][:-2]))

            match = re.search(regex, prefix)
            if match:
                full_timestamp = match.group(1)
                    # Assume the current year from the user request date

                # Prepend the year to the string
                year = 2026
                full_timestamp_str = f"{year}-{full_timestamp}"
                print(f"Full Timestamp String with Year: {full_timestamp_str}")

                # Define the format
                # %Y - Year with century
                # %m - Month as a zero-padded decimal number
                # %d - Day of the month as a zero-padded decimal number
                # %H - Hour (24-hour clock) as a zero-padded decimal number
                # %M - Minute as a zero-padded decimal number
                # %S - Second as a zero-padded decimal number
                date_format = "%Y-%m-%d %H:%M:%S"

                # Parse the string into a datetime object
                datetime_obj = datetime.datetime.strptime(full_timestamp_str, date_format)
                ts.append(datetime_obj)
    assert len(ts) == len(prepare_time)
    assert len(ts) == len(pull_time)
    assert len(ts) == len(size)

    fig, axes = plt.subplots(2, 2, figsize=(18, 8))
    ax = axes[0, 0]
    ax.plot(*cdf(prepare_time), label="Prepare time")
    ax.plot(*cdf(pull_time), label="Pull time")
    ax.set_xlabel("Time (ms)")
    ax.set_ylim(0, 1)
    ax.set_ylabel("CDF")
    ax.legend()

    ax = axes[0, 1]
    ax.plot(*cdf(size))
    ax.set_xlabel("KV transfer size (MiB)")
    ax.set_ylim(0, 1)
    ax.set_ylabel("CDF")

    ax = axes[1, 0]
    ax.scatter(size, prepare_time)
    ax.set_xlabel("KV transfer size (MiB)")
    ax.set_ylabel("Prepare time (ms)")

    ax = axes[1, 1]
    ax.scatter(size, pull_time, color="C1")
    ax.set_xlabel("KV transfer size (MiB)")
    ax.set_ylabel("Pull time (ms)")

    plt.savefig(os.path.join(output_dir, 'kv_transfer_dist.png'), bbox_inches='tight')

    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)

    xvals = [(t - ts[0]).total_seconds() for t in ts]

    ax = axes[0]
    ax.plot(xvals, size, '.-')
    ax.set_ylabel('KV Size (MiB)')
    ax = axes[1]
    ax.plot(xvals, pull_time, '.-')
    ax.set_ylabel('Pull time (ms)')
    ax = axes[2]
    ax.plot(xvals, prepare_time, '.-')
    ax.set_xlim(0, )
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Prepare time (ms)')

    plt.savefig(os.path.join(output_dir, 'kv_transfer_time_series.png'), bbox_inches='tight')

def plot_stress_nic(output_dir):
    stats = ['mean', 'min', 'p1', 'p10', 'p50', 'max']
    # single nic, 1 client, 1MiB request, 1KiB response, 8 tcp flows, 4 threads
    # ms-pd-llm-d-modelservice-prefill-7b4d86cd4c-dkg8k --- (1MiB) --> ms-pd-llm-d-modelservice-decode-5f54bc9fb5-nt2wv
    # ms-pd-llm-d-modelservice-prefill-7b4d86cd4c-dkg8k <-- (1KiB) --- ms-pd-llm-d-modelservice-decode-5f54bc9fb5-nt2wv
    # tcp server recv rate, count: 98, min/avg/max: 142/159/175, p50/p90/p99: 159/148/142 Gbps
    # tcp client recv rate, count: 98, min/avg/max: 138/154/170, p50/p90/p99: 154/144/138 Mbps
    tcp_rr_rates_8f_4t = [159, 142, 142 ,148, 159, 175]

    # single nic, 1 client, 1MiB request, 1KiB response, 16 tcp flows, 8 threads
    # ms-pd-llm-d-modelservice-prefill-7b4d86cd4c-dkg8k --- (1MiB) --> ms-pd-llm-d-modelservice-decode-5f54bc9fb5-nt2wv
    # ms-pd-llm-d-modelservice-prefill-7b4d86cd4c-dkg8k <-- (1KiB) --- ms-pd-llm-d-modelservice-decode-5f54bc9fb5-nt2wv
    # tcp server recv rate, count: 98, min/avg/max: 187/189/191, p50/p90/p99: 189/188/187 Gbps
    # tcp client recv rate, count: 98, min/avg/max: 182/184/186, p50/p90/p99: 185/183/182 Mbps
    tcp_rr_rates_16f_8t = [189, 187, 187 ,188, 189, 191]

    # jnt 8 tcp flows, H2H
    # ms-pd-llm-d-modelservice-prefill-7b4d86cd4c-dkg8k --- (1MiB) --> ms-pd-llm-d-modelservice-decode-5f54bc9fb5-nt2wv
    # ms-pd-llm-d-modelservice-prefill-7b4d86cd4c-dkg8k <-- (1KiB) --- ms-pd-llm-d-modelservice-decode-5f54bc9fb5-nt2wv
    # jnt server recv rate, count: 58, min/avg/max: 99/104/108, p50/p90/p99: 104/102/99 Gbps
    # jnt client recv rate, count: 0, min/avg/max: 0/0/0, p50/p90/p99: 0/0/0 Mbps
    jnt_rates_h2h = [104, 99, 99 ,102, 104, 108]

    # jnt 8 tcp flows, D2D
    jnt_rates_d2d = [170, 158,158, 167 , 171, 174]

    fig, ax = plt.subplots(1, 1, figsize=(8, 6))
    xticks = np.arange(len(stats)) * 4

    width=0.8
    ax.axhline(y=200, color='r', ls='--', label='Single nic line rate')
    ax.bar(xticks, tcp_rr_rates_8f_4t, color='C0', label="tcp_rr 8flow 4thread", edgecolor='k')
    ax.bar(xticks + width, tcp_rr_rates_16f_8t, color='C0', hatch='//',
           label="tcp_rr 16flow 8thread", edgecolor='k')
    ax.bar(xticks + width*2, jnt_rates_h2h, color='C1', label="JNT H2H 8flow", edgecolor='k')
    ax.bar(xticks + width*3, jnt_rates_d2d, color='C1', hatch='//', label="JNT D2D 8flow", edgecolor='k')

    ax.set_xticks(xticks + 1.5 * width)
    ax.set_xticklabels(stats)

    ax.set_ylim(0, 250)
    ax.set_ylabel("Recv rates (Gbps)")
    ax.legend(ncols=2)

    plt.savefig(os.path.join(output_dir, 'stress_nic.png'), bbox_inches='tight')


def main():
    report_dir = './benchmark-report'
    report_file = os.path.join(report_dir, 'summary_lifecycle_metrics.json')
    config_file = os.path.join(report_dir, 'config.yaml')
    kv_transfer_log = os.path.join(report_dir, 'kv_transfer.log')
    plot_stress_nic(report_dir)
    plot_inference_perf_report(config_file, report_file, report_dir)
    plot_kv_transfer(kv_transfer_log, report_dir)


if __name__ == '__main__':
    main()
