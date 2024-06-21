import streamlit as st
import stripe
import io
from pydub import AudioSegment
import streamlit as st
import json
import os
import logging
from contextlib import contextmanager
import tempfile
import uuid
import ffmpeg
from openai import OpenAI as openai

stripe.api_key = ''

client = openai.Client()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@contextmanager
def temporary_file(suffix=None):
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
                transcript = client.audio.transcriptions.create(
                    model = "whisper-1",
                    file=audio_file
                )
            
            return transcript["text"]
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
        
@st.cache_data(show_spinner=False)
def cache_audio(audio_file):
    # Cache the audio file
    return audio_file

def calculate_price(duration_seconds, rate_per_minute=0.50):
    # Calculate the price of the transcription
    duration_minutes = duration_seconds / 60
    return round(duration_minutes * rate_per_minute, 2)

def create_checkout_session(price):
    try:
        # Create a new Checkout Session using the price ID
        amount = int(price * 100) # Convert dollars to cents
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Transcription'
                    },
                    'unit_amount': amount
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url='http://localhost:8501/?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='http://localhost:8501/cancel',
        )
        return session.url
    except Exception as e:
        return str(e)

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
            
            transcription = transcribe_audio(wav_data)
            
            if transcription:
                st.write("Transcription:")
                st.write(transcription)

"""    
    # Cache the audio file
    uploaded_file = cache_audio(uploaded_file)
    with st.spinner('Processing audio file...'):
        # Check if the file is already a WAV file
        if uploaded_file.name.lower().endswith(".wav"):
            audio = AudioSegment.from_file(io.BytesIO(uploaded_file.getvalue()))
            bytes_data = uploaded_file.getvalue()
            duration_seconds = audio.duration_seconds
        else:
            # Convert the audio file to WAV
            bytes_data, duration_seconds = convert_audio_to_wav(uploaded_file)
        
        # 2. Calculate the price
        price = calculate_price(duration_seconds)
        price_message = f"The transcription will cost ${price}."
        st.write(price_message)

        session_url = create_checkout_session(price)
        if session_url:
            st.write(f"Click [here]({session_url}) to pay and start the transcription.")

if 'session_id' not in st.query_params:
    st.query_params["session_id"] = ''
    
# Return the user back to the app with their transcaction code as a query
if st.query_params["session_id"]:
    session_id = st.query_params["session_id"]            
    with st.spinner('Verifying your payment...'):
        try:
            # Check the Stripe database to see if that payment was successful 
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == 'paid':
                st.success("Payment successful! Starting transcription...")
            else:
                st.error("Payment failed. Please try again.")
        except stripe.error.StripeError as e:
            st.error(f"Error: {e}")
    


st.header("Transcription Output")

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
"""