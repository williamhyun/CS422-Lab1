import random


import subprocess
import re
import platform
import matplotlib.pyplot as plt

'''
    Given an ip adress try to find its RTT for every stop
    Returns a list of dicts: [, ...]
    Each entry in the list represents a single dictionary in the form {'hop': (Which hop), 'ip': (IP), 'rtts': (List of RTT values)}
'''
def ping_ip(dest_ip):
    #Find which platform is being used (-n for windows -c for mac/linux)
    command = ""
    is_windows = platform.system().lower() == "windows"
    if is_windows:
        command = ["tracert", "-d", dest_ip]
    else:
        command = ["traceroute", "-n", dest_ip]


    hops = []
    try:
        #Attempt to run trace route and store its stdout
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30).stdout
    except Exception as e:
        print(f"Failed to run traceroute for {dest_ip}: {e}")
        return hops


    lines = result.splitlines()

    #Every line is a hop, so for every hop:
    for line in lines:
        line = line.strip()

        #skip empty lines
        if not line:
            continue

        #return format is platform dependent
        if (is_windows):
            # Windows line format example: "  1    <1 ms    <1 ms    <1 ms  192.168.1.1"
            #Use regular expression to pick information
            match = re.match(r"^\s*(\d+)\s+(.+?)\s+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+|\*)$", line)

            if match:
                hop_num = int(match.group(1))
                metrics_str = match.group(2)
                hop_ip = match.group(3)
                            
                # Extract all ms values
                rtts = [float(val) for val in re.findall(r"([0-9]+)\s*ms", metrics_str)]

                # SKIP if hop timed out / has no RTTs / is an asterisk
                if not rtts or hop_ip == "*":
                    continue

                hops.append({"hop": hop_num, "ip": hop_ip, "rtts": rtts})

        else: #(not windows)
            # Linux/Mac line format example: " 1  192.168.1.1  1.123 ms  1.054 ms"
            #Use regular expression to pick information
            match = re.search(r"^\s*(\d+)\s+(?:([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)|\*)", line)
            if match:
                hop_num = int(match.group(1))
                # Find all IP addresses in the line if present
                ips = re.findall(r"([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", line)
                hop_ip = ips[0] if ips else None
                            
                # Extract all millisecond values
                rtts = [float(val) for val in re.findall(r"([0-9]+\.[0-9]+)\s*ms", line)]

                # SKIP if hop timed out / has no RTTs
                if not rtts or not hop_ip:
                    continue

                hops.append({"hop": hop_num, "ip": hop_ip, "rtts": rtts})

    return hops




'''
    Takes in a list of ips and picks n random ips
    It the stores the results as a list of touples (ip address, RTT hop dictionary)
'''
def find_random_rtt(ip_list, n = 5):
    results = list()
    length = len(ip_list)

    #index of attempted ips
    attempted = list()

    valid_traces = 0
    while (valid_traces < n):

        #Raise error if all IPs were tried. This is a lazy way of checking this
        if (len(attempted) == length):
            return None
            #raise RuntimeError(f"Not enough valid ips to find {n} random traces")

        #Try find unattempted ip
        attempt = random.randint(0, length - 1)
        if (attempt in attempted):
            continue
        attempted.append(attempt)


        #get trace route
        result = ping_ip(ip_list[attempt])
        if (len(result) == 0):
            continue

        results.append((ip_list[attempt], result))
        valid_traces += 1

    return results

def average_list(list):
    summ = 0
    for i in list:
        summ += i

    return summ / len(list)

def find_and_print_random(ip_list, n=5):
    results = find_random_rtt(ip_list, n)

    if (results == None):
        print(f"Not enough valid ips to find {n} random traces")
        return

    for result in results:
        print("------------------------")
        print(f"Destination IP Adress: {result[0]}")
        for hop in result[1]:
            print(f"   Hop: {hop['hop']}   |   ip: {hop['ip']}   |   RTT (Averaged): {average_list(hop['rtts'])}")

    return results





    
#Plotting functions are just ai generated for now because I was lazy and its just matplotlib anyway


def plot_stacked_bar_chart(results):
    if not results:
        print("No results to plot.")
        return

    plt.figure(figsize=(10, 6))

    # Traceroute gives *cumulative* RTT. To stack them, we need to calculate the *incremental* 
    # latency added by each specific hop (current hop RTT - previous hop RTT).
    for dest_ip, hops in results:
        current_bottom = 0.0
        
        for hop in hops:
            avg_rtt = average_list(hop['rtts'])
            
            # Use max(0, ...) to avoid negative bar chart stacks if a router prioritizes 
            # ICMP differently, causing a later hop to reply faster than an earlier one.
            incremental_rtt = max(0, avg_rtt - current_bottom)
            
            # Plot the segment
            plt.bar(dest_ip, incremental_rtt, bottom=current_bottom, edgecolor='white', width=0.6)
            
            # Update the baseline for the next stack
            current_bottom = max(current_bottom, avg_rtt)

    plt.title("Breakdown of Latencies to Each Hop")
    plt.xlabel("Destination IP Address")
    plt.ylabel("Round Trip Time (ms)")
    plt.xticks(rotation=15)
    
    plt.tight_layout()
    plt.savefig("stacked_bar_chart.pdf", dpi=300)
    plt.close()



def plot_scatter_hop_vs_rtt(results):
    if not results:
        print("No results to plot.")
        return

    dest_ips = []
    final_hop_counts = []
    final_rtts = []

    for dest_ip, hops in results:
        dest_ips.append(dest_ip)
        
        # The final hop count is simply the hop number of the very last recorded hop
        final_hop_counts.append(hops[-1]['hop']) 
        
        final_destination_rtt = average_list(hops[-1]['rtts'])
        final_rtts.append(final_destination_rtt)

    plt.figure(figsize=(8, 6))
    plt.scatter(final_hop_counts, final_rtts, color='red', s=100)
    
    # Label each point with its corresponding IP address so you know which is which
    for i, ip in enumerate(dest_ips):
        plt.annotate(ip, (final_hop_counts[i], final_rtts[i]), 
                     textcoords="offset points", xytext=(0,10), ha='center')

    plt.title("Hop Count vs Final RTT")
    plt.xlabel("Total Hop Count")
    plt.ylabel("Final RTT (ms)")
    plt.grid(True, linestyle='--', alpha=0.6)
    
    plt.tight_layout()
    plt.savefig("Scatter.pdf", dpi=300)
    plt.close()


         

