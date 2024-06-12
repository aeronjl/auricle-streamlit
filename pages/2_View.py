import streamlit as st
import json
import os

current_dir = os.getcwd()
files_dir = os.path.join(current_dir, "files")
all_files = os.listdir(files_dir)
json_files = [f for f in all_files if f.endswith("_final_output.json")]

option = st.selectbox(
    'Choose a transcript to display',
    json_files
)

st.write('You selected:', option)

with open(f"files/{option}", "r") as json_file:
    for line in json_file:
        my_json = json.loads(line)

st.json(my_json)