import os
import xmltodict
import streamlit as st
import pandas as pd
from tqdm import tqdm

# -----------------------------
# Config
# -----------------------------
EHR_PATH = "MedAlign/medalign_instructions_v1_3/ehrs"

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
                        "matched_value": str(text)[:200].replace("\n", " ") + "..."
                    })
    return results


# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="MedAlign EHR Viewer", layout="wide")
st.title("🩺 MedAlign EHR Timeline & Dataset Keyword Search")

# Get list of files once
files = [f for f in os.listdir(EHR_PATH) if f.endswith(".xml")]

# ====================================================
# 🌍 Global Keyword Search (Top Section)
# ====================================================
st.subheader("🌍 Global Keyword Search Across All Patients")

# Select search attribute and keyword
attributes = ["#text", "@type", "@visit_id", "@code", "@name"]
attr = st.selectbox("Select attribute to search in:", attributes, index=0)
keyword = st.text_input("Enter keyword to search for across all files:")

# Initialize session state for persistent results
if "search_results" not in st.session_state:
    st.session_state.search_results = None
if "last_keyword" not in st.session_state:
    st.session_state.last_keyword = None
if "last_attr" not in st.session_state:
    st.session_state.last_attr = None

# Search button
search_btn = st.button("🔍 Search Keyword")

# Run search only when button pressed
if search_btn and keyword.strip():
    st.info(f"Searching for **'{keyword}'** in attribute **{attr}** across all EHR XML files... This may take a few seconds ⏳")

    all_results = []
    for f in tqdm(files, desc="Searching files"):
        file_path = os.path.join(EHR_PATH, f)
        all_results.extend(search_keyword_in_file(file_path, keyword, attr))

    if all_results:
        df_all = pd.DataFrame(all_results)
        st.success(f"✅ Found {len(df_all)} matches for '{keyword}' in {attr} across {len(set(df_all['patient_id']))} patients.")
        st.session_state.search_results = df_all
        st.session_state.last_keyword = keyword
        st.session_state.last_attr = attr
    else:
        st.warning(f"No matches found for '{keyword}' in {attr} across dataset.")
        st.session_state.search_results = None
        st.session_state.last_keyword = keyword
        st.session_state.last_attr = attr

# Display previous results if no new search triggered
elif st.session_state.search_results is not None:
    last_kw = st.session_state.last_keyword
    last_attr = st.session_state.last_attr
    st.info(f"Showing previous search results for **'{last_kw}'** in **{last_attr}**.")
    st.dataframe(st.session_state.search_results, use_container_width=True, height=500)

else:
    st.caption("Enter a keyword and click **Search** to begin.")

st.divider()

# ====================================================
# 👤 Patient-Level Exploration
# ====================================================
st.subheader("👤 Explore Individual Patient Files")

filename = st.sidebar.selectbox("Select patient file (for browsing)", files)

if filename:
    data = load_xml(filename)
    ehr_df = get_ehr_summary(data)
    st.subheader("📋 EHR Overview (Encounters)")
    st.dataframe(ehr_df, use_container_width=True)

    # Encounter selection
    encounter_idx = st.number_input("Select encounter index", 0, len(ehr_df) - 1, 0)
    enc = data["eventstream"]["encounter"][encounter_idx]
    entries = enc["events"]["entry"]
    if not isinstance(entries, list):
        entries = [entries]

    # Entry summary
    entry_summary = []
    for i, e in enumerate(entries):
        events = e.get("event", [])
        if not isinstance(events, list):
            events = [events]
        first_event = events[0] if events else {}
        entry_summary.append({
            "entry_index": i,
            "note_count": len(events),
            "main_type": first_event.get("@type", "N/A"),
            "main_code": first_event.get("@code", "N/A")
        })

    entry_df = pd.DataFrame(entry_summary)

    entry_idx = st.number_input("Select entry index", 0, len(entry_df) - 1, 0)
    selected_entry = entries[entry_idx]
    notes = selected_entry.get("event", [])
    if not isinstance(notes, list):
        notes = [notes]

    # Notes table
    note_table = []
    for j, n in enumerate(notes):
        note_table.append({
            "note_index": j,
            "type": n.get("@type", "N/A"),
            "code": n.get("@code", "N/A"),
            "snippet": n.get("#text", "")
        })

    st.subheader(f"🧾 Notes in Entry #{entry_idx}")
    note_df = pd.DataFrame(note_table)
    st.dataframe(note_df, use_container_width=True, height=300)

    # Note text viewer
    note_idx = st.number_input("Select note index", 0, len(note_df) - 1, 0)
    selected_note = notes[note_idx]
    note_text = selected_note.get("#text", "")

    if note_text:
        st.subheader("📝 Note Text")
        st.text_area("Note", note_text, height=300)