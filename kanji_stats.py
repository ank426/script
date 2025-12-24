#!/usr/bin/python

import argparse
import os
import webbrowser
from collections import Counter
import plotly.graph_objects as go
import numpy as np # Import numpy for vectorized array operations

# --- 1. Japanese Character Definitions ---
HIRAGANA_START = 0x3040
HIRAGANA_END = 0x309F
KATAKANA_START = 0x30A0
KATAKANA_END = 0x30FF
KANJI_START = 0x4E00
KANJI_END = 0x9FFF

# --- 2. Top Kanji List (Simulated) ---
TOP_KANJI_SET = set("日一人二年大小中学会社出本語名")
TOP_KANJI_COUNT = 2500

# --- 3. Core Analysis Functions ---

def classify_and_count_chars(text):
    """Classifies and counts all Japanese characters in the text."""
    hiragana_count = 0
    katakana_count = 0
    kanji_counts = Counter()  # Use Counter to track frequency of individual kanji

    for char in text:
        char_code = ord(char)

        if HIRAGANA_START <= char_code <= HIRAGANA_END:
            hiragana_count += 1
        elif KATAKANA_START <= char_code <= KATAKANA_END:
            katakana_count += 1
        elif KANJI_START <= char_code <= KANJI_END:
            kanji_counts[char] += 1

    total_japanese = hiragana_count + katakana_count + sum(kanji_counts.values())

    return {
        'hiragana': hiragana_count,
        'katakana': katakana_count,
        'kanji': kanji_counts,
        'total_japanese': total_japanese
    }

def calculate_top_kanji_percentage(kanji_counts):
    """
    Calculates the cumulative percentage of kanji covered by the most frequent kanji.
    Returns lists for plotting: (X: number of top kanji, Y: cumulative percentage).

    MODIFIED: Prepends (0, 0) to the lists to ensure the plot starts at the origin.
    """
    # If no kanji, return the origin point.
    if not kanji_counts:
        return [0], [0.0]

    # Get a list of (kanji, frequency) sorted by frequency (most frequent first)
    sorted_kanji = kanji_counts.most_common()

    # Total number of kanji *instances*
    total_kanji_instances = sum(kanji_counts.values())

    # Total number of *unique* kanji
    unique_kanji_count = len(sorted_kanji)

    # 1. Prepare X (number of top kanji) and Y (cumulative percentage) lists
    # START AT (0, 0) to force the line to the origin
    X_plot = [0]
    Y_plot = [0.0]

    cumulative_count = 0

    # Iterate through the sorted list and calculate the running total
    for rank, (kanji, count) in enumerate(sorted_kanji):
        cumulative_count += count

        # X: The rank of the kanji (1-indexed)
        X_plot.append(rank + 1)

        # Y: The cumulative percentage
        Y_plot.append((cumulative_count / total_kanji_instances) * 100)

    # Add a final point for completeness if the last point wasn't the total count
    if X_plot[-1] != unique_kanji_count:
            X_plot.append(unique_kanji_count)
            Y_plot.append(100.0)

    return X_plot, Y_plot

# --- 4. Plotting Functions ---

def inject_black_body_style(filepath):
    """Reads the HTML file, injects CSS to set the <body> background to black, and overwrites the file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # The CSS to inject: Target the <body> element specifically
        css_style = """
<style>
body {
    background-color: black !important;
    margin: 0;
}
</style>
"""

        # Find the closing </head> tag and insert the style block just before it.
        content = content.replace("</head>", css_style + "</head>", 1)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    except Exception as e:
        print(f"⚠️ Error injecting CSS into HTML file: {e}")


def plot_kanji_coverage(X, Y, filename):
    """Generates the Plotly graph of Kanji coverage (Y is cumulative percentage)."""
    fig = go.Figure()

    # Add the main trace
    fig.add_trace(go.Scatter(
        x=X,
        y=Y,
        mode='lines',
        name='Kanji Coverage',
        line=dict(color='yellow', width=2)
    ))

    # Calculate the maximum number of unique kanji for setting x-axis range
    max_x = max(X) if X else 100
    max_y = 100.0 # Y-axis always goes up to 100%

    # Update layout for dark mode and black background, AND set gridlines/ticks
    fig.update_layout(
        title={
            'text': 'Graph 1: Kanji Coverage by Frequency Rank',
            'y': 0.9,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'color': 'white'}
        },
        xaxis=dict(
            title='Top X Most Frequent Unique Kanji',
            # Set grid lines and tick marks every 100
            dtick=100,
            gridcolor='gray',
            range=[0, max_x + 50], # Ensure the max is visible, starts at 0
            showgrid=True,
            color='white'
        ),
        yaxis=dict(
            title='Y% of Total Kanji Instances',
            # Set grid lines and tick marks every 10 (as a percentage)
            dtick=10,
            gridcolor='gray',
            range=[0, max_y + 1], # Starts at 0
            showgrid=True,
            color='white'
        ),
        template='plotly_dark',
        plot_bgcolor='black',
        paper_bgcolor='black',
        font=dict(color='white')
    )

    # 1. Write the initial HTML file
    fig.write_html(filename, auto_open=False)

    # 2. Inject the necessary CSS to make the entire <body> black
    inject_black_body_style(filename)

    print(f"\n✨ Graph 1 (Coverage) saved successfully to: {os.path.abspath(filename)}")
    webbrowser.open_new_tab(f'file://{os.path.abspath(filename)}')


def plot_kanji_difficulty(X, Y_coverage, filename):
    """
    Generates the Plotly graph of Kanji difficulty (Y is inverse of remaining coverage).
    Y_new = 1 / (1 - Y_coverage / 100)

    MODIFIED: Y-axis is now linear, and the plot is capped at X <= 1500.
    """
    # 1. Calculate the new Y-axis values
    Y_old_percent = np.array(Y_coverage)

    # Calculate Y_new = 1 / (1 - Y_old / 100)
    Y_remaining = 1.0 - (Y_old_percent / 100.0)

    # Replace 0s in Y_remaining with a small epsilon to avoid division by zero.
    epsilon = 1e-10
    Y_remaining[Y_remaining == 0] = epsilon

    Y_difficulty = 1.0 / Y_remaining

    # 2. Truncate data points to X <= 1500 for plotting
    max_x_limit = 1000

    # Use numpy for filtering the arrays
    X_np = np.array(X)
    Y_difficulty_np = Y_difficulty

    mask = X_np <= max_x_limit

    X_plot_truncated = X_np[mask].tolist()
    Y_plot_truncated = Y_difficulty_np[mask].tolist()

    if not X_plot_truncated:
         print(f"⚠️ Warning: No data points found for X <= {max_x_limit} for difficulty graph.")
         return

    # Calculate max_y based on the truncated data
    max_y = Y_difficulty_np[mask].max() if Y_difficulty_np[mask].size > 0 else 10.0

    # 3. Create the Plotly Figure
    fig = go.Figure()

    # Add the main trace using truncated data
    fig.add_trace(go.Scatter(
        x=X_plot_truncated,
        y=Y_plot_truncated,
        mode='lines',
        name='Kanji Difficulty',
        line=dict(color='orange', width=2)
    ))

    # Update layout for dark mode and black background
    fig.update_layout(
        title={
            'text': 'Graph 2: Relative Difficulty (1 / [1 - Coverage])',
            'y': 0.9,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'color': 'white'}
        },
        xaxis=dict(
            title='Top X Most Frequent Unique Kanji',
            dtick=100,
            gridcolor='gray',
            range=[0, max_x_limit], # HARDCODED X-AXIS MAX
            showgrid=True,
            color='white'
        ),
        yaxis=dict(
            title='Difficulty Multiplier (1 / (1 - Y_coverage))',
            type='linear', # CHANGED to linear scale
            # Set dtick to something reasonable, adjusted for the new linear scale
            # dtick=2,
            gridcolor='gray',
            # Set range to start at 1 (the minimum value for this metric)
            range=[1, max_y * 1.05],
            showgrid=True,
            color='white'
        ),
        template='plotly_dark',
        plot_bgcolor='black',
        paper_bgcolor='black',
        font=dict(color='white')
    )

    # 4. Save and Open
    fig.write_html(filename, auto_open=False)
    inject_black_body_style(filename)

    print(f"\n✨ Graph 2 (Difficulty) saved successfully to: {os.path.abspath(filename)}")
    webbrowser.open_new_tab(f'file://{os.path.abspath(filename)}')


# --- 5. Main Execution Logic ---

def main():
    """Main function to parse arguments, process files, and generate results."""
    parser = argparse.ArgumentParser(
        description="Analyze Japanese character usage in text files."
    )
    parser.add_argument(
        'files',
        metavar='FILE',
        type=str,
        nargs='+',
        help='List of text files to analyze.'
    )

    args = parser.parse_args()

    # Aggregated results across all files
    total_results = {
        'hiragana': 0,
        'katakana': 0,
        'kanji': Counter(),
        'total_japanese': 0
    }

    print("--- Starting Japanese Text Analysis ---")

    for filepath in args.files:
        if not os.path.exists(filepath):
            print(f"⚠️ Error: File not found: {filepath}")
            continue

        print(f"\nProcessing file: **{filepath}**")

        try:
            # Attempt to read with 'utf-8', which is necessary for Japanese characters
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            print(f"⚠️ Error: Could not decode {filepath}. Ensure it is UTF-8 encoded.")
            continue
        except Exception as e:
            print(f"⚠️ An error occurred while reading {filepath}: {e}")
            continue

        file_results = classify_and_count_chars(content)

        # Aggregate results
        total_results['hiragana'] += file_results['hiragana']
        total_results['katakana'] += file_results['katakana']
        total_results['kanji'].update(file_results['kanji'])
        total_results['total_japanese'] += file_results['total_japanese']

    # --- Final Calculations and Output ---

    total_hiragana = total_results['hiragana']
    total_katakana = total_results['katakana']
    total_kanji_instances = sum(total_results['kanji'].values())
    total_japanese = total_results['total_japanese']

    if total_japanese == 0:
        print("\n--- Analysis Complete ---")
        print("❌ No Japanese characters were found in the provided files.")
        return

    # 1. Percentage of each script (Hiragana, Katakana, Kanji)
    print("\n--- Japanese Script Distribution (Total Instances) ---")
    print(f"Total Japanese Characters Found: **{total_japanese:,}**")

    # Use a helper lambda for percentage calculation
    pct = lambda count: (count / total_japanese) * 100

    # Print the distribution table
    print(f"* **Hiragana**: {total_hiragana:,} instances ({pct(total_hiragana):.2f}%)")
    print(f"* **Katakana**: {total_katakana:,} instances ({pct(total_katakana):.2f}%)")
    print(f"* **Kanji**:    {total_kanji_instances:,} instances ({pct(total_kanji_instances):.2f}%)")

    # 2. Percentage of Kanji covered by Top X
    print("\n--- Kanji Frequency Analysis ---")
    if total_kanji_instances > 0:

        # Calculate the X and Y lists for plotting
        X_plot, Y_plot = calculate_top_kanji_percentage(total_results['kanji'])

        # Find the index of the point corresponding to rank 250 or the highest rank if less than 250
        target_rank = 250
        top_x_index = -1
        try:
            # Find the index of the actual rank
            top_x_index = X_plot.index(target_rank)
        except ValueError:
            # If 250 is not in the list, use the last index (max rank)
            top_x_index = len(X_plot) - 1
            target_rank = X_plot[top_x_index]

        if top_x_index >= 0:
            top_x_kanji_count = X_plot[top_x_index]
            top_x_kanji_coverage = Y_plot[top_x_index]

            print(f"The **top {top_x_kanji_count}** most frequent unique kanji found")
            print(f"make up **{top_x_kanji_coverage:.2f}%** of all kanji instances.")

        # 3. Plot the graphs

        # --- Graph 1: Standard Coverage ---
        plot_filename_1 = "kanji_coverage.html"
        plot_kanji_coverage(X_plot, Y_plot, plot_filename_1)

        # --- Graph 2: Difficulty/Inverse Coverage ---
        plot_filename_2 = "kanji_difficulty.html"
        plot_kanji_difficulty(X_plot, Y_plot, plot_filename_2)

    else:
        print("❌ No Kanji characters were found for frequency analysis.")

    print("\n--- Script Finished ---")

if __name__ == "__main__":
    main()
