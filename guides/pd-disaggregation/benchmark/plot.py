import json
import os
import re

from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytz
import yaml

nic_line_rate_Gbps = 200

# Intentionally drop 'p0.1', 'p1'
STATS = ['min', 'p5', 'p10', 'p25', 'mean', 'median', 'p75', 'p90', 'p95', 'p99', 'p99.9', 'max']

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

    if output_dir:
        plt.savefig(os.path.join(output_dir, 'benchmark_results.png'), bbox_inches='tight')


def plot_kv_transfer(kv_transfer_log, sar_log="", output_dir='.'):
    nic_rx_rates = parse_sar_log(sar_log) if sar_log else None
    # Regex to find the date and time pattern (MM-DD HH:MM:SS)
    regex = r"(\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
    ts, prepare_time, pull_time, size = [], [], [], []
    with open(kv_transfer_log, 'r') as f:
        for line in f:
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
                # print(f"Full Timestamp String with Year: {full_timestamp_str}")

                # Define the format
                # %Y - Year with century
                # %m - Month as a zero-padded decimal number
                # %d - Day of the month as a zero-padded decimal number
                # %H - Hour (24-hour clock) as a zero-padded decimal number
                # %M - Minute as a zero-padded decimal number
                # %S - Second as a zero-padded decimal number
                date_format = "%Y-%m-%d %H:%M:%S"

                # Parse the string into a datetime object
                datetime_obj = datetime.strptime(full_timestamp_str, date_format)
                datetime_obj = pytz.utc.localize(datetime_obj)
                ts.append(datetime_obj)
    assert len(ts) == len(prepare_time)
    assert len(ts) == len(pull_time)
    assert len(ts) == len(size)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    ax = axes[0]
    ax.plot(*cdf(prepare_time), label="Prepare time")
    ax.plot(*cdf(pull_time), label="Pull time")
    ax.set_xlim(0, )
    ax.set_xlabel("Time (ms)")
    ax.set_ylim(0, 1)
    ax.set_ylabel("CDF")
    ax.legend()

    ax = axes[1]
    ax.plot(*cdf(size))
    ax.set_xlabel("KV transfer size (MiB)")
    ax.set_ylim(0, 1)
    ax.set_ylabel("CDF")
    if output_dir:
        plt.savefig(os.path.join(output_dir, 'kv_transfer_dist.png'), bbox_inches='tight')

    fig, ax = plt.subplots(1, 1, figsize=(6, 5))
    ax.scatter(size, prepare_time, label='Prepare time')
    ax.scatter(size, pull_time, label='Pull time')
    ax.set_xlabel("KV transfer size (MiB)")
    ax.set_ylabel("Time (ms)")
    ax.set_ylim(0, )
    ax.legend()
    if output_dir:
        plt.savefig(os.path.join(output_dir, 'kv_transfer_time_vs_size.png'), bbox_inches='tight')


    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)

    xvals = [(t - ts[0]).total_seconds() for t in ts]

    ax = axes[0]
    ax.plot(xvals, size, '.-')
    ax.set_ylabel('KV Size (MiB)')

    ax = axes[1]
    ax.plot(xvals, prepare_time, '.-', label='Prepare time')
    ax.plot(xvals, pull_time, '.-', label='Pull time')
    ax.set_xlim(0, )
    ax.set_ylabel('Time (ms)')
    ax.set_ylim(0, )
    ax.legend()

    ax = axes[2]
    for iface, group in nic_rx_rates.groupby('IFACE'):
        mask = group['Time'] >= ts[0]
        nic_util = group[mask]['rxkB/s'] * 8 / 1000000 / nic_line_rate_Gbps
        ax.plot((group[mask]['Time'] - ts[0]).dt.total_seconds(), nic_util, marker='.', label=iface)
    ax.legend()
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('NIC Util')
    ax.set_ylim(0, 1)

    if output_dir:
        plt.savefig(os.path.join(output_dir, 'kv_transfer_time_series.png'), bbox_inches='tight')

def plot_stress_nic(output_dir):
    stats = ['min', 'p1', 'p10', 'mean', 'p50', 'max']
    # single nic, 1 client, 1MiB request, 1KiB response, 8 tcp flows, 4 threads
    # ms-pd-llm-d-modelservice-prefill-7b4d86cd4c-dkg8k --- (1MiB) --> ms-pd-llm-d-modelservice-decode-5f54bc9fb5-nt2wv
    # ms-pd-llm-d-modelservice-prefill-7b4d86cd4c-dkg8k <-- (1KiB) --- ms-pd-llm-d-modelservice-decode-5f54bc9fb5-nt2wv
    # tcp server recv rate, count: 98, min/avg/max: 142/159/175, p50/p90/p99: 159/148/142 Gbps
    # tcp client recv rate, count: 98, min/avg/max: 138/154/170, p50/p90/p99: 154/144/138 Mbps
    tcp_rr_rates_8f_4t = [142, 142 ,148, 159, 159, 175]

    # single nic, 1 client, 1MiB request, 1KiB response, 16 tcp flows, 8 threads
    # ms-pd-llm-d-modelservice-prefill-7b4d86cd4c-dkg8k --- (1MiB) --> ms-pd-llm-d-modelservice-decode-5f54bc9fb5-nt2wv
    # ms-pd-llm-d-modelservice-prefill-7b4d86cd4c-dkg8k <-- (1KiB) --- ms-pd-llm-d-modelservice-decode-5f54bc9fb5-nt2wv
    # tcp server recv rate, count: 98, min/avg/max: 187/189/191, p50/p90/p99: 189/188/187 Gbps
    # tcp client recv rate, count: 98, min/avg/max: 182/184/186, p50/p90/p99: 185/183/182 Mbps
    tcp_rr_rates_16f_8t = [187, 187 ,188, 189, 189, 191]

    # jnt 8 tcp flows, H2H
    # ms-pd-llm-d-modelservice-prefill-7b4d86cd4c-dkg8k --- (1MiB) --> ms-pd-llm-d-modelservice-decode-5f54bc9fb5-nt2wv
    # ms-pd-llm-d-modelservice-prefill-7b4d86cd4c-dkg8k <-- (1KiB) --- ms-pd-llm-d-modelservice-decode-5f54bc9fb5-nt2wv
    # jnt server recv rate, count: 58, min/avg/max: 99/104/108, p50/p90/p99: 104/102/99 Gbps
    # jnt client recv rate, count: 0, min/avg/max: 0/0/0, p50/p90/p99: 0/0/0 Mbps
    jnt_rates_h2h = [99, 99 ,102, 104, 104, 108]

    # jnt 8 tcp flows, D2D
    jnt_rates_d2d = [158,158, 167, 170, 171, 174]

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


def parse_sar_log(sar_log):
    parsed_data = []
    date_str = ""
    la_tz = pytz.timezone("America/Los_Angeles")
    with open(sar_log, 'r') as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            if i == 0:
                cols = line.split('\t')
                date_str = cols[1]
                continue
            cols = line.split()
            # Filter for data lines: Must have HH:MM:SS AM/PM format
            # Skip the average lines
            if not (len(cols) >= 6 and cols[1] in ['AM', 'PM']):
                continue
            # Skip the column header line
            if cols[2] == 'IFACE':
                continue
            # Parse timestamp and numeric values
            time_str = f"{cols[0]} {cols[1]}"
            time_obj = datetime.strptime(date_str + " " + time_str, "%m/%d/%Y %I:%M:%S %p")
            time_obj = la_tz.localize(time_obj)
            iface = cols[2]
            rx_kb_s = float(cols[5])

            parsed_data.append({
                'Time': time_obj,
                'IFACE': iface,
                'rxkB/s': rx_kb_s
            })

    return pd.DataFrame(parsed_data)

def parse_line(cols):
    req_id = -1
    offset = -1
    bytes = -1
    is_largest = False
    ts = ""
    bond_id = -1
    for col in cols:
        k, v = col.split(':', 1)
        k = k.strip()
        v = v.strip()
        if k == 'req_id':
            req_id = int(v)
        elif k == "bytes":
            bytes = int(v)
        elif k == "offset":
            offset = int(v)
        elif k == 'is_largest':
            is_largest = v == 'true'
        elif k == 'timestamp':
            ts = datetime.fromisoformat(v)  # datetime object stores up to us and drops ns precision
        elif k == 'bond_id':
            bond_id = int(v)
        elif k == 'buf_size':
            pass
        else:
            raise ValueError("Unkown " + k)
    return req_id, offset, bytes, is_largest, ts, bond_id


def parse_jnt_network_metrics(prefill_log, decode_log):
    network_metrics = {}
    for log_file in [prefill_log, decode_log]:
        with open(log_file, 'r') as f:
            for i, line in enumerate(f):
                if "[metric]" not in line:
                    continue
                cols = line.strip().split(',')
                req_id, offset, bytes, is_largest, ts, bond_id = parse_line(cols[1:])
                if req_id not in network_metrics:
                    network_metrics[req_id] = {}
                req_metrics = network_metrics[req_id]

                if offset not in req_metrics:
                    req_metrics[offset] = {}
                chunk_metrics = req_metrics[offset]

                chunk_metrics.setdefault('bytes', bytes)
                assert chunk_metrics['bytes'] == bytes

                chunk_metrics.setdefault('is_largest', is_largest)
                assert chunk_metrics['is_largest'] == is_largest

                if bond_id != -1:
                    chunk_metrics.setdefault('bond_id', bond_id)
                    assert chunk_metrics['bond_id'] == bond_id

                if 'on_send' in cols[0]:
                    assert 'ts_on_send' not in chunk_metrics, log_file +  ", line " + str(i)
                    chunk_metrics['ts_on_send'] = ts
                elif 'Send on_done' in cols[0]:
                    assert 'ts_on_send_done' not in chunk_metrics
                    chunk_metrics['ts_on_send_done'] = ts
                elif 'on_recv' in cols[0]:
                    assert 'ts_on_recv' not in chunk_metrics
                    chunk_metrics['ts_on_recv'] = ts

    def is_valid_chunk_metrics(chunk_metrics):
        return 'ts_on_send' in chunk_metrics and 'ts_on_send_done' in chunk_metrics and 'ts_on_recv' in chunk_metrics and 'is_largest' in chunk_metrics

    def is_valid_req_metrics(req_metrics):
        has_is_largest = False
        for offset, chunk_metrics in req_metrics.items():
            if not is_valid_chunk_metrics(chunk_metrics):
                # print('here')
                return False
            has_is_largest = has_is_largest or chunk_metrics['is_largest']
            # print(has_is_largest, chunk_metrics['is_largest'])
        return has_is_largest

    print(len(network_metrics))
    ret = {req: req_metrics for req, req_metrics in network_metrics.items() if is_valid_req_metrics(req_metrics)}
    print(len(ret))
    return ret


def plot_jnt_network_metrics(net_metrics, output_dir='.'):
    xvals = []
    net_lats = []
    send_lats = []
    sizes = []
    req_lats = []
    req_recv_ts = []
    for req_id, req_metrics in net_metrics.items():
        ts_on_send = []
        ts_on_recv = []
        for offset, v in req_metrics.items():
            xvals.append(v['ts_on_recv'])
            net_lat = (v['ts_on_recv'] - v['ts_on_send']).total_seconds() * 1000
            net_lats.append(net_lat)
            send_lat = (v['ts_on_send_done'] - v['ts_on_send']).total_seconds() * 1000
            send_lats.append(send_lat)
            sizes.append(v['bytes'] / 1024 / 1024)

            ts_on_send.append(v['ts_on_send'])
            ts_on_recv.append(v['ts_on_recv'])
        req_recv_ts.append(max(ts_on_recv))
        req_lats.append((max(ts_on_recv) - min(ts_on_send)).total_seconds() * 1000)

    sorted_tuples = sorted(zip(xvals, net_lats, send_lats, sizes))
    xvals, net_lats, send_lats, sizes = zip(*sorted_tuples)
    xvals, net_lats, send_lats, sizes = list(xvals), list(net_lats), list(send_lats), list(sizes)
    ts_start = xvals[0]
    xvals = [(x - ts_start).total_seconds() for x in xvals]
    fig, axes = plt.subplots(4, 1, figsize=(20, 14), sharex=True)
    ax = axes[0]
    ax.plot(xvals, net_lats, '.-', label="Chunk network transfer latency")
    ax.set_xlim(0, )
    ax.set_ylabel("Latency (ms)")
    ax.legend()

    ax = axes[1]
    ax.plot(xvals, send_lats, '.-', label="Chunk send latency")
    ax.set_ylabel("Latency (ms)")
    ax.legend()

    ax = axes[2]
    ax.plot(xvals, sizes, '.-', label="Chunk size")
    ax.set_ylabel("Chunk sizes (MiB)")
    ax.legend()

    ax.set_xlim(0, )

    ax = axes[3]
    req_recv_ts = [(x - ts_start).total_seconds() for x in req_recv_ts]
    ax.plot(req_recv_ts, req_lats, '.-')
    print(len(req_lats), len(xvals))
    ax.set_ylabel('PjRtBuffer network transfer latency (ms)')
    ax.set_xlabel("Time (s)")

    if output_dir:
        plt.savefig(os.path.join(output_dir, "jnt_lats.png"), bbox_inches='tight')


def main():
    report_dir = './benchmark-report'
    report_file = os.path.join(report_dir, 'summary_lifecycle_metrics.json')
    config_file = os.path.join(report_dir, 'config.yaml')
    kv_transfer_log = os.path.join(report_dir, 'kv_transfer.log')
    sar_log = os.path.join(report_dir, 'sar.csv')

    plot_inference_perf_report(config_file, report_file, report_dir)
    plot_kv_transfer(kv_transfer_log, sar_log, report_dir)

    prefill_jnt_metrics_log = os.path.join(report_dir, 'prefill_jnt_metrics.log')
    decode_jnt_metrics_log = os.path.join(report_dir, 'decode_jnt_metrics.log')
    network_metrics = parse_jnt_network_metrics(prefill_jnt_metrics_log, decode_jnt_metrics_log)
    plot_jnt_network_metrics(network_metrics, report_dir)

    plot_stress_nic(report_dir)

if __name__ == '__main__':
    main()
