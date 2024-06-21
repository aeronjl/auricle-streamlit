
from contextlib import contextmanager
import json
import logging
import os
import tempfile
import uuid

import ffmpeg
from openai import OpenAI
import precisetranscribe as pts
import streamlit as st

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@contextmanager
def temporary_file(suffix = None):
    """Context manager for creating temporary files."""
    temp_dir = tempfile.gettempdir()
    temp_file = os.path.join(temp_dir, f"{uuid.uuid4()}{suffix or ''}")
    try:
        yield temp_file
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

@st.cache_data(show_spinner=False)
def convert_to_wav(input_file):
    with temporary_file() as temp_input, temporary_file('.wav') as temp_output:
        # Write the input file to the temporary file
        with open(temp_input, 'wb') as f:
            f.write(input_file.getvalue())
        
        try:
            stream = ffmpeg.input(temp_input)
            stream = ffmpeg.output(stream, temp_output, acodec='pcm_s16le', ac=1, ar='16k')
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
            
            # Read the output file
            with open(temp_output, 'rb') as f:
                return f.read()
        except ffmpeg.Error as e:
            logger.error(f"Error converting file: {e.stderr.decode()}")
            st.error("An error occurred while processing the audio file.")
            return None
        
@st.cache_data(show_spinner=False)
def transcribe_audio(audio_data):
    try:
        with temporary_file('.wav') as temp_audio:
            # Write the audio data to the temporary file
            with open(temp_audio, 'wb') as f:
                f.write(audio_data)
            
            # Transcribe the audio file
            with open(temp_audio, "rb") as audio_file:
                transcript_segments, combined_processed_chunks = pts.transcribe_audio(audio_file)
            
            return combined_processed_chunks
    except Exception as e:
        logger.error(f"Error during transcription: {str(e)}")
        st.error("An error occurred during transcription.")
        return None

def validate_file_type(file):
    allowed_types = [
        "audio/mpeg", "audio/mp4", "audio/x-m4a", "audio/wav", "audio/webm",
        "video/mp4", "video/mpeg", "video/webm"
    ]
    if file.type not in allowed_types:
        return False
    return True

tab1, tab2 = st.tabs(["Transcription", "Viewer"])

with tab1:
    # 1. Upload an audio file
    uploaded_file = st.file_uploader("Choose a media file", type=["mp3", "wav", "m4a", "mp4", "webm", "mpeg"])

    if uploaded_file is not None:
        if not validate_file_type(uploaded_file):
            st.error("Invalid file type. Please upload an audio or video file.")
        else:
            st.success("File uploaded successfully.")
            
            wav_data = convert_to_wav(uploaded_file)
        
            if wav_data:
                st.success("File prepared for transcription.")
                
            combined_transcript_segments, combined_processed_chunks = pts.transcribe_audio(wav_data)
            
            if combined_processed_chunks:
                st.success("Transcription complete.")
                st.download_button("Download transcript", json.dumps(combined_processed_chunks, indent=2), f"{uploaded_file.name}_final_output.json", "json")
                

with tab2:
    current_dir = os.getcwd()
    files_dir = os.path.join(current_dir, "files")
    all_files = os.listdir(files_dir)
    json_files = [f for f in all_files if f.endswith("_final_output.json")]

    if len(json_files) == 0:
        st.error("No transcripts available.")
    else:
        option = st.selectbox(
            'Choose a transcript to display',
            json_files
        )
        
        with open(f"files/{option}", "r") as json_file:
            for line in json_file:
                my_json = json.loads(line)

        if my_json:
            st.json(my_json)