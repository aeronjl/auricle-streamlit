import streamlit as st
import stripe
import io
from pydub import AudioSegment

stripe.api_key = ''

def convert_audio_to_wav(input_file):
    audio = AudioSegment.from_file(io.BytesIO(input_file.getvalue()))
    output_buffer = io.BytesIO()
    audio.export(output_buffer, format="wav")
    return output_buffer.getvalue(), audio.duration_seconds

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

st.title('Auricle')
st.image('wave.jpg')

# 1. Upload an audio file
uploaded_file = st.file_uploader("Choose a file")

if uploaded_file is not None:
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
    
