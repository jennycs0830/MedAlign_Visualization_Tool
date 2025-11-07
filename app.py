import os
import xmltodict
import streamlit as st
import pandas as pd
from tqdm import tqdm
import argparse
import json
from collections import defaultdict

# -----------------------------
# Config
# -----------------------------
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--path",
        type=str,
        default="/Users/jennysun0830/Desktop/MedAlign",
        help="Base path to MedAlign dataset"
    )
    args, _ = parser.parse_known_args()
    return args

if __name__ == "__main__":
    args = parse_args()
    EHR_PATH = os.path.join(args.path, "medalign_instructions_v1_3/ehrs")
else:
    EHR_PATH = "./medalign_instructions_v1_3/ehrs"


# -----------------------------
# Utility Functions
# -----------------------------
def load_xml(filename):
    """Load and parse an XML EHR file."""
    with open(os.path.join(EHR_PATH, filename), "r") as f:
        return xmltodict.parse(f.read())

def get_ehr_summary(data):
    """Summarize encounters for the selected patient."""
    encounters = data["eventstream"]["encounter"]
    if not isinstance(encounters, list):
        encounters = [encounters]

    summary = []
    for i, enc in enumerate(encounters):
        entries = enc["events"]["entry"]
        if not isinstance(entries, list):
            entries = [entries]
        ts = entries[0].get("@timestamp", "N/A")
        summary.append({"index": i, "timestamp": ts, "entry_count": len(entries)})
    return pd.DataFrame(summary)

def search_keyword_in_file(filepath, keyword, attr):
    """Search for a keyword in a specific attribute within a single EHR file."""
    filename = os.path.basename(filepath)
    patient_id = filename.replace(".xml", "")
    results = []

    try:
        with open(filepath, "r") as f:
            data = xmltodict.parse(f.read())
    except Exception:
        return results  # skip malformed files

    encounters = data.get("eventstream", {}).get("encounter", [])
    if not isinstance(encounters, list):
        encounters = [encounters]

    for encounter_idx, encounter in enumerate(encounters):
        entries = encounter.get("events", {}).get("entry", [])
        if not isinstance(entries, list):
            entries = [entries]

        for entry_idx, entry in enumerate(entries):
            events = entry.get("event", [])
            if not isinstance(events, list):
                events = [events]

            for event in events:
                text = event.get(attr, "")
                if text and keyword.lower() in str(text).lower():
                    results.append({
                        "patient_id": patient_id,
                        "encounter_idx": encounter_idx,
                        "entry_idx": entry_idx,
                        "attribute": attr,
                        "matched_value": str(text)
                    })
    return results


def collect_unique_values(ehr_path, files, attributes):
    """
    Collect all unique values for each selected attribute across all XML files.
    Returns a dict: {attribute_name: set(values)}.
    """
    unique_values = defaultdict(set)

    for f in tqdm(files, desc="Collecting unique values"):
        file_path = os.path.join(ehr_path, f)
        try:
            with open(file_path, "r") as xml_file:
                data = xmltodict.parse(xml_file.read())
        except Exception:
            continue

        encounters = data.get("eventstream", {}).get("encounter", [])
        if not isinstance(encounters, list):
            encounters = [encounters]

        for encounter in encounters:
            entries = encounter.get("events", {}).get("entry", [])
            if not isinstance(entries, list):
                entries = [entries]
            for entry in entries:
                events = entry.get("event", [])
                if not isinstance(events, list):
                    events = [events]
                for event in events:
                    for attr in attributes:
                        val = event.get(attr, None)
                        if val:
                            unique_values[attr].add(str(val).strip())

    return {k: list(v) for k, v in unique_values.items()}


# -----------------------------
# Streamlit Layout Setup
# -----------------------------
st.set_page_config(page_title="MedAlign EHR Viewer", layout="wide")

# Add resizable CSS behavior for columns
st.markdown("""
<style>
[data-testid="stHorizontalBlock"] > div:first-child {
    resize: horizontal;
    overflow: auto;
    min-width: 400px;
    max-width: 80%;
}
</style>
""", unsafe_allow_html=True)

st.title("🩺 MedAlign EHR Visualization Tool")
st.caption(f"Dataset path: `{EHR_PATH}`")

# Get file list
if not os.path.exists(EHR_PATH):
    st.error(f"❌ Path not found: {EHR_PATH}")
    st.stop()

files = [f for f in os.listdir(EHR_PATH) if f.endswith(".xml")]
if not files:
    st.warning("No XML files found in the specified folder.")
    st.stop()

# Initialize session state
if "search_results" not in st.session_state:
    st.session_state.search_results = None
if "last_keyword" not in st.session_state:
    st.session_state.last_keyword = None
if "last_attr" not in st.session_state:
    st.session_state.last_attr = None

# -----------------------------
# Split Page: Left / Right
# -----------------------------
left_col, right_col = st.columns([1.3, 1.7], gap="large")

# ====================================================
# 🌍 LEFT: Global Keyword Search
# ====================================================
with left_col:
    st.subheader("🌍 Global Keyword Search Across All Patients")

    attributes = ["#text", "@type", "@visit_id", "@code", "@name"]
    attr = st.selectbox("Select attribute to search in:", attributes, index=0)
    keyword = st.text_input("Enter keyword to search for across all files:")

    search_btn = st.button("🔍 Search Keyword")

    if search_btn and keyword.strip():
        st.info(f"Searching for **'{keyword}'** in **{attr}** across all EHR XML files... ⏳")
        all_results = []
        for f in tqdm(files, desc="Searching files"):
            file_path = os.path.join(EHR_PATH, f)
            all_results.extend(search_keyword_in_file(file_path, keyword, attr))

        if all_results:
            df_all = pd.DataFrame(all_results)
            st.session_state.update({
                "search_results": df_all,
                "last_keyword": keyword,
                "last_attr": attr
            })
            st.success(f"✅ Found {len(df_all)} matches across {len(set(df_all['patient_id']))} patients.")
        else:
            st.warning(f"No matches found for '{keyword}' in {attr}.")
            st.session_state.search_results = None

    if st.session_state.search_results is not None:
        st.info(f"Showing results for **'{st.session_state.last_keyword}'** in **{st.session_state.last_attr}**.")
        st.dataframe(st.session_state.search_results, use_container_width=True, height=650)
    else:
        st.caption("Enter a keyword and click **Search** to begin.")


    # ====================================================
    # 🧩 Collect Unique Attribute Values
    # ====================================================
    st.divider()
    st.subheader("🧩 Collect Unique Attribute Values")

    st.caption("Extract all unique values from selected attributes across the entire dataset.")

    attributes_to_collect = st.multiselect(
        "Select attributes to collect unique values for:",
        ["#text", "@type", "@visit_id", "@code", "@name"],
        default=["@type", "@code", "@name"]
    )

    collect_btn = st.button("📊 Collect and Save Unique Values")

    if collect_btn:
        st.info("Collecting unique attribute values... This may take a few minutes ⏳")
        unique_dict = collect_unique_values(EHR_PATH, files, attributes_to_collect)

        # Save results
        save_path_json = os.path.join(EHR_PATH, "unique_values_summary.json")
        save_path_csv = os.path.join(EHR_PATH, "unique_values_summary.csv")

        # Save JSON
        with open(save_path_json, "w") as jf:
            json.dump(unique_dict, jf, indent=2, ensure_ascii=False)

        # Save flattened CSV (attribute,value)
        flat_rows = []
        for attr, values in unique_dict.items():
            for v in values:
                flat_rows.append({"attribute": attr, "value": v})

        st.dataframe(pd.DataFrame(flat_rows), use_container_width=True, height=400)


# ====================================================
# 👤 RIGHT: Patient-Level Exploration
# ====================================================
with right_col:
    st.subheader("👤 Explore Individual Patient Files")

    filename = st.selectbox("Select patient file (for browsing)", files)

    if filename:
        data = load_xml(filename)
        ehr_df = get_ehr_summary(data)
        st.dataframe(ehr_df, use_container_width=True, height=250)

        encounter_idx = st.number_input("Select encounter index", 0, len(ehr_df) - 1, 0)
        enc = data["eventstream"]["encounter"][encounter_idx]
        entries = enc["events"]["entry"]
        if not isinstance(entries, list):
            entries = [entries]

        entry_summary = []
        for i, e in enumerate(entries):
            events = e.get("event", [])
            if not isinstance(events, list):
                events = [events]
            entry_summary.append({
                "entry_index": i,
                "note_count": len(events),
            })

        entry_df = pd.DataFrame(entry_summary)
        st.dataframe(entry_df, use_container_width=True, height=250)

        entry_idx = st.number_input("Select entry index", 0, len(entry_df) - 1, 0)
        selected_entry = entries[entry_idx]
        notes = selected_entry.get("event", [])
        if not isinstance(notes, list):
            notes = [notes]

        note_table = []
        for j, n in enumerate(notes):
            note_table.append({
                "note_index": j,
                "type": n.get("@type", "N/A"),
                "code": n.get("@code", "N/A"),
                "snippet": n.get("#text", "")
            })

        note_df = pd.DataFrame(note_table)
        st.subheader(f"🧾 Notes in Entry #{entry_idx}")
        st.dataframe(note_df, use_container_width=True, height=250)

        note_idx = st.number_input("Select note index", 0, len(note_df) - 1, 0)
        selected_note = notes[note_idx]
        note_text = selected_note.get("#text", "")

        if note_text:
            st.subheader("📝 Note Text")
            st.text_area("Note", note_text, height=300)